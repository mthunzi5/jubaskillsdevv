from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.timesheet import Timesheet
from app.models.induction import InductionSubmission, InductionPortalSettings, INDUCTION_DOC_FIELDS
from app.models.intern_management import CohortMember, InternPlacement, Cohort
from app.models.notification import Notification
from app.models.user import User
from app.utils.decorators import intern_required, profile_complete_required
from app.utils.helpers import allowed_file, generate_filename, format_month_year, create_soft_delete_request
from datetime import datetime
import os

bp = Blueprint('intern', __name__, url_prefix='/intern')


def _resolve_induction_file(submission, doc_key):
    meta = INDUCTION_DOC_FIELDS.get(doc_key)
    if not submission or not meta:
        return None, None

    file_path = getattr(submission, meta['path_attr'])
    filename = getattr(submission, meta['name_attr'])
    if not file_path:
        return None, None

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return None, filename

    return abs_path, filename

@bp.route('/dashboard')
@login_required
@intern_required
@profile_complete_required
def dashboard():
    """Intern dashboard"""
    total_submissions = Timesheet.query.filter_by(
        intern_id=current_user.id,
        is_deleted=False
    ).count()
    
    # Current month submissions
    current_month = datetime.utcnow().strftime('%Y-%m')
    current_month_submissions = Timesheet.query.filter_by(
        intern_id=current_user.id,
        submission_month=current_month,
        is_deleted=False
    ).count()
    
    recent_submissions = Timesheet.query.filter_by(
        intern_id=current_user.id,
        is_deleted=False
    ).order_by(Timesheet.submission_date.desc()).limit(5).all()
    
    return render_template('intern/dashboard.html',
                         total_submissions=total_submissions,
                         current_month_submissions=current_month_submissions,
                         recent_submissions=recent_submissions)


