from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.intern_management import Cohort, CohortMember, HostCompany, InternGroup, InternPlacement
from app.models.notification import Notification
from app.models.user import User
from app.utils.audit import log_audit_event
from app.utils.decorators import permission_required, staff_required

bp = Blueprint('intern_management', __name__, url_prefix='/intern-management')

INTERN_TYPE_CHOICES = ['varsity', 'tvet', 'mixed']


def ensure_intern_type_groups():
    """Ensure fixed groups exist for each intern type."""
    mapping = {}
    for intern_type in INTERN_TYPE_CHOICES:
        group = InternGroup.query.filter_by(education_type=intern_type, is_active=True).first()
        if not group:
            group = InternGroup(
                name=intern_type.upper(),
                education_type=intern_type,
                description=f'Auto-managed group for {intern_type} interns.',
                created_by=current_user.id if current_user.is_authenticated else None,
                is_active=True,
            )
            db.session.add(group)
            db.session.flush()
        mapping[intern_type] = group
    return mapping


@bp.route('/')
@login_required
@staff_required
def dashboard():
    """Central page for cohorts and host companies using intern type grouping."""
    intern_type = request.args.get('intern_type', 'all')

    group_map = ensure_intern_type_groups()
    db.session.commit()

    intern_query = User.query.filter_by(role='intern', is_deleted=False)
    if intern_type in INTERN_TYPE_CHOICES:
        intern_query = intern_query.filter_by(intern_type=intern_type)
    interns = intern_query.order_by(User.created_at.desc()).all()

    cohorts = Cohort.query.order_by(Cohort.created_at.desc()).all()
    hosts = HostCompany.query.order_by(HostCompany.created_at.desc()).all()

    active_placements = (
        InternPlacement.query.filter_by(is_active=True)
        .order_by(InternPlacement.assigned_at.desc())
        .all()
    )

    unassigned_intern_ids = {
        user.id
        for user in interns
        if not InternPlacement.query.filter_by(intern_id=user.id, is_active=True).first()
    }

    return render_template(
        'staff/intern_management.html',
        interns=interns,
        intern_type_choices=INTERN_TYPE_CHOICES,
        intern_type_groups=group_map,
        cohorts=cohorts,
        hosts=hosts,
        active_placements=active_placements,
        intern_type=intern_type,
        unassigned_intern_ids=unassigned_intern_ids,
    )


