from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.timesheet import Timesheet
from app.models.induction import InductionSubmission, InductionExportAuditLog, INDUCTION_DOC_FIELDS
from app.models.user import User
from app.models.notification import Notification
from app.models.intern_management import Cohort, CohortMember, InternPlacement
from app.utils.decorators import staff_required, admin_required
from datetime import datetime
import os
from io import BytesIO
from zipfile import ZipFile

bp = Blueprint('staff', __name__, url_prefix='/staff')


def _run_timesheet_reminders_safely(month_value):
    try:
        _send_missing_timesheet_reminders(month_value)
    except Exception:
        current_app.logger.exception('Failed to generate timesheet reminders for %s', month_value)


def _resolve_induction_doc(submission, doc_key):
    meta = INDUCTION_DOC_FIELDS.get(doc_key)
    if not submission or not meta:
        return None, None

    stored_path = getattr(submission, meta['path_attr'])
    original_name = getattr(submission, meta['name_attr'])
    if not stored_path:
        return None, original_name

    abs_path = os.path.abspath(stored_path)
    if not os.path.exists(abs_path):
        return None, original_name

    return abs_path, original_name


def _month_related_type(month_value):
    """Generate a notification related_type key scoped to a specific month."""
    return f'timesheet_month_{month_value}'


def _send_missing_timesheet_reminders(month_value, only_cohort_id=None):
    """Send reminders for missing cohort timesheets; deduplicated per user/cohort/month/day."""
    today = datetime.utcnow().date()
    related_type = _month_related_type(month_value)

    cohort_query = Cohort.query.filter_by(is_active=True)
    if only_cohort_id:
        cohort_query = cohort_query.filter_by(id=only_cohort_id)
    cohorts = cohort_query.all()

    reminders_to_create = []

    for cohort in cohorts:
        memberships = (
            CohortMember.query
            .filter_by(cohort_id=cohort.id)
            .order_by(CohortMember.created_at.desc())
            .all()
        )

        pending_interns = []
        for membership in memberships:
            intern = membership.intern
            if not intern or intern.is_deleted:
                continue

            existing_timesheet = (
                Timesheet.query
                .filter_by(
                    intern_id=intern.id,
                    cohort_id=cohort.id,
                    submission_month=month_value,
                    is_deleted=False,
                )
                .order_by(Timesheet.submission_date.desc())
                .first()
            )
            if existing_timesheet:
                continue

            pending_interns.append(intern)

            existing_reminder = (
                Notification.query
                .filter(
                    Notification.user_id == intern.id,
                    Notification.notification_type == 'timesheet_missing_reminder',
                    Notification.related_type == related_type,
                    Notification.related_id == cohort.id,
                )
                .order_by(Notification.created_at.desc())
                .first()
            )
            if existing_reminder and existing_reminder.created_at and existing_reminder.created_at.date() == today:
                continue

            reminders_to_create.append(Notification(
                user_id=intern.id,
                title=f'Timesheet Missing for {month_value}',
                message=f'No timesheet found yet for cohort {cohort.name} in {month_value}. Please submit or follow up with your host company.',
                notification_type='timesheet_missing_reminder',
                related_type=related_type,
                related_id=cohort.id,
            ))

        host_pending = {}
        for intern in pending_interns:
            placement = (
                InternPlacement.query
                .filter_by(intern_id=intern.id, cohort_id=cohort.id, is_active=True)
                .order_by(InternPlacement.assigned_at.desc())
                .first()
            )
            if not placement or not placement.host_company or not placement.host_company.login_user_id:
                continue
            host_user_id = placement.host_company.login_user_id
            host_pending[host_user_id] = host_pending.get(host_user_id, 0) + 1

        for host_user_id, pending_total in host_pending.items():
            existing_host_reminder = (
                Notification.query
                .filter(
                    Notification.user_id == host_user_id,
                    Notification.notification_type == 'host_timesheet_incomplete_reminder',
                    Notification.related_type == related_type,
                    Notification.related_id == cohort.id,
                )
                .order_by(Notification.created_at.desc())
                .first()
            )
            if existing_host_reminder and existing_host_reminder.created_at and existing_host_reminder.created_at.date() == today:
                continue

            reminders_to_create.append(Notification(
                user_id=host_user_id,
                title=f'Cohort Timesheets Incomplete ({month_value})',
                message=f'{pending_total} learner timesheet(s) are still missing for cohort {cohort.name} in {month_value}.',
                notification_type='host_timesheet_incomplete_reminder',
                related_type=related_type,
                related_id=cohort.id,
            ))

    if reminders_to_create:
        db.session.add_all(reminders_to_create)
        db.session.commit()

    return len(reminders_to_create)


