from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import current_user, login_required
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from app import db
from app.models.intern_management import HostCompany, InternPlacement, Cohort
from app.models.timesheet import (
    Timesheet,
    TimesheetPolicySettings,
    TimesheetNonWorkingMonth,
    HostInternMonthlyFeedback,
)
from app.models.notification import Notification
from app.utils.decorators import host_company_required, permission_required
from app.utils.audit import log_audit_event

bp = Blueprint('host_company', __name__, url_prefix='/host-company')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _validate_submission_month(submission_month):
    if not submission_month or len(submission_month) != 7 or '-' not in submission_month:
        return False
    return True


def _enforce_month_policy_or_flash(submission_month):
    policy = TimesheetPolicySettings.get_settings()
    current_month = datetime.utcnow().strftime('%Y-%m')

    if policy.block_future_months and submission_month > current_month:
        flash('Submitting for future months is currently blocked by policy.', 'danger')
        return False

    if policy.lock_before_month and submission_month < policy.lock_before_month:
        flash(f'Submissions before {policy.lock_before_month} are locked by policy.', 'danger')
        return False

    return True

@bp.route('/dashboard')
@login_required
@host_company_required
@permission_required('view_host_dashboard')
def dashboard():
    """Host company dashboard showing assigned interns grouped by cohort."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()

    cohorts_data = {}
    total_assigned = 0
    submitted_this_month = 0
    not_worked_this_month = 0
    feedback_this_month = 0
    pending_this_month = 0
    current_month = datetime.utcnow().strftime('%Y-%m')

    if host:
        # Get all active placements for this host
        placements = (
            InternPlacement.query
            .filter_by(host_company_id=host.id, is_active=True)
            .order_by(InternPlacement.assigned_at.desc())
            .all()
        )

        unique_intern_ids = set()
        
        # Group interns by cohort
        for placement in placements:
            cohort = placement.cohort
            if cohort:
                if cohort.id not in cohorts_data:
                    cohorts_data[cohort.id] = {
                        'cohort': cohort,
                        'interns': []
                    }
                cohorts_data[cohort.id]['interns'].append(placement)

            unique_intern_ids.add(placement.intern_id)

        total_assigned = len(unique_intern_ids)

        submitted_this_month = (
            Timesheet.query
            .filter_by(host_company_id=host.id, submission_month=current_month, is_deleted=False)
            .with_entities(Timesheet.intern_id)
            .distinct()
            .count()
        )

        not_worked_this_month = (
            TimesheetNonWorkingMonth.query
            .filter_by(host_company_id=host.id, submission_month=current_month)
            .with_entities(TimesheetNonWorkingMonth.intern_id)
            .distinct()
            .count()
        )

        feedback_this_month = (
            HostInternMonthlyFeedback.query
            .filter_by(host_company_id=host.id, submission_month=current_month)
            .with_entities(HostInternMonthlyFeedback.intern_id)
            .distinct()
            .count()
        )

        pending_this_month = max(total_assigned - submitted_this_month - not_worked_this_month, 0)

    return render_template(
        'host_company/dashboard.html',
        host=host,
        cohorts_data=cohorts_data,
        current_month=current_month,
        total_assigned=total_assigned,
        submitted_this_month=submitted_this_month,
        not_worked_this_month=not_worked_this_month,
        feedback_this_month=feedback_this_month,
        pending_this_month=pending_this_month,
    )


@bp.route('/interns')
@login_required
@host_company_required
def interns_list():
    """Flat list view of all interns currently assigned to this host company."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    placements = (
        InternPlacement.query
        .filter_by(host_company_id=host.id, is_active=True)
        .order_by(InternPlacement.assigned_at.desc())
        .all()
    )

    seen = set()
    rows = []
    for placement in placements:
        if placement.intern_id in seen:
            continue
        seen.add(placement.intern_id)
        rows.append(placement)

    return render_template('host_company/interns.html', host=host, placements=rows)