@bp.route('/groups/create', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def create_group():
    name = (request.form.get('name') or '').strip()
    education_type = (request.form.get('education_type') or 'mixed').strip().lower()
    description = (request.form.get('description') or '').strip()

    if not name:
        flash('Group name is required.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    if education_type not in ['varsity', 'tvet', 'mixed']:
        flash('Invalid group education type.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    existing = InternGroup.query.filter(db.func.lower(InternGroup.name) == name.lower()).first()
    if existing:
        flash('A group with this name already exists.', 'warning')
        return redirect(url_for('intern_management.dashboard'))

    group = InternGroup(
        name=name,
        education_type=education_type,
        description=description or None,
        created_by=current_user.id,
    )
    db.session.add(group)
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='intern_group_created',
        entity_type='intern_group',
        entity_id=group.id,
        details={'name': group.name, 'education_type': group.education_type},
    )

    flash('Intern group created successfully.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/cohorts/create', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def create_cohort():
    name = (request.form.get('name') or '').strip()
    status = (request.form.get('status') or 'active').strip().lower()
    intern_type = (request.form.get('intern_type') or '').strip().lower()
    start_date_raw = (request.form.get('start_date') or '').strip()
    end_date_raw = (request.form.get('end_date') or '').strip()
    notes = (request.form.get('notes') or '').strip()

    if not name or intern_type not in INTERN_TYPE_CHOICES:
        flash('Cohort name and intern type are required.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    if status not in ['active', 'completed', 'archived']:
        flash('Invalid cohort status.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    group_map = ensure_intern_type_groups()
    group = group_map[intern_type]

    start_date = None
    end_date = None

    try:
        if start_date_raw:
            start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
        if end_date_raw:
            end_date = datetime.strptime(end_date_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format provided.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    cohort = Cohort(
        name=name,
        group_id=group.id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        notes=notes or None,
        created_by=current_user.id,
    )
    db.session.add(cohort)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('A cohort with this name already exists in the selected group.', 'warning')
        return redirect(url_for('intern_management.dashboard'))

    flash('Cohort created successfully.', 'success')
    log_audit_event(
        actor_user_id=current_user.id,
        action='cohort_created',
        entity_type='cohort',
        entity_id=cohort.id,
        details={'name': cohort.name, 'group_id': cohort.group_id, 'intern_type': intern_type},
    )
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/cohorts/assign-member', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_assignments')
def assign_member_to_cohort():
    cohort_id = request.form.get('cohort_id', type=int)
    intern_ids = [int(x) for x in request.form.getlist('intern_ids') if x.isdigit()]

    if not cohort_id or not intern_ids:
        flash('Please select a cohort and at least one intern.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    cohort = Cohort.query.get(cohort_id)
    if not cohort:
        flash('Invalid cohort selected.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    cohort_intern_type = cohort.group.education_type if cohort.group else 'mixed'
    assigned = skipped = type_mismatch = 0

    for intern_id in intern_ids:
        intern = User.query.filter_by(id=intern_id, role='intern', is_deleted=False).first()
        if not intern:
            skipped += 1
            continue

        intern_type = (intern.intern_type or 'mixed').lower()
        if cohort_intern_type != 'mixed' and intern_type != cohort_intern_type:
            type_mismatch += 1
            continue

        if CohortMember.query.filter_by(cohort_id=cohort_id, intern_id=intern_id).first():
            skipped += 1
            continue

        member = CohortMember(cohort_id=cohort_id, intern_id=intern_id, created_by=current_user.id)
        db.session.add(member)
        assigned += 1

    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='cohort_member_assigned',
        entity_type='cohort_member',
        entity_id=cohort_id,
        details={'cohort_id': cohort_id, 'assigned': assigned, 'skipped': skipped},
    )

    parts = [f'{assigned} intern(s) assigned to cohort.']
    if skipped:
        parts.append(f'{skipped} skipped (already assigned or not found).')
    if type_mismatch:
        parts.append(f'{type_mismatch} skipped (intern type mismatch).')
    flash(' '.join(parts), 'success' if assigned else 'warning')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/hosts/create', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_host_companies')
def create_host_company():
    company_name = (request.form.get('company_name') or '').strip()
    contact_person = (request.form.get('contact_person') or '').strip()
    contact_email = (request.form.get('contact_email') or '').strip().lower()
    contact_phone = (request.form.get('contact_phone') or '').strip()
    address = (request.form.get('address') or '').strip()
    login_password = (request.form.get('login_password') or '').strip() or 'JubaHost2026!'

    if not company_name or not contact_email:
        flash('Company name and login email are required.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    if HostCompany.query.filter(db.func.lower(HostCompany.company_name) == company_name.lower()).first():
        flash('Host company with this name already exists.', 'warning')
        return redirect(url_for('intern_management.dashboard'))

    if User.query.filter_by(email=contact_email, is_deleted=False).first():
        flash('The login email is already used by another user.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    host_user = User(
        email=contact_email,
        role='host_company',
        name=contact_person or company_name,
        is_profile_complete=True,
        first_login=False,
        requires_password_change=True,
        created_by=current_user.id,
    )
    host_user.set_password(login_password)
    db.session.add(host_user)
    db.session.flush()

    host = HostCompany(
        company_name=company_name,
        contact_person=contact_person or None,
        contact_email=contact_email,
        contact_phone=contact_phone or None,
        address=address or None,
        login_user_id=host_user.id,
        created_by=current_user.id,
    )
    db.session.add(host)
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='host_company_created',
        entity_type='host_company',
        entity_id=host.id,
        details={'company_name': host.company_name, 'login_user_id': host.login_user_id},
    )

    flash('Host company created. The host can now log in with the configured email/password.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/hosts/assign-intern', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_assignments')
def assign_intern_to_host():
    intern_ids = [int(x) for x in request.form.getlist('intern_ids') if x.isdigit()]
    host_company_id = request.form.get('host_company_id', type=int)
    cohort_id = request.form.get('cohort_id', type=int) or None

    host = HostCompany.query.filter_by(id=host_company_id, is_active=True).first()
    if not host or not intern_ids:
        flash('Please select a host company and at least one intern.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    if cohort_id and not Cohort.query.get(cohort_id):
        flash('Selected cohort does not exist.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    assigned = skipped = 0
    now = datetime.utcnow()

    for intern_id in intern_ids:
        intern = User.query.filter_by(id=intern_id, role='intern', is_deleted=False).first()
        if not intern:
            skipped += 1
            continue

        for item in InternPlacement.query.filter_by(intern_id=intern_id, is_active=True).all():
            item.is_active = False
            item.ended_at = now

        placement = InternPlacement(
            intern_id=intern_id,
            host_company_id=host_company_id,
            cohort_id=cohort_id,
            assigned_by=current_user.id,
            is_active=True,
        )
        db.session.add(placement)
        assigned += 1

        Notification.create_notification(
            user_id=intern.id,
            title='Host Placement Updated',
            message=f'You have been assigned to host company: {host.company_name}.',
            notification_type='intern_host_assignment',
            related_type='host_company',
            related_id=host.id,
        )

    db.session.commit()

    if host.login_user_id and assigned:
        Notification.create_notification(
            user_id=host.login_user_id,
            title='New Interns Assigned',
            message=f'{assigned} intern(s) have been assigned to your company.',
            notification_type='host_intern_assignment',
            related_type='host_company',
            related_id=host.id,
        )

    log_audit_event(
        actor_user_id=current_user.id,
        action='intern_host_assignment_updated',
        entity_type='host_company',
        entity_id=host_company_id,
        details={'host_company_id': host_company_id, 'assigned': assigned, 'cohort_id': cohort_id},
    )

    parts = [f'{assigned} intern(s) assigned to {host.company_name}.']
    if skipped:
        parts.append(f'{skipped} skipped (not found).')
    flash(' '.join(parts), 'success' if assigned else 'warning')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/groups/<int:group_id>/edit', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def edit_group(group_id):
    group = InternGroup.query.get_or_404(group_id)

    name = (request.form.get('name') or '').strip()
    education_type = (request.form.get('education_type') or 'mixed').strip().lower()
    description = (request.form.get('description') or '').strip()

    if not name:
        flash('Group name is required.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    if education_type not in ['varsity', 'tvet', 'mixed']:
        flash('Invalid education type.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    group.name = name
    group.education_type = education_type
    group.description = description or None

    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='intern_group_updated',
        entity_type='intern_group',
        entity_id=group.id,
        details={'name': group.name, 'education_type': group.education_type},
    )

    flash('Intern group updated successfully.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/groups/<int:group_id>/archive', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def archive_group(group_id):
    group = InternGroup.query.get_or_404(group_id)
    group.is_active = False
    group.archived_at = datetime.utcnow()
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='intern_group_archived',
        entity_type='intern_group',
        entity_id=group.id,
        details={'name': group.name},
    )

    flash('Intern group archived.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/cohorts/<int:cohort_id>/edit', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def edit_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)

    name = (request.form.get('name') or '').strip()
    status = (request.form.get('status') or 'active').strip().lower()
    notes = (request.form.get('notes') or '').strip()

    if not name:
        flash('Cohort name is required.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    if status not in ['active', 'completed', 'archived']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    cohort.name = name
    cohort.status = status
    cohort.notes = notes or None
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='cohort_updated',
        entity_type='cohort',
        entity_id=cohort.id,
        details={'name': cohort.name, 'status': cohort.status},
    )

    flash('Cohort updated successfully.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/cohorts/<int:cohort_id>/archive', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def archive_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    cohort.is_active = False
    cohort.archived_at = datetime.utcnow()
    cohort.status = 'archived'
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='cohort_archived',
        entity_type='cohort',
        entity_id=cohort.id,
        details={'name': cohort.name},
    )

    flash('Cohort archived.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/cohorts/<int:cohort_id>/restore', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_intern_operations')
def restore_cohort(cohort_id):
    cohort = Cohort.query.get_or_404(cohort_id)
    cohort.is_active = True
    cohort.archived_at = None
    if cohort.status == 'archived':
        cohort.status = 'active'
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='cohort_restored',
        entity_type='cohort',
        entity_id=cohort.id,
        details={'name': cohort.name},
    )

    flash('Cohort restored.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/hosts/<int:host_id>/edit', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_host_companies')
def edit_host_company(host_id):
    host = HostCompany.query.get_or_404(host_id)

    host.company_name = (request.form.get('company_name') or '').strip() or host.company_name
    host.contact_person = (request.form.get('contact_person') or '').strip() or None
    host.contact_phone = (request.form.get('contact_phone') or '').strip() or None
    host.address = (request.form.get('address') or '').strip() or None
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='host_company_updated',
        entity_type='host_company',
        entity_id=host.id,
        details={'company_name': host.company_name},
    )

    flash('Host company updated.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/hosts/<int:host_id>/archive', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_host_companies')
def archive_host_company(host_id):
    host = HostCompany.query.get_or_404(host_id)
    host.is_active = False
    host.archived_at = datetime.utcnow()
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='host_company_archived',
        entity_type='host_company',
        entity_id=host.id,
        details={'company_name': host.company_name},
    )

    flash('Host company archived.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/hosts/<int:host_id>/restore', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_host_companies')
def restore_host_company(host_id):
    host = HostCompany.query.get_or_404(host_id)
    host.is_active = True
    host.archived_at = None
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='host_company_restored',
        entity_type='host_company',
        entity_id=host.id,
        details={'company_name': host.company_name},
    )

    flash('Host company restored.', 'success')
    return redirect(url_for('intern_management.dashboard'))


@bp.route('/hosts/<int:host_id>/reset-password', methods=['POST'])
@login_required
@staff_required
@permission_required('manage_host_companies')
def reset_host_password(host_id):
    """Reset host account password and force immediate password change on next login."""
    host = HostCompany.query.get_or_404(host_id)
    new_password = (request.form.get('new_password') or '').strip() or 'JubaHost2026!'

    if not host.login_user:
        flash('This host company has no linked login user.', 'danger')
        return redirect(url_for('intern_management.dashboard'))

    host.login_user.set_password(new_password)
    host.login_user.requires_password_change = True
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        action='host_password_reset',
        entity_type='host_company',
        entity_id=host.id,
        details={'login_user_id': host.login_user_id},
    )

    Notification.create_notification(
        user_id=host.login_user_id,
        title='Password Reset',
        message='Your host account password was reset by Juba staff. Please log in and change your password.',
        notification_type='host_password_reset',
        related_type='host_company',
        related_id=host.id,
    )

    flash('Host password reset successfully.', 'success')
    return redirect(url_for('intern_management.dashboard'))