def _send_missing_induction_reminders(only_cohort_id=None):
    """Send reminders to interns with incomplete induction document submissions."""
    today = datetime.utcnow().date()
    
    cohort_query = Cohort.query.filter_by(is_active=True)
    if only_cohort_id:
        cohort_query = cohort_query.filter_by(id=only_cohort_id)
    cohorts = cohort_query.all()

    reminders_to_create = []

    for cohort in cohorts:
        interns = (
            User.query
            .join(CohortMember, CohortMember.user_id == User.id)
            .filter(CohortMember.cohort_id == cohort.id, User.role == 'intern', User.is_deleted == False)
            .all()
        )

        for intern in interns:
            submission = InductionSubmission.query.filter_by(intern_id=intern.id).first()
            
            # Skip if already complete
            if submission and submission.is_complete():
                continue

            # Check if already reminded today
            existing_reminder = (
                Notification.query
                .filter(
                    Notification.user_id == intern.id,
                    Notification.notification_type == 'induction_documents_missing_reminder',
                    Notification.related_id == cohort.id,
                )
                .order_by(Notification.created_at.desc())
                .first()
            )
            if existing_reminder and existing_reminder.created_at and existing_reminder.created_at.date() == today:
                continue

            missing_docs = []
            if not submission:
                missing_docs = [meta['label'] for meta in INDUCTION_DOC_FIELDS.values()]
            else:
                missing_docs = submission.missing_documents()

            reminders_to_create.append(Notification(
                user_id=intern.id,
                title='Induction Documents Missing',
                message=f'You still need to submit: {", ".join(missing_docs)}. Please complete your induction document uploads.',
                notification_type='induction_documents_missing_reminder',
                related_type='induction',
                related_id=cohort.id,
            ))

    if reminders_to_create:
        db.session.add_all(reminders_to_create)
        db.session.commit()

    return len(reminders_to_create)

@bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    """Staff dashboard"""
    _run_timesheet_reminders_safely(datetime.utcnow().strftime('%Y-%m'))

    total_timesheets = Timesheet.query.filter_by(is_deleted=False).count()
    total_interns = User.query.filter_by(role='intern', is_deleted=False).count()
    
    # Get current month timesheets
    current_month = datetime.utcnow().strftime('%Y-%m')
    current_month_timesheets = Timesheet.query.filter_by(
        submission_month=current_month,
        is_deleted=False
    ).count()
    
    recent_submissions = Timesheet.query.filter_by(is_deleted=False).order_by(
        Timesheet.submission_date.desc()
    ).limit(5).all()
    
    return render_template('staff/dashboard.html',
                         total_timesheets=total_timesheets,
                         total_interns=total_interns,
                         current_month_timesheets=current_month_timesheets,
                         recent_submissions=recent_submissions)

@bp.route('/timesheets')
@login_required
@staff_required
def timesheets():
    """View all timesheets organized by month"""
    _run_timesheet_reminders_safely(datetime.utcnow().strftime('%Y-%m'))

    month_filter = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    intern_type_filter = request.args.get('intern_type', 'all')
    
    query = Timesheet.query.filter_by(submission_month=month_filter, is_deleted=False)
    
    if intern_type_filter != 'all':
        query = query.join(User, Timesheet.intern_id == User.id).filter(User.intern_type == intern_type_filter)
    
    timesheets = query.order_by(Timesheet.submission_date.desc()).all()
    
    # Get available months
    available_months = db.session.query(Timesheet.submission_month).distinct().filter_by(
        is_deleted=False
    ).order_by(Timesheet.submission_month.desc()).all()
    available_months = [m[0] for m in available_months]

    cohorts = (
        db.session.query(Cohort)
        .join(Timesheet, Cohort.id == Timesheet.cohort_id)
        .filter(Timesheet.is_deleted == False)
        .distinct()
        .order_by(Cohort.name.asc())
        .all()
    )
    
    return render_template('staff/timesheets.html',
                         timesheets=timesheets,
                         month_filter=month_filter,
                         intern_type_filter=intern_type_filter,
                         available_months=available_months,
                         cohorts=cohorts)