@bp.route('/cohorts/<int:cohort_id>/interns')
@login_required
@host_company_required
def cohort_interns(cohort_id):
    """Return active interns for this host in a specific cohort."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        return jsonify({'ok': False, 'message': 'Host company not found'}), 404

    month = (request.args.get('month') or '').strip()

    placements = (
        InternPlacement.query
        .filter_by(host_company_id=host.id, cohort_id=cohort_id, is_active=True)
        .order_by(InternPlacement.assigned_at.desc())
        .all()
    )

    interns = []
    seen = set()
    for placement in placements:
        if not placement.intern or placement.intern.id in seen:
            continue
        seen.add(placement.intern.id)
        existing = None
        if month and len(month) == 7 and '-' in month:
            existing = (
                Timesheet.query
                .filter_by(intern_id=placement.intern.id, submission_month=month, is_deleted=False)
                .order_by(Timesheet.submission_date.desc())
                .first()
            )

        submitted_by = None
        submitted_at = None
        if existing:
            submitted_by = 'host' if existing.host_company_id else 'intern'
            submitted_at = existing.submission_date.strftime('%Y-%m-%d %H:%M') if existing.submission_date else None

        interns.append({
            'id': placement.intern.id,
            'name': placement.intern.name or '',
            'surname': placement.intern.surname or '',
            'id_number': placement.intern.id_number or '',
            'intern_type': placement.intern.intern_type or 'mixed',
            'already_submitted': bool(existing),
            'submitted_by': submitted_by,
            'submitted_at': submitted_at,
        })

    return jsonify({'ok': True, 'interns': interns})


@bp.route('/timesheets/submit', methods=['GET', 'POST'])
@login_required
@host_company_required
def submit_timesheets():
    """Host company submission of timesheets for a cohort/month."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))
    
    # Get unique cohorts this host has interns in
    active_placements = (
        InternPlacement.query
        .filter_by(host_company_id=host.id, is_active=True)
        .all()
    )
    
    cohort_ids = {p.cohort_id for p in active_placements if p.cohort_id}
    cohorts = Cohort.query.filter(Cohort.id.in_(cohort_ids)).all() if cohort_ids else []
    
    if request.method == 'POST':
        cohort_id = request.form.get('cohort_id', type=int)
        submission_month = request.form.get('submission_month')
        selected_interns = request.form.getlist('interns')
        
        if not cohort_id or not submission_month or not selected_interns:
            flash('Please select cohort, month, and at least one intern.', 'danger')
            return redirect(url_for('host_company.submit_timesheets'))

        if not _validate_submission_month(submission_month):
            flash('Please provide a valid submission month (YYYY-MM).', 'danger')
            return redirect(url_for('host_company.submit_timesheets'))

        if not _enforce_month_policy_or_flash(submission_month):
            return redirect(url_for('host_company.submit_timesheets'))
        
        # Validate cohort belongs to this host
        cohort = Cohort.query.get_or_404(cohort_id)
        host_interns_in_cohort = {
            p.intern_id for p in active_placements
            if p.cohort_id == cohort_id
        }
        
        submitted_count = 0
        errors = []
        
        for intern_id_str in selected_interns:
            try:
                intern_id = int(intern_id_str)
            except ValueError:
                continue
            
            if intern_id not in host_interns_in_cohort:
                errors.append(f'Intern {intern_id} not assigned to this cohort at your host.')
                continue

            existing = (
                Timesheet.query
                .filter_by(intern_id=intern_id, submission_month=submission_month, is_deleted=False)
                .order_by(Timesheet.submission_date.desc())
                .first()
            )
            if existing:
                submitter_label = 'host company' if existing.host_company_id else 'intern'
                errors.append(f'Intern {intern_id} already has a {submission_month} timesheet submitted by {submitter_label}.')
                continue
            
            file = request.files.get(f'timesheet_{intern_id}')
            if not file or file.filename == '':
                errors.append(f'No file selected for intern {intern_id}.')
                continue
            
            if not allowed_file(file.filename):
                errors.append(f'File type not allowed for intern {intern_id}. Use PDF, DOC, DOCX, XLS, XLSX.')
                continue
            
            # Save file using absolute path so DB records are portable
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
            uploads_dir = os.path.join(base_dir, 'app', 'static', 'submissions')
            os.makedirs(uploads_dir, exist_ok=True)
            
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            saved_filename = f"{cohort_id}_{intern_id}_{timestamp}_{filename}"
            file_path = os.path.join(uploads_dir, saved_filename)
            
            file.save(file_path)
            
            # Create timesheet record
            try:
                year = int(submission_month.split('-')[0])
            except (ValueError, IndexError):
                errors.append(f'Invalid month format for intern {intern_id}.')
                continue
            timesheet = Timesheet(
                intern_id=intern_id,
                cohort_id=cohort_id,
                host_company_id=host.id,
                submitted_by=current_user.id,
                filename=saved_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                submission_month=submission_month,
                submission_year=year,
                submission_date=datetime.utcnow()
            )
            db.session.add(timesheet)
            submitted_count += 1
        
        db.session.commit()
        
        # Send notifications to interns
        for intern_id_str in selected_interns:
            try:
                intern_id = int(intern_id_str)
                if intern_id in host_interns_in_cohort:
                    Notification.create_notification(
                        user_id=intern_id,
                        title='Timesheet Submitted',
                        message=f'{host.company_name} submitted your timesheet for {submission_month}.',
                        notification_type='timesheet_submitted',
                        related_type='timesheet',
                        related_id=None,
                    )
            except:
                pass
        
        log_audit_event(
            actor_user_id=current_user.id,
            action='host_submitted_cohort_timesheets',
            entity_type='cohort',
            entity_id=cohort_id,
            details={
                'host_company_id': host.id,
                'submission_month': submission_month,
                'interns_submitted': submitted_count,
                'errors': errors,
            },
        )
        
        flash(f'Submitted {submitted_count} timesheet(s) successfully.', 'success')
        if errors:
            flash('Errors: ' + ' | '.join(errors), 'warning')
        return redirect(url_for('host_company.submit_timesheets'))
    
    return render_template('host_company/submit_timesheets.html', cohorts=cohorts)


