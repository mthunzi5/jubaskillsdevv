from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.permission import RolePermission
from app.models.deletion_history import DeletionHistory
from app.models.soft_delete import SoftDelete
from app.models.timesheet import Timesheet
from app.models.intern_management import Cohort, HostCompany, InternPlacement, CohortMember, InternGroup
from app.models.job_application import JobApplication, JobPost
from app.models.notification import Notification
from app.models.induction import InductionPortalSettings, InductionExportAuditLog
from app.utils.audit import log_audit_event
from app.utils.decorators import admin_required
from app.utils.helpers import save_deletion_history
from datetime import datetime
import json

PERMISSION_KEYS = [
    'manage_job_posts',
    'manage_intern_operations',
    'manage_host_companies',
    'manage_assignments',
    'view_host_dashboard',
]

ROLE_CHOICES = ['admin', 'staff', 'host_company', 'intern']

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    # Trigger automatic timesheet completeness reminders for current month.
    from app.routes.staff import _send_missing_timesheet_reminders
    _send_missing_timesheet_reminders(datetime.utcnow().strftime('%Y-%m'))

    total_users = User.query.filter_by(is_deleted=False).count()
    total_admins = User.query.filter_by(role='admin', is_deleted=False).count()
    total_staff = User.query.filter_by(role='staff', is_deleted=False).count()
    total_interns = User.query.filter_by(role='intern', is_deleted=False).count()
    pending_approvals = SoftDelete.query.filter_by(approved=False).count()
    total_cohorts = Cohort.query.filter_by(is_active=True).count()
    total_hosts = HostCompany.query.filter_by(is_active=True).count()
    total_active_placements = InternPlacement.query.filter_by(is_active=True).count()
    unassigned_interns = (
        User.query
        .filter_by(role='intern', is_deleted=False)
        .outerjoin(InternPlacement, (InternPlacement.intern_id == User.id) & (InternPlacement.is_active == True))
        .filter(InternPlacement.id.is_(None))
        .count()
    )
    varsity_interns = User.query.filter_by(role='intern', intern_type='varsity', is_deleted=False).count()
    tvet_interns = User.query.filter_by(role='intern', intern_type='tvet', is_deleted=False).count()
    mixed_interns = User.query.filter_by(role='intern', intern_type='mixed', is_deleted=False).count()

    total_job_posts = JobPost.query.filter_by(is_archived=False).count()
    open_job_posts = JobPost.query.filter_by(is_open=True, is_archived=False).count()
    total_job_applications = JobApplication.query.filter_by(is_deleted=False).count()
    submitted_applications = JobApplication.query.filter_by(status='submitted', is_deleted=False).count()
    under_review_applications = JobApplication.query.filter_by(status='under_review', is_deleted=False).count()
    
    recent_deletions = DeletionHistory.query.order_by(DeletionHistory.deletion_date.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_admins=total_admins,
                         total_staff=total_staff,
                         total_interns=total_interns,
                         pending_approvals=pending_approvals,
                         total_cohorts=total_cohorts,
                         total_hosts=total_hosts,
                         total_active_placements=total_active_placements,
                         unassigned_interns=unassigned_interns,
                         varsity_interns=varsity_interns,
                         tvet_interns=tvet_interns,
                         mixed_interns=mixed_interns,
                         total_job_posts=total_job_posts,
                         open_job_posts=open_job_posts,
                         total_job_applications=total_job_applications,
                         submitted_applications=submitted_applications,
                         under_review_applications=under_review_applications,
                         recent_deletions=recent_deletions)

