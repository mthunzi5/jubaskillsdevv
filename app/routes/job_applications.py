from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.job_application import JobApplication, JobApplicationDocument
from app.models.user import User
from app.utils.decorators import staff_required
from datetime import datetime
import os
from config import Config

bp = Blueprint('job_applications', __name__, url_prefix='/job-applications')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'job_applications')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}

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


@bp.route('/')
def list_applications():
    """Public job applications page - info and apply button"""
    return render_template('job_applications/apply.html')


@bp.route('/apply', methods=['GET', 'POST'])
def start_application():
    """Start job application process"""
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
            return render_template('job_applications/apply.html')
        
        # Check if email has already submitted an application
        existing_application = JobApplication.query.filter_by(email=email, is_deleted=False).first()
        if existing_application:
            flash('An application has already been submitted with this email address.', 'warning')
            return render_template('job_applications/apply.html')
        
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
            return render_template('job_applications/apply.html')
    
    return render_template('job_applications/apply.html')


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
                         recent_applications=recent_applications)


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