@bp.route('/timesheets/<int:timesheet_id>/download')
@login_required
@staff_required
def download_timesheet(timesheet_id):
    """Download individual timesheet"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'danger')
        return redirect(url_for('staff.timesheets'))
    
    try:
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=True,
            download_name=timesheet.original_filename
        )
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        return redirect(url_for('staff.timesheets'))


@bp.route('/timesheets/<int:timesheet_id>/view')
@login_required
@staff_required
def view_timesheet(timesheet_id):
    """Open a timesheet in-browser preview."""
    timesheet = Timesheet.query.get_or_404(timesheet_id)

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'danger')
        return redirect(url_for('staff.timesheets'))

    try:
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=False,
            download_name=timesheet.original_filename
        )
    except Exception as e:
        flash(f'Error opening file: {str(e)}', 'danger')
        return redirect(url_for('staff.timesheets'))

@bp.route('/timesheets/download-month/<string:month>')
@login_required
@staff_required
def download_month_timesheets(month):
    """Download timesheets for a specific month and optional intern type as ZIP"""
    intern_type_filter = request.args.get('intern_type', 'all')
    
    # Build query
    query = Timesheet.query.filter_by(submission_month=month, is_deleted=False)
    
    if intern_type_filter != 'all':
        query = query.join(User, Timesheet.intern_id == User.id).filter(User.intern_type == intern_type_filter)
    
    timesheets = query.order_by(Timesheet.submission_date.desc()).all()

    # Deduplicate by intern for this month; keep latest submission only.
    unique_by_intern = {}
    for ts in timesheets:
        if ts.intern_id not in unique_by_intern:
            unique_by_intern[ts.intern_id] = ts
    timesheets = list(unique_by_intern.values())
    
    if not timesheets:
        flash('No timesheets found for the selected filters.', 'warning')
        return redirect(url_for('staff.timesheets'))
    
    # Create ZIP file in memory
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for timesheet in timesheets:
            abs_path = os.path.abspath(timesheet.file_path)
            if os.path.exists(abs_path):
                intern = timesheet.intern
                
                # Build filename with name or ID number
                if intern.name and intern.surname:
                    intern_identifier = f"{intern.name}_{intern.surname}"
                else:
                    intern_identifier = intern.id_number if intern.id_number else f"User_{intern.id}"
                
                # Get file extension
                file_ext = os.path.splitext(timesheet.original_filename)[1]
                
                # Create new filename: Name_IDNumber_Month.ext
                zip_filename = f"{intern_identifier}_{intern.id_number}_{month}{file_ext}"
                
                zf.write(abs_path, zip_filename)
    
    memory_file.seek(0)
    
    # Build download filename based on filters
    if intern_type_filter != 'all':
        download_name = f'timesheets_{intern_type_filter}_{month}.zip'
    else:
        download_name = f'timesheets_all_{month}.zip'
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name
    )

@bp.route('/timesheets/download-cohort/<int:cohort_id>/<string:month>')
@login_required
@staff_required
def download_cohort_timesheets(cohort_id, month):
    """Download all timesheets for a specific cohort and month, organized by host company."""
    cohort = Cohort.query.get_or_404(cohort_id)
    
    # Get all timesheets for this cohort in the given month
    timesheets = Timesheet.query.filter_by(
        cohort_id=cohort_id,
        submission_month=month,
        is_deleted=False
    ).order_by(Timesheet.host_company_id, Timesheet.submission_date.desc()).all()

    # Deduplicate by intern for this cohort-month; keep latest submission only.
    unique_by_intern = {}
    for ts in timesheets:
        if ts.intern_id not in unique_by_intern:
            unique_by_intern[ts.intern_id] = ts
    timesheets = list(unique_by_intern.values())
    
    if not timesheets:
        flash(f'No timesheets found for cohort {cohort.name} in {month}.', 'warning')
        return redirect(url_for('staff.timesheets'))
    
    # Create ZIP file in memory with host company organization
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for timesheet in timesheets:
            abs_path = os.path.abspath(timesheet.file_path)
            if os.path.exists(abs_path):
                intern = timesheet.intern
                host_company = timesheet.host_company
                
                # Build host company folder name
                if host_company:
                    host_folder = f"{host_company.company_name.replace(' ', '_')}"
                else:
                    host_folder = "Unknown_Host"
                
                # Build filename with name or ID number
                if intern.name and intern.surname:
                    intern_identifier = f"{intern.name}_{intern.surname}"
                else:
                    intern_identifier = intern.id_number if intern.id_number else f"User_{intern.id}"
                
                # Get file extension
                file_ext = os.path.splitext(timesheet.original_filename)[1]
                
                # Create path: Host_Company/Name_IDNumber_Month.ext
                zip_path = f"{host_folder}/{intern_identifier}_{intern.id_number}_{month}{file_ext}"
                
                zf.write(abs_path, zip_path)
    
    memory_file.seek(0)
    
    # Build download filename
    download_name = f'timesheets_cohort_{cohort.name.replace(" ", "_")}_{month}.zip'
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name
    )


@bp.route('/timesheets/submission-status')
@login_required
@staff_required
def timesheet_submission_status():
    """Track submitted vs pending timesheets by cohort and month."""
    month_filter = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    selected_cohort_id = request.args.get('cohort_id', type=int)
    send_reminders = request.args.get('send_reminders', '0') == '1'

    cohorts = Cohort.query.filter_by(is_active=True).order_by(Cohort.name.asc()).all()

    if not selected_cohort_id and cohorts:
        selected_cohort_id = cohorts[0].id

    selected_cohort = None
    rows = []
    submitted_count = 0
    pending_count = 0

    if selected_cohort_id:
        selected_cohort = Cohort.query.get(selected_cohort_id)

    if selected_cohort:
        memberships = (
            CohortMember.query
            .filter_by(cohort_id=selected_cohort.id)
            .order_by(CohortMember.created_at.desc())
            .all()
        )

        for membership in memberships:
            intern = membership.intern
            if not intern or intern.is_deleted:
                continue

            timesheet = (
                Timesheet.query
                .filter_by(
                    intern_id=intern.id,
                    cohort_id=selected_cohort.id,
                    submission_month=month_filter,
                    is_deleted=False,
                )
                .order_by(Timesheet.submission_date.desc())
                .first()
            )

            placement = (
                InternPlacement.query
                .filter_by(intern_id=intern.id, cohort_id=selected_cohort.id, is_active=True)
                .order_by(InternPlacement.assigned_at.desc())
                .first()
            )

            host_name = '-'
            if timesheet and timesheet.host_company:
                host_name = timesheet.host_company.company_name
            elif placement and placement.host_company:
                host_name = placement.host_company.company_name

            if timesheet:
                submitted_count += 1
            else:
                pending_count += 1

            rows.append({
                'intern': intern,
                'host_name': host_name,
                'submitted': bool(timesheet),
                'timesheet': timesheet,
            })

    if send_reminders and selected_cohort and pending_count > 0:
        reminders_sent = _send_missing_timesheet_reminders(month_filter, only_cohort_id=selected_cohort.id)

        if reminders_sent:
            flash(f'Reminder notifications sent: {reminders_sent}.', 'success')
        else:
            flash('No new reminders were sent today for the selected cohort and month.', 'info')

        return redirect(url_for('staff.timesheet_submission_status', cohort_id=selected_cohort.id, month=month_filter))

    total_count = submitted_count + pending_count

    return render_template(
        'staff/timesheet_submission_status.html',
        month_filter=month_filter,
        cohorts=cohorts,
        selected_cohort=selected_cohort,
        selected_cohort_id=selected_cohort_id,
        rows=rows,
        total_count=total_count,
        submitted_count=submitted_count,
        pending_count=pending_count,
    )

@bp.route('/interns')
@login_required
@staff_required
def interns():
    """View all interns"""
    intern_type_filter = request.args.get('intern_type', 'all')
    
    query = User.query.filter_by(role='intern', is_deleted=False)
    
    if intern_type_filter != 'all':
        query = query.filter_by(intern_type=intern_type_filter)
    
    interns = query.order_by(User.created_at.desc()).all()
    
    return render_template('staff/interns.html',
                         interns=interns,
                         intern_type_filter=intern_type_filter)

@bp.route('/interns/<int:intern_id>/timesheets')
@login_required
@staff_required
def intern_timesheets(intern_id):
    """View timesheets for specific intern"""
    intern = User.query.get_or_404(intern_id)
    
    if intern.role != 'intern':
        flash('Invalid intern ID.', 'danger')
        return redirect(url_for('staff.interns'))
    
    timesheets = Timesheet.query.filter_by(
        intern_id=intern_id,
        is_deleted=False
    ).order_by(Timesheet.submission_date.desc()).all()
    
    return render_template('staff/intern_timesheets.html',
                         intern=intern,
                         timesheets=timesheets)


@bp.route('/induction')
@login_required
@staff_required
def induction_documents():
    """View induction document submission status for all active interns, with optional cohort filtering."""
    cohort_id = request.args.get('cohort_id', type=int)
    
    # Get all cohorts for dropdown
    cohorts = Cohort.query.filter_by(is_active=True).order_by(Cohort.name.asc()).all()
    
    # Build base query
    interns_query = User.query.filter_by(role='intern', is_deleted=False)
    
    # Filter by cohort if specified
    if cohort_id:
        selected_cohort = Cohort.query.get(cohort_id)
        if not selected_cohort:
            flash('Cohort not found.', 'danger')
            return redirect(url_for('staff.induction_documents'))
        
        interns_query = (
            interns_query
            .join(CohortMember, CohortMember.user_id == User.id)
            .filter(CohortMember.cohort_id == cohort_id)
        )
    
    interns = interns_query.order_by(User.name.asc(), User.surname.asc()).all()
    submissions = InductionSubmission.query.all()
    by_intern = {sub.intern_id: sub for sub in submissions}

    rows = []
    complete_count = 0
    for intern in interns:
        submission = by_intern.get(intern.id)
        is_complete = submission.is_complete() if submission else False
        if is_complete:
            complete_count += 1
        rows.append({
            'intern': intern,
            'submission': submission,
            'is_complete': is_complete,
        })

    return render_template(
        'staff/induction_documents.html',
        rows=rows,
        total_interns=len(interns),
        complete_count=complete_count,
        doc_fields=INDUCTION_DOC_FIELDS,
        cohorts=cohorts,
        selected_cohort_id=cohort_id,
    )


@bp.route('/induction/<int:submission_id>/<string:doc_key>/view')
@login_required
@staff_required
def view_induction_document(submission_id, doc_key):
    """Preview one induction document for staff/admin."""
    if doc_key not in INDUCTION_DOC_FIELDS:
        flash('Invalid induction document type.', 'danger')
        return redirect(url_for('staff.induction_documents'))

    submission = InductionSubmission.query.get_or_404(submission_id)
    file_path, original_name = _resolve_induction_doc(submission, doc_key)
    if not file_path:
        flash('Document file not found for this learner.', 'warning')
        return redirect(url_for('staff.induction_documents'))

    return send_file(file_path, as_attachment=False, download_name=original_name)


@bp.route('/induction/<int:submission_id>/<string:doc_key>/download')
@login_required
@staff_required
def download_induction_document(submission_id, doc_key):
    """Download one induction document for staff/admin."""
    if doc_key not in INDUCTION_DOC_FIELDS:
        flash('Invalid induction document type.', 'danger')
        return redirect(url_for('staff.induction_documents'))

    submission = InductionSubmission.query.get_or_404(submission_id)
    file_path, original_name = _resolve_induction_doc(submission, doc_key)
    if not file_path:
        flash('Document file not found for this learner.', 'warning')
        return redirect(url_for('staff.induction_documents'))

    return send_file(file_path, as_attachment=True, download_name=original_name)


@bp.route('/induction/download/<string:doc_key>/zip')
@login_required
@staff_required
def download_induction_zip(doc_key):
    """Download all interns' files for a single induction document type as a ZIP, with optional cohort filtering."""
    meta = INDUCTION_DOC_FIELDS.get(doc_key)
    if not meta:
        flash('Invalid induction document type.', 'danger')
        return redirect(url_for('staff.induction_documents'))

    cohort_id = request.args.get('cohort_id', type=int)
    
    # Build base query
    submissions_query = (
        InductionSubmission.query
        .join(User, User.id == InductionSubmission.intern_id)
        .filter(User.role == 'intern', User.is_deleted == False)
    )
    
    # Filter by cohort if specified
    if cohort_id:
        selected_cohort = Cohort.query.get(cohort_id)
        if not selected_cohort:
            flash('Cohort not found.', 'danger')
            return redirect(url_for('staff.induction_documents'))
        submissions_query = submissions_query.filter(InductionSubmission.cohort_id == cohort_id)
    
    submissions = submissions_query.order_by(InductionSubmission.updated_at.desc()).all()

    files_added = 0
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for submission in submissions:
            abs_path, original_name = _resolve_induction_doc(submission, doc_key)
            if not abs_path:
                continue

            intern = submission.intern
            safe_name = (intern.name or 'Intern').replace(' ', '_')
            safe_surname = (intern.surname or '').replace(' ', '_')
            intern_id_number = intern.id_number or f'user_{intern.id}'
            ext = os.path.splitext(original_name or '')[1] or os.path.splitext(abs_path)[1]
            zip_name = f"{safe_name}_{safe_surname}_{intern_id_number}_{doc_key}{ext}"
            zf.write(abs_path, zip_name)
            files_added += 1

    if files_added == 0:
        flash(f'No files found for {meta["label"]}.', 'warning')
        return redirect(url_for('staff.induction_documents'))

    # Log the export to audit trail
    audit_log = InductionExportAuditLog(
        user_id=current_user.id,
        export_type=doc_key,
        cohort_id=cohort_id,
        file_count=files_added,
        exported_at=datetime.utcnow()
    )
    db.session.add(audit_log)
    db.session.commit()

    memory_file.seek(0)
    download_name = f"induction_{doc_key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=download_name)