@bp.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    role_filter = request.args.get('role', 'all')
    intern_type_filter = request.args.get('intern_type', 'all')
    assignment_filter = request.args.get('assignment', 'all')
    host_filter = request.args.get('host_company_id', 'all')
    
    query = User.query.filter_by(is_deleted=False)
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)

    if role_filter == 'intern' and intern_type_filter in ['varsity', 'tvet', 'mixed']:
        query = query.filter_by(intern_type=intern_type_filter)
    
    users = query.order_by(User.created_at.desc()).all()

    groups = InternGroup.query.filter_by(is_active=True).order_by(InternGroup.name.asc()).all()
    cohorts = Cohort.query.filter_by(is_active=True).order_by(Cohort.created_at.desc()).all()
    hosts = HostCompany.query.filter_by(is_active=True).order_by(HostCompany.company_name.asc()).all()

    intern_context = {}
    filtered_users = []
    for user in users:
        latest_membership = None
        active_placement = None
        linked_host_company = None

        if user.role == 'intern':
            latest_membership = (
                CohortMember.query
                .join(Cohort, CohortMember.cohort_id == Cohort.id)
                .filter(CohortMember.intern_id == user.id, Cohort.is_active == True)
                .order_by(CohortMember.created_at.desc())
                .first()
            )
            active_placement = (
                InternPlacement.query
                .filter_by(intern_id=user.id, is_active=True)
                .order_by(InternPlacement.assigned_at.desc())
                .first()
            )

            if host_filter != 'all':
                if host_filter == 'unassigned':
                    if active_placement:
                        continue
                else:
                    try:
                        host_filter_id = int(host_filter)
                    except ValueError:
                        host_filter_id = None
                    if not host_filter_id or not active_placement or active_placement.host_company_id != host_filter_id:
                        continue

            if assignment_filter == 'assigned' and not (latest_membership or active_placement):
                continue
            if assignment_filter == 'unassigned' and (latest_membership or active_placement):
                continue

            filtered_users.append(user)

        elif user.role == 'host_company':
            linked_host_company = HostCompany.query.filter_by(login_user_id=user.id).first()
            filtered_users.append(user)
        else:
            filtered_users.append(user)

        intern_context[user.id] = {
            'latest_membership': latest_membership,
            'active_placement': active_placement,
            'linked_host_company': linked_host_company,
        }

    return render_template(
        'admin/users.html',
        users=filtered_users,
        role_filter=role_filter,
        intern_type_filter=intern_type_filter,
        assignment_filter=assignment_filter,
        host_filter=host_filter,
        groups=groups,
        cohorts=cohorts,
        hosts=hosts,
        intern_context=intern_context,
    )