@bp.route('/induction', methods=['GET', 'POST'])
@login_required
@intern_required
@profile_complete_required
def induction():
    """Induction portal where interns upload required onboarding documents."""
    # Check if portal is open
    portal_settings = InductionPortalSettings.get_settings()
    if not portal_settings.is_open:
        flash('The induction portal is currently closed. Please try again later.', 'warning')
        return redirect(url_for('intern.dashboard'))
    
    submission = InductionSubmission.query.filter_by(intern_id=current_user.id).first()
    created_now = False
    was_complete = submission.is_complete() if submission else False

    # Get current user's cohort if available
    cohort = None
    cohort_member = CohortMember.query.filter_by(user_id=current_user.id).first()
    if cohort_member:
        cohort = cohort_member.cohort

    if request.method == 'POST':
        # Check if already locked (unless admin override)
        if submission and submission.is_locked:
            flash('Your submission is locked. No further uploads allowed.', 'warning')
            return redirect(url_for('intern.induction'))
        
        if not submission:
            submission = InductionSubmission(intern_id=current_user.id, cohort_id=cohort.id if cohort else None)
            db.session.add(submission)
            created_now = True
        elif cohort and submission.cohort_id != cohort.id:
            submission.cohort_id = cohort.id

        uploaded_any = False
        for doc_key, meta in INDUCTION_DOC_FIELDS.items():
            file = request.files.get(doc_key)
            if not file or file.filename == '':
                continue

            if not allowed_file(file.filename, current_app.config['INDUCTION_ALLOWED_EXTENSIONS']):
                flash(f"{meta['label']}: invalid file type. Allowed: PDF, PNG, JPG, JPEG.", 'danger')
                return redirect(url_for('intern.induction'))

            original_name = secure_filename(file.filename)
            extension = os.path.splitext(original_name)[1].lower()
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            saved_name = f"induction_{current_user.id}_{doc_key}_{timestamp}{extension}"

            upload_dir = current_app.config['INDUCTION_UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, saved_name)
            file.save(save_path)

            setattr(submission, meta['path_attr'], save_path)
            setattr(submission, meta['name_attr'], original_name)
            setattr(submission, meta['size_attr'], os.path.getsize(save_path))
            setattr(submission, meta['uploaded_attr'], datetime.utcnow())
            uploaded_any = True

        if not uploaded_any and created_now:
            db.session.rollback()
            flash('Please choose at least one document to upload.', 'warning')
            return redirect(url_for('intern.induction'))

        if not uploaded_any:
            flash('No files selected. Choose at least one document to update.', 'warning')
            return redirect(url_for('intern.induction'))

        db.session.commit()

        missing = submission.missing_documents()
        if missing:
            flash('Documents saved. Still missing: ' + ', '.join(missing), 'warning')
        else:
            flash('All induction documents submitted successfully.', 'success')
            # Lock submission after all 5 documents complete
            submission.is_locked = True
            submission.is_submitted = True
            submission.locked_at = datetime.utcnow()
            submission.submitted_at = datetime.utcnow()
            db.session.commit()
            
            if not was_complete:
                staff_users = User.query.filter_by(role='staff', is_deleted=False).all()
                for staff_user in staff_users:
                    Notification.create_notification(
                        user_id=staff_user.id,
                        title='Induction Documents Completed',
                        message=f'{current_user.name or "Intern"} {current_user.surname or ""} completed induction document uploads.',
                        notification_type='induction_completed',
                        related_type='induction',
                        related_id=submission.id,
                    )

        return redirect(url_for('intern.induction'))

    return render_template(
        'intern/induction.html',
        submission=submission,
        doc_fields=INDUCTION_DOC_FIELDS,
    )


@bp.route('/induction/<string:doc_key>/view')
@login_required
@intern_required
@profile_complete_required
def view_induction_document(doc_key):
    """Preview a specific induction document uploaded by the current intern."""
    portal_settings = InductionPortalSettings.get_settings()
    if not portal_settings.is_open:
        flash('The induction portal is currently closed.', 'warning')
        return redirect(url_for('intern.dashboard'))

    if doc_key not in INDUCTION_DOC_FIELDS:
        flash('Invalid induction document type.', 'danger')
        return redirect(url_for('intern.induction'))

    submission = InductionSubmission.query.filter_by(intern_id=current_user.id).first()
    file_path, original_name = _resolve_induction_file(submission, doc_key)

    if not file_path:
        flash('Document not found. Please upload it first.', 'warning')
        return redirect(url_for('intern.induction'))

    from flask import send_file
    return send_file(file_path, as_attachment=False, download_name=original_name)


@bp.route('/induction/<string:doc_key>/download')
@login_required
@intern_required
@profile_complete_required
def download_induction_document(doc_key):
    """Download a specific induction document uploaded by the current intern."""
    portal_settings = InductionPortalSettings.get_settings()
    if not portal_settings.is_open:
        flash('The induction portal is currently closed.', 'warning')
        return redirect(url_for('intern.dashboard'))

    if doc_key not in INDUCTION_DOC_FIELDS:
        flash('Invalid induction document type.', 'danger')
        return redirect(url_for('intern.induction'))

    submission = InductionSubmission.query.filter_by(intern_id=current_user.id).first()
    file_path, original_name = _resolve_induction_file(submission, doc_key)

    if not file_path:
        flash('Document not found. Please upload it first.', 'warning')
        return redirect(url_for('intern.induction'))

    from flask import send_file
    return send_file(file_path, as_attachment=True, download_name=original_name)

@bp.route('/timesheets')
@login_required
@intern_required
@profile_complete_required
def timesheets():
    """View my timesheets"""
    timesheets = Timesheet.query.filter_by(
        intern_id=current_user.id,
        is_deleted=False
    ).order_by(Timesheet.submission_date.desc()).all()
    
    return render_template('intern/timesheets.html', timesheets=timesheets)

@bp.route('/timesheets/submit', methods=['GET', 'POST'])
@login_required
@intern_required
@profile_complete_required
def submit_timesheet():
    """Submit timesheet"""
    current_month = datetime.utcnow().strftime('%Y-%m')

    if request.method == 'POST':
        submission_month = (request.form.get('submission_month') or '').strip()
        if not submission_month or len(submission_month) != 7 or '-' not in submission_month:
            flash('Please select a valid submission month.', 'danger')
            return redirect(request.url)

        existing = Timesheet.query.filter_by(
            intern_id=current_user.id,
            submission_month=submission_month,
            is_deleted=False,
        ).order_by(Timesheet.submission_date.desc()).first()
        if existing:
            submitter_label = 'host company' if existing.host_company_id else 'intern'
            flash(f'Timesheet for {submission_month} was already submitted by {submitter_label}.', 'warning')
            return redirect(url_for('intern.timesheets'))

        if 'timesheet_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['timesheet_file']
        
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            flash('Only PDF files are allowed.', 'danger')
            return redirect(request.url)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = generate_filename(filename, f"intern_{current_user.id}_")
        
        # Save file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create timesheet record
        submission_date = datetime.utcnow()

        # Link submission to active cohort/host placement where possible.
        active_placement = (
            InternPlacement.query
            .filter_by(intern_id=current_user.id, is_active=True)
            .order_by(InternPlacement.assigned_at.desc())
            .first()
        )
        cohort_id = active_placement.cohort_id if active_placement else None
        host_company_id = active_placement.host_company_id if active_placement else None

        if not cohort_id:
            latest_membership = (
                CohortMember.query
                .filter_by(intern_id=current_user.id)
                .order_by(CohortMember.created_at.desc())
                .first()
            )
            cohort_id = latest_membership.cohort_id if latest_membership else None

        submission_year = int(submission_month.split('-')[0])
        timesheet = Timesheet(
            intern_id=current_user.id,
            cohort_id=cohort_id,
            host_company_id=host_company_id,
            submitted_by=current_user.id,
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            submission_month=submission_month,
            submission_year=submission_year,
            submission_date=submission_date
        )
        
        db.session.add(timesheet)
        db.session.commit()

        if host_company_id and active_placement and active_placement.host_company and active_placement.host_company.login_user_id:
            Notification.create_notification(
                user_id=active_placement.host_company.login_user_id,
                title='Intern Timesheet Submitted',
                message=f'{current_user.name or "Intern"} {current_user.surname or ""} submitted a timesheet for {submission_month}.',
                notification_type='intern_timesheet_submitted',
                related_type='timesheet',
                related_id=timesheet.id,
            )
        
        flash('Timesheet submitted successfully!', 'success')
        return redirect(url_for('intern.timesheets'))
    
    existing_current_month = Timesheet.query.filter_by(
        intern_id=current_user.id,
        submission_month=current_month,
        is_deleted=False,
    ).order_by(Timesheet.submission_date.desc()).first()

    return render_template(
        'intern/submit_timesheet.html',
        current_month=current_month,
        existing_current_month=existing_current_month,
    )


@bp.route('/timesheets/<int:timesheet_id>/download')
@login_required
@intern_required
@profile_complete_required
def download_timesheet(timesheet_id):
    """Download own timesheet (read-only access)."""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    if timesheet.intern_id != current_user.id:
        flash('You can only download your own timesheets.', 'danger')
        return redirect(url_for('intern.timesheets'))

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'warning')
        return redirect(url_for('intern.timesheets'))

    try:
        from flask import send_file
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=True,
            download_name=timesheet.original_filename,
        )
    except Exception as exc:
        flash(f'Error downloading file: {exc}', 'danger')
        return redirect(url_for('intern.timesheets'))