@bp.route('/induction/send-reminders', methods=['POST'])
@login_required
@staff_required
def send_induction_reminders():
    """Send reminders to interns with incomplete induction submissions."""
    cohort_id = request.args.get('cohort_id', type=int)
    count = _send_missing_induction_reminders(only_cohort_id=cohort_id)
    flash(f'Sent {count} reminder notification(s) to interns with incomplete submissions.', 'info')
    
    if cohort_id:
        return redirect(url_for('staff.induction_documents', cohort_id=cohort_id))
    return redirect(url_for('staff.induction_documents'))


@bp.route('/induction/<int:submission_id>/unlock', methods=['POST'])
@login_required
@admin_required
def unlock_induction_submission(submission_id):
    """Admin override to unlock a completed induction submission for further edits."""
    submission = InductionSubmission.query.get_or_404(submission_id)
    submission.is_locked = False
    submission.locked_at = None
    db.session.commit()
    
    # Notify intern
    Notification.create_notification(
        user_id=submission.intern_id,
        title='Induction Submission Unlocked',
        message='Your induction submission has been unlocked. You may now upload or update documents.',
        notification_type='induction_unlocked',
        related_type='induction',
        related_id=submission.id,
    )
    
    flash(f'Unlocked induction submission for {submission.intern.name}.', 'success')
    return redirect(url_for('staff.induction_documents'))