@bp.route('/users/<int:user_id>/intern-info', methods=['POST'])
@login_required
@admin_required
def update_intern_info(user_id):
    """Update intern profile information from admin users page."""
    user = User.query.get_or_404(user_id)
    if user.role != 'intern':
        flash('Only intern users can be updated here.', 'danger')
        return redirect(url_for('admin.users', role='intern'))

    id_number = (request.form.get('id_number') or '').strip()
    name = (request.form.get('name') or '').strip()
    surname = (request.form.get('surname') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    intern_type = (request.form.get('intern_type') or '').strip().lower()

    if id_number and (len(id_number) != 13 or not id_number.isdigit()):
        flash('ID number must be exactly 13 digits.', 'danger')
        return redirect(url_for('admin.users', role='intern'))

    if intern_type not in ['varsity', 'tvet', 'mixed']:
        flash('Intern type must be varsity, tvet, or mixed.', 'danger')
        return redirect(url_for('admin.users', role='intern'))

    existing = User.query.filter(
        User.id != user.id,
        User.id_number == id_number,
        User.is_deleted == False,
    ).first()
    if existing:
        flash('Another intern already uses that ID number.', 'danger')
        return redirect(url_for('admin.users', role='intern'))

    old_values = {
        'name': user.name,
        'surname': user.surname,
        'phone': user.phone,
        'id_number': user.id_number,
        'intern_type': user.intern_type,
    }

    user.name = name or user.name
    user.surname = surname or user.surname
    user.phone = phone or None
    if id_number:
        user.id_number = id_number
    user.intern_type = intern_type

    db.session.commit()

    Notification.create_notification(
        user_id=user.id,
        title='Profile Updated',
        message='Your intern profile details were updated by admin.',
        notification_type='admin_profile_update',
        related_type='intern',
        related_id=user.id,
    )

    log_audit_event(
        actor_user_id=current_user.id,
        action='admin_updated_intern_info',
        entity_type='user',
        entity_id=user.id,
        details={
            'before': old_values,
            'after': {
                'name': user.name,
                'surname': user.surname,
                'phone': user.phone,
                'id_number': user.id_number,
                'intern_type': user.intern_type,
            },
        },
    )

    flash('Intern information updated successfully.', 'success')
    return redirect(url_for('admin.users', role='intern'))


@bp.route('/users/<int:user_id>/assignments', methods=['POST'])
@login_required
@admin_required
def update_intern_assignments(user_id):
    """Update intern cohort membership and host placement from admin users page."""
    user = User.query.get_or_404(user_id)
    if user.role != 'intern':
        flash('Assignments can only be updated for intern users.', 'danger')
        return redirect(url_for('admin.users', role='intern'))

    cohort_id = request.form.get('cohort_id', type=int)
    group_id = request.form.get('group_id', type=int)
    host_company_id = request.form.get('host_company_id', type=int)

    selected_group = None
    if group_id:
        selected_group = InternGroup.query.filter_by(id=group_id, is_active=True).first()
        if not selected_group:
            flash('Selected group does not exist or is inactive.', 'danger')
            return redirect(url_for('admin.users', role='intern'))

    selected_cohort = None
    if cohort_id:
        selected_cohort = Cohort.query.filter_by(id=cohort_id, is_active=True).first()
        if not selected_cohort:
            flash('Selected cohort does not exist or is inactive.', 'danger')
            return redirect(url_for('admin.users', role='intern'))

        if selected_group and selected_cohort.group_id != selected_group.id:
            flash('Selected cohort does not belong to the selected group.', 'danger')
            return redirect(url_for('admin.users', role='intern'))

        if not selected_group:
            selected_group = selected_cohort.group

        cohort_type = selected_cohort.group.education_type if selected_cohort.group else 'mixed'
        intern_type = (user.intern_type or 'mixed').lower()
        if cohort_type != 'mixed' and intern_type != cohort_type:
            flash(f'Intern type ({intern_type}) does not match cohort type ({cohort_type}).', 'danger')
            return redirect(url_for('admin.users', role='intern'))

    if selected_group and selected_group.education_type in ['varsity', 'tvet', 'mixed']:
        user.intern_type = selected_group.education_type

    selected_host = None
    if host_company_id:
        selected_host = HostCompany.query.filter_by(id=host_company_id, is_active=True).first()
        if not selected_host:
            flash('Selected host company does not exist or is inactive.', 'danger')
            return redirect(url_for('admin.users', role='intern'))

    # Replace cohort memberships with the selected one (or clear if omitted).
    CohortMember.query.filter_by(intern_id=user.id).delete()
    if selected_cohort:
        db.session.add(CohortMember(cohort_id=selected_cohort.id, intern_id=user.id, created_by=current_user.id))

    # Replace active host placement with selected host (or clear if omitted).
    current_active = InternPlacement.query.filter_by(intern_id=user.id, is_active=True).all()
    for placement in current_active:
        placement.is_active = False
        placement.ended_at = datetime.utcnow()

    new_placement = None
    if selected_host:
        new_placement = InternPlacement(
            intern_id=user.id,
            host_company_id=selected_host.id,
            cohort_id=selected_cohort.id if selected_cohort else None,
            assigned_by=current_user.id,
            is_active=True,
        )
        db.session.add(new_placement)

    db.session.commit()

    Notification.create_notification(
        user_id=user.id,
        title='Assignment Updated',
        message='Your cohort and/or host company assignment has been updated by admin.',
        notification_type='admin_assignment_update',
        related_type='intern',
        related_id=user.id,
    )

    if new_placement and selected_host and selected_host.login_user_id:
        Notification.create_notification(
            user_id=selected_host.login_user_id,
            title='Intern Assignment Updated',
            message=f'{user.name or "Intern"} {user.surname or ""} is now assigned to your company.',
            notification_type='host_intern_assignment',
            related_type='intern',
            related_id=user.id,
        )

    log_audit_event(
        actor_user_id=current_user.id,
        action='admin_updated_intern_assignments',
        entity_type='user',
        entity_id=user.id,
        details={
            'group_id': selected_group.id if selected_group else None,
            'cohort_id': selected_cohort.id if selected_cohort else None,
            'host_company_id': selected_host.id if selected_host else None,
        },
    )

    flash('Intern assignment updated successfully.', 'success')
    return redirect(url_for('admin.users', role='intern'))

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user"""
    if request.method == 'POST':
        role = request.form.get('role')
        
        if role == 'intern':
            # Create intern
            id_number = request.form.get('id_number')
            intern_type = (request.form.get('intern_type') or '').strip().lower()
            
            # Validate ID number
            if len(id_number) != 13 or not id_number.isdigit():
                flash('ID number must be exactly 13 digits.', 'danger')
                return redirect(url_for('admin.create_user'))
            
            # Check if ID already exists
            existing = User.query.filter_by(id_number=id_number).first()
            if existing:
                flash('Intern with this ID number already exists.', 'danger')
                return redirect(url_for('admin.create_user'))

            if intern_type not in ['varsity', 'tvet', 'mixed']:
                flash('Intern type must be varsity, tvet, or mixed.', 'danger')
                return redirect(url_for('admin.create_user'))
            
            user = User(
                id_number=id_number,
                intern_type=intern_type,
                role='intern',
                first_login=True,
                is_profile_complete=False,
                created_by=current_user.id
            )
            user.set_password('JubaFuture2025')
            
        else:
            # Create admin or staff
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            
            # Check if email already exists
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('User with this email already exists.', 'danger')
                return redirect(url_for('admin.create_user'))
            
            user = User(
                email=email,
                name=name,
                role=role,
                is_profile_complete=True,
                first_login=False,
                created_by=current_user.id
            )
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'{role.capitalize()} created successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/create_user.html')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.surname = request.form.get('surname')
        user.email = request.form.get('email') if user.role != 'intern' else user.email
        user.phone = request.form.get('phone')
        
        if user.role == 'intern':
            intern_type = (request.form.get('intern_type') or '').strip().lower()
            if intern_type not in ['varsity', 'tvet', 'mixed']:
                flash('Intern type must be varsity, tvet, or mixed.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            user.intern_type = intern_type
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/edit_user.html', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user with reason"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason')
    
    if not reason:
        flash('Deletion reason is required.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Save user details before deletion
    user_details = user.to_dict()
    
    # Mark as deleted
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()
    
    # Save deletion history
    save_deletion_history(
        deleted_by=current_user.id,
        item_type='user',
        item_id=user.id,
        reason=reason,
        item_details=user_details,
        is_permanent=True
    )
    
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/deletion-history')
@login_required
@admin_required
def deletion_history():
    """View deletion history"""
    history = DeletionHistory.query.order_by(DeletionHistory.deletion_date.desc()).all()
    return render_template('admin/deletion_history.html', history=history)

@bp.route('/pending-deletions')
@login_required
@admin_required
def pending_deletions():
    """View pending deletion approvals"""
    pending = SoftDelete.query.filter_by(approved=False).order_by(SoftDelete.deleted_at.desc()).all()
    
    # Get associated items
    pending_items = []
    for item in pending:
        if item.item_type == 'timesheet':
            timesheet = Timesheet.query.get(item.item_id)
            if timesheet:
                pending_items.append({
                    'soft_delete': item,
                    'item': timesheet,
                    'type': 'timesheet'
                })
    
    return render_template('admin/pending_deletions.html', pending_items=pending_items)


@bp.route('/permissions', methods=['GET'])
@login_required
@admin_required
def permissions_matrix():
    """Manage per-role permission overrides."""
    entries = RolePermission.query.order_by(RolePermission.role.asc(), RolePermission.permission.asc()).all()
    matrix = {role: {} for role in ROLE_CHOICES}

    for role in ROLE_CHOICES:
        for permission in PERMISSION_KEYS:
            matrix[role][permission] = None

    for entry in entries:
        if entry.role in matrix:
            matrix[entry.role][entry.permission] = entry.allowed

    return render_template(
        'admin/permissions.html',
        roles=ROLE_CHOICES,
        permissions=PERMISSION_KEYS,
        matrix=matrix,
    )


@bp.route('/permissions/update', methods=['POST'])
@login_required
@admin_required
def update_permissions_matrix():
    """Persist explicit permission overrides by role."""
    role = (request.form.get('role') or '').strip()

    if role not in ROLE_CHOICES:
        flash('Invalid role selected.', 'danger')
        return redirect(url_for('admin.permissions_matrix'))

    for permission in PERMISSION_KEYS:
        decision = request.form.get(f'{permission}_decision')
        existing = RolePermission.query.filter_by(role=role, permission=permission).first()

        if decision == 'default':
            if existing:
                db.session.delete(existing)
            continue

        allowed = decision == 'allow'
        if existing:
            existing.allowed = allowed
        else:
            db.session.add(RolePermission(role=role, permission=permission, allowed=allowed))

    db.session.commit()
    flash(f'Permission overrides updated for role: {role}.', 'success')
    return redirect(url_for('admin.permissions_matrix'))

@bp.route('/pending-deletions/<int:soft_delete_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_deletion(soft_delete_id):
    """Approve permanent deletion"""
    soft_delete = SoftDelete.query.get_or_404(soft_delete_id)
    
    if soft_delete.item_type == 'timesheet':
        timesheet = Timesheet.query.get(soft_delete.item_id)
        if timesheet:
            # Save to deletion history
            save_deletion_history(
                deleted_by=soft_delete.deleted_by,
                item_type='timesheet',
                item_id=timesheet.id,
                reason=soft_delete.deletion_reason,
                item_details=timesheet.to_dict(),
                is_permanent=True
            )
            
            # Permanently delete
            db.session.delete(timesheet)
    
    # Mark as approved
    soft_delete.approved = True
    soft_delete.approved_by = current_user.id
    soft_delete.approved_at = datetime.utcnow()
    
    db.session.commit()
    flash('Deletion approved and item permanently deleted.', 'success')
    return redirect(url_for('admin.pending_deletions'))

@bp.route('/pending-deletions/<int:soft_delete_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_deletion(soft_delete_id):
    """Reject deletion request"""
    soft_delete = SoftDelete.query.get_or_404(soft_delete_id)
    
    if soft_delete.item_type == 'timesheet':
        timesheet = Timesheet.query.get(soft_delete.item_id)
        if timesheet:
            # Restore item
            timesheet.is_deleted = False
            timesheet.deleted_at = None
            timesheet.pending_permanent_delete = False
    
    # Remove soft delete request
    db.session.delete(soft_delete)
    db.session.commit()
    
    flash('Deletion request rejected and item restored.', 'success')
    return redirect(url_for('admin.pending_deletions'))


@bp.route('/induction/portal-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_induction_portal():
    """Admin page to open/close the induction portal."""
    settings = InductionPortalSettings.get_settings()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'toggle':
            was_open = settings.is_open
            settings.toggle_open_close()
            status = 'closed' if was_open else 'opened'
            flash(f'Induction portal has been {status}.', 'success')
    
    return render_template(
        'admin/induction_portal_settings.html',
        settings=settings,
    )


@bp.route('/induction/audit-logs', methods=['GET'])
@login_required
@admin_required
def induction_audit_logs():
    """Admin page to view induction export audit logs."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = InductionExportAuditLog.query.order_by(InductionExportAuditLog.exported_at.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return render_template(
        'admin/induction_audit_logs.html',
        logs=logs,
    )
