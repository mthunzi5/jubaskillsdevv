from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.job_application import JobApplication, JobApplicationDocument, JobApplicationSettings
from app.models.user import User
from app.utils.decorators import staff_required
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from config import Config

bp = Blueprint('job_applications', __name__, url_prefix='/job-applications')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'job_applications')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}


def get_job_application_settings():
    """Get or create singleton settings for job applications portal."""
    settings = JobApplicationSettings.query.first()
    if not settings:
        settings = JobApplicationSettings(applications_open=True)
        db.session.add(settings)
        db.session.commit()
    return settings

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_mime_type(filename):
    """Get MIME type based on file extension"""
    ext = filename.rsplit('.', 1)[1].lower()
    mime_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'txt': 'text/plain'
    }
    return mime_types.get(ext, 'application/octet-stream')


def send_feedback_email(app_obj, subject, message):
    """Send feedback email to applicant using SMTP settings."""
    mail_server = Config.SMTP_HOST or Config.MAIL_SERVER
    mail_port = Config.SMTP_PORT or Config.MAIL_PORT
    mail_username = Config.SMTP_USERNAME or Config.MAIL_USERNAME
    mail_password = Config.SMTP_PASSWORD or Config.MAIL_PASSWORD
    mail_sender = Config.SMTP_FROM_EMAIL or Config.MAIL_DEFAULT_SENDER
    mail_sender_name = getattr(Config, 'SMTP_FROM_NAME', None) or 'Juba Consultants'
    use_tls = Config.SMTP_USE_TLS if hasattr(Config, 'SMTP_USE_TLS') else Config.MAIL_USE_TLS

    # Gmail app passwords are often copied with spaces, normalize before login.
    if mail_password:
        mail_password = mail_password.replace(' ', '').strip()

    if not all([mail_server, mail_port, mail_sender]):
        return False, 'Email server is not configured.'

    if not all([mail_username, mail_password]):
        return False, 'SMTP credentials are missing. Set SMTP_USERNAME and SMTP_PASSWORD.'

    email_message = EmailMessage()
    email_message['Subject'] = subject
    email_message['From'] = formataddr((mail_sender_name, mail_sender))
    email_message['To'] = app_obj.email
    email_message.set_content(message)

    try:
        with smtplib.SMTP(mail_server, mail_port) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(mail_username, mail_password)
            smtp.send_message(email_message)
    except Exception as e:
        return False, str(e)

    return True, None


def build_status_email_content(app_obj, status, custom_message=None, subject_override=None):
    """Build professional email subject and message based on status."""
    applicant_name = app_obj.full_name
    qualification = app_obj.qualification_level or 'your submitted qualification'

    if status == 'shortlisted':
        subject = subject_override or 'Application Update: You Have Been Shortlisted'
        body = f"""Dear {applicant_name},

Juba Consultants is pleased to inform you that your application has been shortlisted.

To confirm your continued interest, please contact us on WhatsApp at 068 382 5733 as soon as possible and include the following details:
- Full Name and Surname
- Qualification Name

For your convenience, we have your current qualification listed as: {qualification}.

You can also visit our website for more information: https://www.jubaconsultants.co.za/

WhatsApp Contact: 068 382 5733

We appreciate your interest and look forward to hearing from you.

Kind regards,
Recruitment Team
Juba Consultants"""
        if custom_message:
            body = f"{body}\n\nAdditional Note:\n{custom_message.strip()}"
        return subject, body

    if status == 'under_review':
        subject = subject_override or 'Application Update: Your Application Is Under Review'
        body = f"""Dear {applicant_name},

Thank you for your application.

This is to confirm that your application is currently under review by our recruitment team. We will communicate the next outcome once the review process is completed.

We appreciate your patience and interest in joining our organization.

Kind regards,
Recruitment Team
Juba Consultants"""
        if custom_message:
            body = f"{body}\n\nAdditional Note:\n{custom_message.strip()}"
        return subject, body

    if status == 'accepted':
        if not custom_message:
            return None, None
        subject = subject_override or 'Application Outcome: Accepted'
        body = f"""Dear {applicant_name},

Congratulations. We are pleased to inform you that your application has been accepted.

{custom_message.strip()}

Kind regards,
Recruitment Team
Juba Consultants"""
        return subject, body

    if status == 'rejected':
        subject = subject_override or 'Application Outcome Update'
        body = f"""Dear {applicant_name},

Thank you for taking the time to apply.

After careful review, we regret to inform you that your application was not successful for this opportunity. We value your interest and encourage you to apply for future opportunities that match your profile.

We wish you all the best in your career journey.

Kind regards,
Recruitment Team
Juba Consultants"""
        if custom_message:
            body = f"{body}\n\nAdditional Note:\n{custom_message.strip()}"
        return subject, body

    subject = subject_override or 'Application Status Update'
    body = f"""Dear {applicant_name},

This is an update regarding your application status: {status.replace('_', ' ').title()}.

{custom_message.strip() if custom_message else 'Thank you for your application and interest.'}

Kind regards,
Recruitment Team
Juba Consultants"""
    return subject, body