@bp.route('/timesheets/action-center', methods=['GET', 'POST'])
@login_required
@host_company_required
def bulk_action_center():
    """Bulk month operations: upload missing, replace, or mark not worked with reason."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    active_placements = (
        InternPlacement.query
        .filter_by(host_company_id=host.id, is_active=True)
        .all()
    )
    cohort_ids = {p.cohort_id for p in active_placements if p.cohort_id}
    cohorts = Cohort.query.filter(Cohort.id.in_(cohort_ids)).order_by(Cohort.name.asc()).all() if cohort_ids else []

    selected_month = (request.values.get('submission_month') or datetime.utcnow().strftime('%Y-%m')).strip()
    selected_cohort_id = request.values.get('cohort_id', type=int)

    if request.method == 'POST':
        if not selected_cohort_id or not _validate_submission_month(selected_month):
            flash('Select a valid cohort and month.', 'danger')
            return redirect(url_for('host_company.bulk_action_center'))

        if not _enforce_month_policy_or_flash(selected_month):
            return redirect(url_for('host_company.bulk_action_center', cohort_id=selected_cohort_id, submission_month=selected_month))

        processed = 0
        warnings = []

        placements = (
            InternPlacement.query
            .filter_by(host_company_id=host.id, cohort_id=selected_cohort_id, is_active=True)
            .all()
        )

        for placement in placements:
            intern = placement.intern
            if not intern:
                continue

            replace_existing = request.form.get(f'replace_{intern.id}') == 'on'
            mark_not_worked = request.form.get(f'not_worked_{intern.id}') == 'on'
            not_worked_reason = (request.form.get(f'not_worked_reason_{intern.id}') or '').strip()
            feedback_comments = (request.form.get(f'feedback_comments_{intern.id}') or '').strip() or None
            file = request.files.get(f'timesheet_{intern.id}')

            existing = (
                Timesheet.query
                .filter_by(intern_id=intern.id, submission_month=selected_month, is_deleted=False)
                .order_by(Timesheet.submission_date.desc())
                .first()
            )

            if mark_not_worked:
                if not not_worked_reason:
                    warnings.append(f'{intern.name} {intern.surname}: add reason when marking not worked.')
                else:
                    if existing and replace_existing:
                        existing.is_deleted = True
                        existing.deleted_at = datetime.utcnow()
                        existing.deleted_by = current_user.id
                        existing.pending_permanent_delete = False
                    elif existing and not replace_existing:
                        warnings.append(f'{intern.name} {intern.surname}: already has submitted timesheet; tick replace to override.')
                    else:
                        status = TimesheetNonWorkingMonth.query.filter_by(
                            host_company_id=host.id,
                            cohort_id=selected_cohort_id,
                            intern_id=intern.id,
                            submission_month=selected_month,
                        ).first()
                        if not status:
                            status = TimesheetNonWorkingMonth(
                                host_company_id=host.id,
                                cohort_id=selected_cohort_id,
                                intern_id=intern.id,
                                submission_month=selected_month,
                                created_by=current_user.id,
                                reason=not_worked_reason,
                            )
                            db.session.add(status)
                        else:
                            status.reason = not_worked_reason
                        processed += 1

            if file and file.filename:
                if not allowed_file(file.filename):
                    warnings.append(f'{intern.name} {intern.surname}: invalid file type.')
                else:
                    if existing and not replace_existing:
                        warnings.append(f'{intern.name} {intern.surname}: existing timesheet found; tick replace to upload new file.')
                    else:
                        if existing and replace_existing:
                            existing.is_deleted = True
                            existing.deleted_at = datetime.utcnow()
                            existing.deleted_by = current_user.id
                            existing.pending_permanent_delete = False

                        non_worked = TimesheetNonWorkingMonth.query.filter_by(
                            host_company_id=host.id,
                            cohort_id=selected_cohort_id,
                            intern_id=intern.id,
                            submission_month=selected_month,
                        ).first()
                        if non_worked:
                            db.session.delete(non_worked)

                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        uploads_dir = os.path.join(base_dir, 'app', 'static', 'submissions')
                        os.makedirs(uploads_dir, exist_ok=True)

                        filename = secure_filename(file.filename)
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        saved_filename = f"{selected_cohort_id}_{intern.id}_{timestamp}_{filename}"
                        file_path = os.path.join(uploads_dir, saved_filename)
                        file.save(file_path)

                        try:
                            year = int(selected_month.split('-')[0])
                        except (ValueError, IndexError):
                            warnings.append(f'{intern.name} {intern.surname}: invalid month format.')
                            continue

                        ts = Timesheet(
                            intern_id=intern.id,
                            cohort_id=selected_cohort_id,
                            host_company_id=host.id,
                            submitted_by=current_user.id,
                            filename=saved_filename,
                            original_filename=file.filename,
                            file_path=file_path,
                            file_size=os.path.getsize(file_path),
                            submission_month=selected_month,
                            submission_year=year,
                            submission_date=datetime.utcnow(),
                        )
                        db.session.add(ts)
                        processed += 1

            ratings = {
                'attendance_rating': request.form.get(f'attendance_{intern.id}', type=int),
                'punctuality_rating': request.form.get(f'punctuality_{intern.id}', type=int),
                'communication_rating': request.form.get(f'communication_{intern.id}', type=int),
                'task_quality_rating': request.form.get(f'task_quality_{intern.id}', type=int),
            }

            if any(v for v in ratings.values()) or feedback_comments:
                feedback = HostInternMonthlyFeedback.query.filter_by(
                    host_company_id=host.id,
                    cohort_id=selected_cohort_id,
                    intern_id=intern.id,
                    submission_month=selected_month,
                ).first()
                if not feedback:
                    feedback = HostInternMonthlyFeedback(
                        host_company_id=host.id,
                        cohort_id=selected_cohort_id,
                        intern_id=intern.id,
                        submission_month=selected_month,
                        created_by=current_user.id,
                    )
                    db.session.add(feedback)

                feedback.attendance_rating = ratings['attendance_rating']
                feedback.punctuality_rating = ratings['punctuality_rating']
                feedback.communication_rating = ratings['communication_rating']
                feedback.task_quality_rating = ratings['task_quality_rating']
                feedback.comments = feedback_comments
                processed += 1

        db.session.commit()

        if processed:
            flash(f'Bulk actions saved ({processed} update(s)).', 'success')
        if warnings:
            flash('Warnings: ' + ' | '.join(warnings), 'warning')

        return redirect(url_for('host_company.bulk_action_center', cohort_id=selected_cohort_id, submission_month=selected_month))

    rows = []
    if selected_cohort_id and _validate_submission_month(selected_month):
        placements = (
            InternPlacement.query
            .filter_by(host_company_id=host.id, cohort_id=selected_cohort_id, is_active=True)
            .order_by(InternPlacement.assigned_at.desc())
            .all()
        )

        for placement in placements:
            intern = placement.intern
            if not intern:
                continue

            timesheet = (
                Timesheet.query
                .filter_by(intern_id=intern.id, submission_month=selected_month, is_deleted=False)
                .order_by(Timesheet.submission_date.desc())
                .first()
            )
            non_worked = TimesheetNonWorkingMonth.query.filter_by(
                host_company_id=host.id,
                cohort_id=selected_cohort_id,
                intern_id=intern.id,
                submission_month=selected_month,
            ).first()
            feedback = HostInternMonthlyFeedback.query.filter_by(
                host_company_id=host.id,
                cohort_id=selected_cohort_id,
                intern_id=intern.id,
                submission_month=selected_month,
            ).first()

            rows.append({
                'placement': placement,
                'intern': intern,
                'timesheet': timesheet,
                'non_worked': non_worked,
                'feedback': feedback,
            })

    return render_template(
        'host_company/bulk_action_center.html',
        host=host,
        cohorts=cohorts,
        rows=rows,
        selected_cohort_id=selected_cohort_id,
        selected_month=selected_month,
    )


@bp.route('/feedback', methods=['GET', 'POST'])
@login_required
@host_company_required
def monthly_feedback():
    """Simple monthly feedback capture page per intern, visible to staff."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    active_placements = InternPlacement.query.filter_by(host_company_id=host.id, is_active=True).all()
    cohort_ids = {p.cohort_id for p in active_placements if p.cohort_id}
    cohorts = Cohort.query.filter(Cohort.id.in_(cohort_ids)).order_by(Cohort.name.asc()).all() if cohort_ids else []

    selected_cohort_id = request.values.get('cohort_id', type=int)
    selected_month = (request.values.get('submission_month') or datetime.utcnow().strftime('%Y-%m')).strip()

    if request.method == 'POST':
        if not selected_cohort_id or not _validate_submission_month(selected_month):
            flash('Please select a valid cohort and month.', 'danger')
            return redirect(url_for('host_company.monthly_feedback'))

        placements = InternPlacement.query.filter_by(host_company_id=host.id, cohort_id=selected_cohort_id, is_active=True).all()
        updated = 0
        for placement in placements:
            intern = placement.intern
            if not intern:
                continue

            comments = (request.form.get(f'comments_{intern.id}') or '').strip() or None
            ratings = {
                'attendance_rating': request.form.get(f'attendance_{intern.id}', type=int),
                'punctuality_rating': request.form.get(f'punctuality_{intern.id}', type=int),
                'communication_rating': request.form.get(f'communication_{intern.id}', type=int),
                'task_quality_rating': request.form.get(f'task_quality_{intern.id}', type=int),
            }
            if not any(v for v in ratings.values()) and not comments:
                continue

            feedback = HostInternMonthlyFeedback.query.filter_by(
                host_company_id=host.id,
                cohort_id=selected_cohort_id,
                intern_id=intern.id,
                submission_month=selected_month,
            ).first()
            if not feedback:
                feedback = HostInternMonthlyFeedback(
                    host_company_id=host.id,
                    cohort_id=selected_cohort_id,
                    intern_id=intern.id,
                    submission_month=selected_month,
                    created_by=current_user.id,
                )
                db.session.add(feedback)

            feedback.attendance_rating = ratings['attendance_rating']
            feedback.punctuality_rating = ratings['punctuality_rating']
            feedback.communication_rating = ratings['communication_rating']
            feedback.task_quality_rating = ratings['task_quality_rating']
            feedback.comments = comments
            updated += 1

        db.session.commit()
        flash(f'Feedback saved for {updated} intern(s).', 'success' if updated else 'info')
        return redirect(url_for('host_company.monthly_feedback', cohort_id=selected_cohort_id, submission_month=selected_month))

    rows = []
    if selected_cohort_id and _validate_submission_month(selected_month):
        placements = InternPlacement.query.filter_by(host_company_id=host.id, cohort_id=selected_cohort_id, is_active=True).all()
        for placement in placements:
            intern = placement.intern
            if not intern:
                continue
            feedback = HostInternMonthlyFeedback.query.filter_by(
                host_company_id=host.id,
                cohort_id=selected_cohort_id,
                intern_id=intern.id,
                submission_month=selected_month,
            ).first()
            rows.append({'placement': placement, 'intern': intern, 'feedback': feedback})

    return render_template(
        'host_company/monthly_feedback.html',
        host=host,
        cohorts=cohorts,
        rows=rows,
        selected_cohort_id=selected_cohort_id,
        selected_month=selected_month,
    )