@bp.route('/timesheets/<int:timesheet_id>/view')
@login_required
@intern_required
@profile_complete_required
def view_timesheet(timesheet_id):
    """View own timesheet in browser."""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    if timesheet.intern_id != current_user.id:
        flash('You can only view your own timesheets.', 'danger')
        return redirect(url_for('intern.timesheets'))

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'warning')
        return redirect(url_for('intern.timesheets'))

    try:
        from flask import send_file
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=False,
            download_name=timesheet.original_filename,
        )
    except Exception as exc:
        flash(f'Error opening file: {exc}', 'danger')
        return redirect(url_for('intern.timesheets'))

@bp.route('/timesheets/<int:timesheet_id>/delete', methods=['POST'])
@login_required
@intern_required
@profile_complete_required
def delete_timesheet(timesheet_id):
    """Soft delete timesheet (requires admin approval)"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    # Verify ownership
    if timesheet.intern_id != current_user.id:
        flash('You can only delete your own timesheets.', 'danger')
        return redirect(url_for('intern.timesheets'))
    
    reason = request.form.get('reason')
    
    if not reason:
        flash('Deletion reason is required.', 'danger')
        return redirect(url_for('intern.timesheets'))
    
    # Mark as deleted (soft delete)
    timesheet.is_deleted = True
    timesheet.deleted_at = datetime.utcnow()
    timesheet.deleted_by = current_user.id
    timesheet.pending_permanent_delete = True
    
    # Create soft delete request for admin approval
    create_soft_delete_request(
        item_type='timesheet',
        item_id=timesheet.id,
        deleted_by=current_user.id,
        reason=reason
    )
    
    db.session.commit()
    
    flash('Timesheet deleted from your view. Awaiting admin approval for permanent deletion.', 'info')
    return redirect(url_for('intern.timesheets'))

@bp.route('/profile')
@login_required
@intern_required
def profile():
    """View profile"""
    return render_template('intern/profile.html')

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@intern_required
def edit_profile():
    """Edit profile"""
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.surname = request.form.get('surname')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('intern.profile'))
    
    return render_template('intern/edit_profile.html')