@bp.route('/')
def list_applications():
    """Public job applications page - info and apply button"""
    settings = get_job_application_settings()
    return render_template('job_applications/apply.html', applications_open=settings.applications_open)


@bp.route('/apply', methods=['GET', 'POST'])
def start_application():
    """Start job application process"""
    settings = get_job_application_settings()

    if not settings.applications_open:
        if request.method == 'POST':
            flash('Applications are currently closed. Please check back later.', 'warning')
        return render_template('job_applications/apply.html', applications_open=False)

    if request.method == 'POST':
        # Get form data
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        national_id = request.form.get('national_id')
        qualification_level = request.form.get('qualification_level')
        motivation = request.form.get('motivation')
        skills = request.form.get('skills')
        
        # Validate required fields
        if not all([full_name, email, phone_number, motivation]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('job_applications/apply.html', applications_open=True)
        
        # Check if email has already submitted an application
        existing_application = JobApplication.query.filter_by(email=email, is_deleted=False).first()
        if existing_application:
            flash('An application has already been submitted with this email address.', 'warning')
            return render_template('job_applications/apply.html', applications_open=True)
        
        try:
            # Create application
            app_obj = JobApplication(
                full_name=full_name,
                email=email,
                phone_number=phone_number,
                national_id=national_id,
                qualification_level=qualification_level,
                motivation=motivation,
                skills=skills
            )
            db.session.add(app_obj)
            db.session.flush()  # Get the ID without committing
            
            # Handle file uploads
            for file_type in ['id_copy', 'qualification', 'cv', 'affidavit']:
                if file_type in request.files:
                    file = request.files[file_type]
                    if file and file.filename and allowed_file(file.filename):
                        # Create secure filename
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        filename = secure_filename(f"{file_type}_{app_obj.id}_{timestamp}_{file.filename}")
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        
                        # Save file
                        ensure_dir(file_path)
                        file.save(file_path)
                        
                        # Create document record
                        doc = JobApplicationDocument(
                            application_id=app_obj.id,
                            document_type=file_type,
                            original_filename=file.filename,
                            file_path=file_path,
                            file_size=os.path.getsize(file_path),
                            mime_type=get_mime_type(file.filename)
                        )
                        db.session.add(doc)
            
            # Handle optional other documents
            if 'other_documents' in request.files:
                files = request.files.getlist('other_documents')
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        filename = secure_filename(f"other_{app_obj.id}_{timestamp}_{file.filename}")
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        
                        ensure_dir(file_path)
                        file.save(file_path)
                        
                        doc = JobApplicationDocument(
                            application_id=app_obj.id,
                            document_type='other',
                            original_filename=file.filename,
                            file_path=file_path,
                            file_size=os.path.getsize(file_path),
                            mime_type=get_mime_type(file.filename)
                        )
                        db.session.add(doc)
            
            db.session.commit()
            
            flash(f'Application submitted successfully! Application ID: {app_obj.id}', 'success')
            return redirect(url_for('job_applications.application_received', app_id=app_obj.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'danger')
            return render_template('job_applications/apply.html', applications_open=True)
    
    return render_template('job_applications/apply.html', applications_open=True)


@bp.route('/received/<int:app_id>')
def application_received(app_id):
    """Confirmation page after application submission"""
    app_obj = JobApplication.query.get_or_404(app_id)
    missing_docs = app_obj.get_missing_documents()
    return render_template('job_applications/received.html', application=app_obj, missing_docs=missing_docs)


@bp.route('/staff/dashboard')
@login_required
@staff_required
def staff_dashboard():
    """Staff dashboard for viewing applications"""
    settings = get_job_application_settings()

    # Get statistics
    total_applications = JobApplication.query.filter_by(is_deleted=False).count()
    submitted = JobApplication.query.filter_by(status='submitted', is_deleted=False).count()
    under_review = JobApplication.query.filter_by(status='under_review', is_deleted=False).count()
    shortlisted = JobApplication.query.filter_by(status='shortlisted', is_deleted=False).count()
    rejected = JobApplication.query.filter_by(status='rejected', is_deleted=False).count()
    accepted = JobApplication.query.filter_by(status='accepted', is_deleted=False).count()
    
    # Get recent applications
    recent_applications = JobApplication.query.filter_by(is_deleted=False).order_by(
        JobApplication.submitted_at.desc()
    ).limit(10).all()
    
    return render_template('job_applications/staff_dashboard.html',
                         total_applications=total_applications,
                         submitted=submitted,
                         under_review=under_review,
                         shortlisted=shortlisted,
                         rejected=rejected,
                         accepted=accepted,
                         recent_applications=recent_applications,
                         applications_open=settings.applications_open,
                         portal_settings=settings)


@bp.route('/staff/toggle-application-portal', methods=['POST'])
@login_required
@staff_required
def toggle_application_portal():
    """Open or close public job applications portal."""
    settings = get_job_application_settings()
    next_state = request.form.get('applications_open') == 'true'

    try:
        settings.applications_open = next_state
        settings.updated_by = current_user.id
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        if next_state:
            flash('Job applications have been opened for applicants.', 'success')
        else:
            flash('Job applications have been closed. Applicants can no longer submit.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to update application portal status: {str(e)}', 'danger')

    return redirect(url_for('job_applications.staff_dashboard'))


@bp.route('/staff/list')
@login_required
@staff_required
def staff_list_applications():
    """List all applications with filtering"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    query = JobApplication.query.filter_by(is_deleted=False)
    
    # Apply status filter
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Apply search filter
    if search_query:
        query = query.filter(
            (JobApplication.full_name.ilike(f'%{search_query}%')) |
            (JobApplication.email.ilike(f'%{search_query}%')) |
            (JobApplication.phone_number.ilike(f'%{search_query}%'))
        )
    
    # Order by most recent
    applications = query.order_by(JobApplication.submitted_at.desc()).paginate(page=page, per_page=15)
    
    return render_template('job_applications/staff_list.html',
                         applications=applications,
                         status_filter=status_filter,
                         search_query=search_query)


@bp.route('/staff/view/<int:app_id>')
@login_required
@staff_required
def staff_view_application(app_id):
    """View detailed application"""
    app_obj = JobApplication.query.get_or_404(app_id)
    
    if app_obj.is_deleted:
        flash('This application has been deleted.', 'warning')
        return redirect(url_for('job_applications.staff_list_applications'))
    
    return render_template('job_applications/staff_view.html', application=app_obj)


@bp.route('/staff/update-status/<int:app_id>', methods=['POST'])
@login_required
@staff_required
def update_application_status(app_id):
    """Update application status"""
    app_obj = JobApplication.query.get_or_404(app_id)
    
    status = request.form.get('status')
    rating = request.form.get('rating', type=int)
    review_notes = request.form.get('review_notes')
    
    valid_statuses = ['submitted', 'under_review', 'shortlisted', 'rejected', 'accepted']
    if status not in valid_statuses:
        flash('Invalid status provided.', 'danger')
        return redirect(url_for('job_applications.staff_view_application', app_id=app_id))
    
    try:
        app_obj.mark_as_reviewed(
            reviewer_id=current_user.id,
            rating=rating,
            status=status,
            notes=review_notes
        )
        db.session.commit()
        flash(f'Application status updated to {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating application: {str(e)}', 'danger')
    
    return redirect(url_for('job_applications.staff_view_application', app_id=app_id))


@bp.route('/staff/send-feedback/<int:app_id>', methods=['POST'])
@login_required
@staff_required
def send_application_feedback(app_id):
    """Save and optionally email applicant feedback."""
    app_obj = JobApplication.query.get_or_404(app_id)

    feedback_message = request.form.get('feedback_message', '').strip()
    subject = request.form.get('feedback_subject', '').strip() or f'Update on your application #{app_obj.id}'
    send_email = request.form.get('send_email') == 'on'

    if not feedback_message:
        flash('Feedback message cannot be empty.', 'danger')
        return redirect(url_for('job_applications.staff_view_application', app_id=app_id))

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    reviewer_name = current_user.name if getattr(current_user, 'name', None) else current_user.username
    feedback_entry = f"[{timestamp}] Feedback by {reviewer_name}:\n{feedback_message}"

    try:
        # Keep existing notes and append the latest feedback entry.
        if app_obj.review_notes:
            app_obj.review_notes = f"{app_obj.review_notes}\n\n{feedback_entry}"
        else:
            app_obj.review_notes = feedback_entry

        app_obj.reviewed_by = current_user.id
        app_obj.reviewed_at = datetime.utcnow()
        if app_obj.status == 'submitted':
            app_obj.status = 'under_review'

        email_sent = False
        if send_email:
            ok, err = send_feedback_email(app_obj, subject, feedback_message)
            if not ok:
                db.session.rollback()
                flash(f'Feedback not sent. Email error: {err}', 'danger')
                return redirect(url_for('job_applications.staff_view_application', app_id=app_id))
            email_sent = True

        db.session.commit()

        if email_sent:
            flash('Feedback saved and emailed to applicant.', 'success')
        else:
            flash('Feedback saved successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving feedback: {str(e)}', 'danger')

    return redirect(url_for('job_applications.staff_view_application', app_id=app_id))


@bp.route('/staff/send-feedback-by-status', methods=['POST'])
@login_required
@staff_required
def send_feedback_by_status():
    """Send status-based feedback emails to all matching applicants."""
    status = request.form.get('status', '').strip()
    subject_override = request.form.get('subject', '').strip()
    custom_message = request.form.get('custom_message', '').strip()

    valid_statuses = ['submitted', 'under_review', 'shortlisted', 'accepted', 'rejected']
    if status not in valid_statuses:
        flash('Please select a valid status group.', 'danger')
        return redirect(url_for('job_applications.staff_dashboard'))

    if status == 'accepted' and not custom_message:
        flash('For accepted applicants, please type the email message before sending.', 'danger')
        return redirect(url_for('job_applications.staff_dashboard'))

    selected_ids = request.form.getlist('selected_application_ids')
    recipient_selection_mode = request.form.get('recipient_selection_mode') == 'manual'

    if recipient_selection_mode and not selected_ids:
        flash('Please select at least one applicant before sending emails.', 'danger')
        return redirect(url_for('job_applications.staff_dashboard'))

    query = JobApplication.query.filter_by(status=status, is_deleted=False)
    if selected_ids:
        parsed_ids = []
        for app_id in selected_ids:
            try:
                parsed_ids.append(int(app_id))
            except (TypeError, ValueError):
                continue
        if parsed_ids:
            query = query.filter(JobApplication.id.in_(parsed_ids))
        else:
            flash('No valid selected applicants were provided.', 'danger')
            return redirect(url_for('job_applications.staff_dashboard'))

    applications = query.all()
    if not applications:
        flash(f'No applications found with status: {status.replace("_", " ")}.', 'warning')
        return redirect(url_for('job_applications.staff_dashboard'))

    sent_count = 0
    failed = []

    for app_obj in applications:
        subject, message = build_status_email_content(
            app_obj,
            status,
            custom_message=custom_message,
            subject_override=subject_override or None
        )

        if not subject or not message:
            failed.append(f'#{app_obj.id} ({app_obj.email}): missing message content')
            continue

        ok, err = send_feedback_email(app_obj, subject, message)
        if ok:
            sent_count += 1
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            reviewer_name = current_user.name if getattr(current_user, 'name', None) else current_user.username
            note_entry = f"[{timestamp}] Email feedback sent for status '{status}' by {reviewer_name}. Subject: {subject}"
            if app_obj.review_notes:
                app_obj.review_notes = f"{app_obj.review_notes}\n\n{note_entry}"
            else:
                app_obj.review_notes = note_entry
            app_obj.reviewed_by = current_user.id
            app_obj.reviewed_at = datetime.utcnow()
        else:
            failed.append(f'#{app_obj.id} ({app_obj.email}): {err}')

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Emails processed, but failed to save logs: {str(e)}', 'warning')
        return redirect(url_for('job_applications.staff_dashboard'))

    if sent_count:
        flash(f'Sent {sent_count} professional feedback email(s) to {status.replace("_", " ")} applicants.', 'success')
    if failed:
        flash(f'{len(failed)} email(s) failed. Example: {failed[0]}', 'warning')

    return redirect(url_for('job_applications.staff_dashboard'))


@bp.route('/staff/applications-by-status', methods=['GET'])
@login_required
@staff_required
def staff_applications_by_status():
    """Return applicants filtered by status for selection UI."""
    status = request.args.get('status', '').strip()
    valid_statuses = ['submitted', 'under_review', 'shortlisted', 'accepted', 'rejected']
    if status not in valid_statuses:
        return jsonify({'ok': False, 'message': 'Invalid status'}), 400

    applications = JobApplication.query.filter_by(status=status, is_deleted=False).order_by(JobApplication.submitted_at.desc()).all()
    payload = [
        {
            'id': app_obj.id,
            'full_name': app_obj.full_name,
            'email': app_obj.email,
            'qualification_level': app_obj.qualification_level or '',
            'submitted_at': app_obj.submitted_at.strftime('%Y-%m-%d %H:%M') if app_obj.submitted_at else ''
        }
        for app_obj in applications
    ]

    return jsonify({'ok': True, 'applications': payload})


@bp.route('/staff/preview-feedback-by-status', methods=['POST'])
@login_required
@staff_required
def preview_feedback_by_status():
    """Generate exact preview email for selected status and applicant."""
    status = request.form.get('status', '').strip()
    subject_override = request.form.get('subject', '').strip()
    custom_message = request.form.get('custom_message', '').strip()
    selected_ids = request.form.getlist('selected_application_ids')

    valid_statuses = ['submitted', 'under_review', 'shortlisted', 'accepted', 'rejected']
    if status not in valid_statuses:
        return jsonify({'ok': False, 'message': 'Please choose a valid status.'}), 400

    preview_app = None
    for app_id in selected_ids:
        try:
            parsed_id = int(app_id)
        except (TypeError, ValueError):
            continue
        preview_app = JobApplication.query.filter_by(id=parsed_id, status=status, is_deleted=False).first()
        if preview_app:
            break

    if not preview_app:
        preview_app = JobApplication.query.filter_by(status=status, is_deleted=False).order_by(JobApplication.submitted_at.desc()).first()

    if not preview_app:
        return jsonify({'ok': False, 'message': 'No applicant found for the selected status.'}), 404

    if status == 'accepted' and not custom_message:
        return jsonify({'ok': False, 'message': 'Accepted status requires custom message before preview.'}), 400

    subject, message = build_status_email_content(
        preview_app,
        status,
        custom_message=custom_message,
        subject_override=subject_override or None
    )

    if not subject or not message:
        return jsonify({'ok': False, 'message': 'Unable to generate preview content.'}), 400

    return jsonify({
        'ok': True,
        'recipient': {
            'id': preview_app.id,
            'name': preview_app.full_name,
            'email': preview_app.email
        },
        'subject': subject,
        'body': message
    })


@bp.route('/staff/verify-document/<int:doc_id>', methods=['POST'])
@login_required
@staff_required
def verify_document(doc_id):
    """Verify a document"""
    doc = JobApplicationDocument.query.get_or_404(doc_id)
    verification_notes = request.form.get('verification_notes', '')
    
    try:
        doc.mark_as_verified(current_user.id, verification_notes)
        db.session.commit()
        flash('Document verified successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error verifying document: {str(e)}', 'danger')
    
    return redirect(url_for('job_applications.staff_view_application', app_id=doc.application_id))


@bp.route('/staff/download-document/<int:doc_id>')
@login_required
@staff_required
def download_document(doc_id):
    """Download a document"""
    doc = JobApplicationDocument.query.get_or_404(doc_id)
    
    if doc.is_deleted or not os.path.exists(doc.file_path):
        flash('Document not found.', 'danger')
        return redirect(url_for('job_applications.staff_view_application', app_id=doc.application_id))
    
    try:
        return send_file(
            doc.file_path,
            as_attachment=True,
            download_name=doc.original_filename,
            mimetype=doc.mime_type
        )
    except Exception as e:
        flash(f'Error downloading document: {str(e)}', 'danger')
        return redirect(url_for('job_applications.staff_view_application', app_id=doc.application_id))


@bp.route('/staff/view-document/<int:doc_id>')
@login_required
@staff_required
def view_document(doc_id):
    """View a document in browser"""
    doc = JobApplicationDocument.query.get_or_404(doc_id)
    
    if doc.is_deleted or not os.path.exists(doc.file_path):
        flash('Document not found.', 'danger')
        return redirect(url_for('job_applications.staff_view_application', app_id=doc.application_id))
    
    try:
        return send_file(
            doc.file_path,
            as_attachment=False,  # Don't force download, let browser handle it
            download_name=doc.original_filename,
            mimetype=doc.mime_type
        )
    except Exception as e:
        flash(f'Error viewing document: {str(e)}', 'danger')
        return redirect(url_for('job_applications.staff_view_application', app_id=doc.application_id))


@bp.route('/staff/delete-document/<int:doc_id>', methods=['POST'])
@login_required
@staff_required
def delete_document(doc_id):
    """Soft delete a document"""
    doc = JobApplicationDocument.query.get_or_404(doc_id)
    app_id = doc.application_id
    
    try:
        doc.is_deleted = True
        doc.deleted_at = datetime.utcnow()
        db.session.commit()
        flash('Document deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'danger')
    
    return redirect(url_for('job_applications.staff_view_application', app_id=app_id))


@bp.route('/staff/export-applications', methods=['POST'])
@login_required
@staff_required
def export_applications():
    """Export applications to CSV"""
    import csv
    from io import StringIO
    
    status_filter = request.form.get('status', 'all')
    
    query = JobApplication.query.filter_by(is_deleted=False)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    applications = query.all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Full Name', 'Email', 'Phone', 'Qualification', 'Status', 'Rating', 'Submitted Date', 'Reviewed Date', 'Has All Documents'])
    
    for app in applications:
        writer.writerow([
            app.id,
            app.full_name,
            app.email,
            app.phone_number,
            app.qualification_level or 'N/A',
            app.status,
            app.rating or 'N/A',
            app.submitted_at.strftime('%Y-%m-%d %H:%M'),
            app.reviewed_at.strftime('%Y-%m-%d %H:%M') if app.reviewed_at else 'Not reviewed',
            'Yes' if app.has_all_required_documents() else 'No'
        ])
    
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Disposition': 'attachment; filename=job_applications.csv',
        'Content-Type': 'text/csv'
    }


def ensure_dir(file_path):
    """Ensure directory exists for file"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