@bp.route('/timesheets/view')
@login_required
@host_company_required
def view_timesheets():
    """View submitted timesheets by this host."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))
    
    month_filter = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    cohort_filter = request.args.get('cohort_id', 'all')
    
    query = Timesheet.query.filter_by(host_company_id=host.id, is_deleted=False)

    if month_filter and month_filter != 'all':
        query = query.filter_by(submission_month=month_filter)
    
    if cohort_filter != 'all':
        try:
            cohort_id = int(cohort_filter)
            query = query.filter_by(cohort_id=cohort_id)
        except ValueError:
            pass
    
    timesheets = query.order_by(Timesheet.submission_date.desc()).all()
    
    # Get available months and cohorts
    available_months = db.session.query(Timesheet.submission_month).distinct().filter(
        Timesheet.host_company_id == host.id,
        Timesheet.is_deleted == False
    ).order_by(Timesheet.submission_month.desc()).all()
    available_months = [m[0] for m in available_months]
    
    # Get cohorts this host has submitted timesheets for
    cohorts = db.session.query(Cohort).join(
        Timesheet, Cohort.id == Timesheet.cohort_id
    ).filter(
        Timesheet.host_company_id == host.id,
        Timesheet.is_deleted == False
    ).distinct().all()
    
    return render_template(
        'host_company/view_timesheets.html',
        timesheets=timesheets,
        available_months=available_months,
        cohorts=cohorts,
        month_filter=month_filter,
        cohort_filter=cohort_filter
    )


@bp.route('/timesheets/<int:timesheet_id>/download')
@login_required
@host_company_required
def download_timesheet(timesheet_id):
    """Allow host company to download own submitted timesheets only."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    timesheet = Timesheet.query.get_or_404(timesheet_id)
    if timesheet.host_company_id != host.id:
        flash('You do not have access to this timesheet.', 'danger')
        return redirect(url_for('host_company.view_timesheets'))

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'warning')
        return redirect(url_for('host_company.view_timesheets'))

    try:
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=True,
            download_name=timesheet.original_filename,
        )
    except Exception as exc:
        flash(f'Error downloading file: {exc}', 'danger')
        return redirect(url_for('host_company.view_timesheets'))


@bp.route('/timesheets/<int:timesheet_id>/view')
@login_required
@host_company_required
def view_timesheet(timesheet_id):
    """Allow host company to preview own submitted timesheets only."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    timesheet = Timesheet.query.get_or_404(timesheet_id)
    if timesheet.host_company_id != host.id:
        flash('You do not have access to this timesheet.', 'danger')
        return redirect(url_for('host_company.view_timesheets'))

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'warning')
        return redirect(url_for('host_company.view_timesheets'))

    try:
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=False,
            download_name=timesheet.original_filename,
        )
    except Exception as exc:
        flash(f'Error opening file: {exc}', 'danger')
        return redirect(url_for('host_company.view_timesheets'))
