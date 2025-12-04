from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models.request_hub import Request, RequestSubmission, RequestDocument
from app.models.user import User
from app.models.notification import Notification
from app.models.recurring_request import RecurringRequest
from app.utils.decorators import staff_required
from app.utils.pdf_generator import generate_submission_receipt, download_submission_receipt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
from werkzeug.utils import secure_filename

request_hub_bp = Blueprint('request_hub', __name__, url_prefix='/request-hub')

# Staff Routes
@request_hub_bp.route('/staff')
@login_required
@staff_required
def staff_index():
    """Staff view: List all requests"""
    requests = Request.query.order_by(Request.created_at.desc()).all()
    
    # Calculate stats for each request
    request_stats = []
    for req in requests:
        expected = req.get_expected_count()
        submitted = req.get_submission_count()
        request_stats.append({
            'request': req,
            'expected': expected,
            'submitted': submitted,
            'completion_rate': (submitted / expected * 100) if expected > 0 else 0
        })
    
    return render_template('request_hub/staff_index.html', request_stats=request_stats)


@request_hub_bp.route('/staff/analytics')
@login_required
@staff_required
def analytics_dashboard():
    """Staff: View request hub analytics"""
    from sqlalchemy import func
    
    # Total requests
    total_requests = Request.query.count()
    active_requests = Request.query.filter_by(is_active=True).count()
    
    # Total submissions
    total_submissions = RequestSubmission.query.count()
    approved_submissions = RequestSubmission.query.filter_by(status='approved').count()
    rejected_submissions = RequestSubmission.query.filter_by(status='rejected').count()
    pending_submissions = RequestSubmission.query.filter_by(status='pending').count()
    
    # Average completion rate
    requests = Request.query.all()
    completion_rates = []
    for req in requests:
        expected = req.get_expected_count()
        submitted = req.get_submission_count()
        if expected > 0:
            completion_rates.append((submitted / expected) * 100)
    
    avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
    
    # Most requested document types
    document_type_stats = db.session.query(
        Request.request_type,
        func.count(Request.id).label('count')
    ).group_by(Request.request_type).order_by(func.count(Request.id).desc()).all()
    
    # Response time metrics (average time from request creation to submission)
    response_times = []
    for req in requests:
        for submission in req.submissions:
            time_diff = submission.submitted_at - req.created_at
            response_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Overdue submissions (requests with deadline passed but not all submitted)
    now = datetime.utcnow()
    overdue_count = 0
    overdue_requests = []
    for req in requests:
        if req.deadline and req.deadline < now and req.is_active:
            expected = req.get_expected_count()
            submitted = req.get_submission_count()
            if submitted < expected:
                overdue_count += (expected - submitted)
                overdue_requests.append({
                    'request': req,
                    'missing': expected - submitted
                })
    
    # Recent activity (last 7 days)
    from datetime import timedelta
    seven_days_ago = now - timedelta(days=7)
    recent_requests = Request.query.filter(Request.created_at >= seven_days_ago).count()
    recent_submissions = RequestSubmission.query.filter(RequestSubmission.submitted_at >= seven_days_ago).count()
    
    # Top submitters
    top_submitters = db.session.query(
        User.id,
        User.name,
        User.surname,
        func.count(RequestSubmission.id).label('submission_count')
    ).join(RequestSubmission, User.id == RequestSubmission.user_id
    ).group_by(User.id).order_by(func.count(RequestSubmission.id).desc()).limit(10).all()
    
    return render_template('request_hub/analytics.html',
                          total_requests=total_requests,
                          active_requests=active_requests,
                          total_submissions=total_submissions,
                          approved_submissions=approved_submissions,
                          rejected_submissions=rejected_submissions,
                          pending_submissions=pending_submissions,
                          avg_completion_rate=avg_completion_rate,
                          document_type_stats=document_type_stats,
                          avg_response_time=avg_response_time,
                          overdue_count=overdue_count,
                          overdue_requests=overdue_requests,
                          recent_requests=recent_requests,
                          recent_submissions=recent_submissions,
                          top_submitters=top_submitters)


@request_hub_bp.route('/staff/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_request():
    """Staff: Create a new request"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        request_type = request.form.get('request_type')
        target_type = request.form.get('target_type')
        target_user_id = request.form.get('target_user_id')
        
        requires_documents = request.form.get('requires_documents') == 'on'
        max_documents = int(request.form.get('max_documents', 5))
        requires_text = request.form.get('requires_text') == 'on'
        text_field_label = request.form.get('text_field_label')
        
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if deadline_str else None
        
        # Validation
        if not all([title, description, request_type, target_type]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('request_hub.create_request'))
        
        if target_type == 'specific' and not target_user_id:
            flash('Please select a specific user.', 'danger')
            return redirect(url_for('request_hub.create_request'))
        
        if max_documents < 1 or max_documents > 25:
            flash('Maximum documents must be between 1 and 25.', 'danger')
            return redirect(url_for('request_hub.create_request'))
        
        # Create request
        new_request = Request(
            title=title,
            description=description,
            request_type=request_type,
            target_type=target_type,
            target_user_id=target_user_id if target_type == 'specific' else None,
            requires_documents=requires_documents,
            max_documents=max_documents,
            requires_text=requires_text,
            text_field_label=text_field_label if requires_text else None,
            deadline=deadline,
            created_by_id=current_user.id
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        # Send notifications to targeted users
        Notification.notify_request_created(new_request)
        
        flash(f'Request "{title}" created successfully!', 'success')
        return redirect(url_for('request_hub.staff_index'))
    
    # GET request
    interns = User.query.filter_by(role='intern', is_deleted=False).order_by(User.name, User.surname).all()
    return render_template('request_hub/create_request.html', interns=interns)


@request_hub_bp.route('/staff/request/<int:request_id>')
@login_required
@staff_required
def view_request(request_id):
    """Staff: View request details and submissions"""
    req = Request.query.get_or_404(request_id)
    
    # Get all expected users
    target_users = req.get_target_users()
    
    # Get submissions with user info
    submissions = req.submissions.all()
    submission_dict = {sub.user_id: sub for sub in submissions}
    
    # Build comprehensive list
    submission_data = []
    for user in target_users:
        submission = submission_dict.get(user.id)
        submission_data.append({
            'user': user,
            'submission': submission,
            'has_submitted': submission is not None,
            'document_count': submission.get_document_count() if submission else 0
        })
    
    return render_template('request_hub/view_request.html', 
                          request=req, 
                          submission_data=submission_data)


@request_hub_bp.route('/staff/submission/<int:submission_id>')
@login_required
@staff_required
def view_submission(submission_id):
    """Staff: View a specific submission"""
    submission = RequestSubmission.query.get_or_404(submission_id)
    documents = submission.documents.all()
    
    return render_template('request_hub/view_submission.html', 
                          submission=submission,
                          documents=documents)


@request_hub_bp.route('/staff/submission/<int:submission_id>/review', methods=['POST'])
@login_required
@staff_required
def review_submission(submission_id):
    """Staff: Approve or reject a submission"""
    submission = RequestSubmission.query.get_or_404(submission_id)
    
    action = request.form.get('action')
    review_notes = request.form.get('review_notes')
    
    if action not in ['approve', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('request_hub.view_submission', submission_id=submission_id))
    
    submission.status = 'approved' if action == 'approve' else 'rejected'
    submission.reviewed_by_id = current_user.id
    submission.reviewed_at = datetime.utcnow()
    submission.review_notes = review_notes
    
    db.session.commit()
    
    # Notify intern about the review
    Notification.notify_submission_reviewed(submission)
    
    flash(f'Submission {action}d successfully!', 'success')
    return redirect(url_for('request_hub.view_request', request_id=submission.request_id))


@request_hub_bp.route('/staff/request/<int:request_id>/toggle', methods=['POST'])
@login_required
@staff_required
def toggle_request(request_id):
    """Staff: Toggle request active status"""
    req = Request.query.get_or_404(request_id)
    req.is_active = not req.is_active
    db.session.commit()
    
    status = 'activated' if req.is_active else 'deactivated'
    flash(f'Request {status} successfully!', 'success')
    return redirect(url_for('request_hub.staff_index'))


@request_hub_bp.route('/staff/request/<int:request_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_request(request_id):
    """Staff: Delete a request and all its submissions"""
    req = Request.query.get_or_404(request_id)
    
    # Delete associated files
    for submission in req.submissions:
        for document in submission.documents:
            try:
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)
            except Exception as e:
                print(f"Error deleting file: {e}")
    
    title = req.title
    db.session.delete(req)
    db.session.commit()
    
    flash(f'Request "{title}" deleted successfully!', 'success')
    return redirect(url_for('request_hub.staff_index'))


@request_hub_bp.route('/staff/request/<int:request_id>/download-all', methods=['GET'])
@login_required
@staff_required
def download_all_submissions(request_id):
    """Staff: Download all submissions as a ZIP file"""
    from io import BytesIO
    from zipfile import ZipFile
    
    req = Request.query.get_or_404(request_id)
    submissions = req.submissions.all()
    
    if not submissions:
        flash('No submissions to download.', 'warning')
        return redirect(url_for('request_hub.view_request', request_id=request_id))
    
    # Create in-memory ZIP file
    memory_file = BytesIO()
    
    with ZipFile(memory_file, 'w') as zipf:
        for submission in submissions:
            user = submission.user
            folder_name = f"{user.name}_{user.surname}_{user.id_number}"
            
            # Add submission info file
            info_content = f"""Submission Details
==================
Request: {req.title}
Submitted by: {user.name} {user.surname}
Email: {user.email}
ID Number: {user.id_number}
Submitted at: {submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}
Status: {submission.status}

"""
            if submission.text_content:
                info_content += f"Text Response:\n{submission.text_content}\n\n"
            
            if submission.reviewed_at:
                info_content += f"""Review Details:
Reviewed by: {submission.reviewed_by.name} {submission.reviewed_by.surname}
Reviewed at: {submission.reviewed_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
                if submission.review_notes:
                    info_content += f"Review notes: {submission.review_notes}\n"
            
            zipf.writestr(f"{folder_name}/submission_info.txt", info_content)
            
            # Add all documents
            for doc in submission.documents.all():
                if os.path.exists(doc.file_path):
                    doc_name = doc.document_name if doc.document_name else doc.original_filename
                    zipf.write(doc.file_path, f"{folder_name}/{doc_name}")
    
    memory_file.seek(0)
    
    # Generate filename
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"{req.title.replace(' ', '_')}_{timestamp}.zip"
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@request_hub_bp.route('/download/<int:document_id>')
@login_required
def download_document(document_id):
    """Download a request document"""
    document = RequestDocument.query.get_or_404(document_id)
    submission = document.submission
    
    # Check permissions
    if current_user.role == 'intern' and submission.user_id != current_user.id:
        flash('You do not have permission to download this file.', 'danger')
        return redirect(url_for('request_hub.intern_index'))
    
    if not os.path.exists(document.file_path):
        flash('File not found.', 'danger')
        return redirect(request.referrer or url_for('request_hub.intern_index'))
    
    return send_file(document.file_path, 
                    as_attachment=True, 
                    download_name=document.original_filename)


# Notification Routes
@request_hub_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications for current user"""
    all_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('request_hub/notifications.html', 
                          notifications=all_notifications,
                          unread_count=unread_count)


@request_hub_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('request_hub.notifications'))
    
    notification.mark_as_read()
    
    # Redirect to related object if specified
    if notification.related_type == 'request':
        if current_user.role == 'intern':
            return redirect(url_for('request_hub.intern_view_request', request_id=notification.related_id))
        else:
            return redirect(url_for('request_hub.view_request', request_id=notification.related_id))
    elif notification.related_type == 'submission':
        submission = RequestSubmission.query.get(notification.related_id)
        if submission:
            if current_user.role == 'intern':
                return redirect(url_for('request_hub.intern_view_request', request_id=submission.request_id))
            else:
                return redirect(url_for('request_hub.view_submission', submission_id=notification.related_id))
    
    return redirect(url_for('request_hub.notifications'))


@request_hub_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True, 'read_at': datetime.utcnow()})
    db.session.commit()
    
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('request_hub.notifications'))


@request_hub_bp.route('/notifications/unread-count')
@login_required
def unread_notification_count():
    """API endpoint to get unread notification count"""
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


# Intern Routes
@request_hub_bp.route('/intern')
@login_required
def intern_index():
    """Intern view: List assigned requests"""
    if current_user.role != 'intern':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all active requests
    all_requests = Request.query.filter_by(is_active=True).order_by(Request.created_at.desc()).all()
    
    # Filter requests that apply to this intern
    assigned_requests = []
    for req in all_requests:
        target_users = req.get_target_users()
        if current_user in target_users:
            submission = req.get_submission(current_user.id)
            assigned_requests.append({
                'request': req,
                'submission': submission,
                'has_submitted': submission is not None,
                'can_edit': submission is None or (req.deadline and datetime.utcnow() < req.deadline) if submission else True
            })
    
    return render_template('request_hub/intern_index.html', assigned_requests=assigned_requests)


@request_hub_bp.route('/intern/request/<int:request_id>')
@login_required
def intern_view_request(request_id):
    """Intern: View request details"""
    if current_user.role != 'intern':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    req = Request.query.get_or_404(request_id)
    
    # Check if this request applies to this intern
    target_users = req.get_target_users()
    if current_user not in target_users:
        flash('This request is not assigned to you.', 'danger')
        return redirect(url_for('request_hub.intern_index'))
    
    submission = req.get_submission(current_user.id)
    documents = submission.documents.all() if submission else []
    
    return render_template('request_hub/intern_view_request.html',
                          request=req,
                          submission=submission,
                          documents=documents)


@request_hub_bp.route('/intern/request/<int:request_id>/submit', methods=['POST'])
@login_required
def submit_request(request_id):
    """Intern: Submit or update submission"""
    if current_user.role != 'intern':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    req = Request.query.get_or_404(request_id)
    
    # Check if this request applies to this intern
    target_users = req.get_target_users()
    if current_user not in target_users:
        flash('This request is not assigned to you.', 'danger')
        return redirect(url_for('request_hub.intern_index'))
    
    # Check deadline
    if req.deadline and datetime.utcnow() > req.deadline:
        flash('The deadline for this request has passed.', 'danger')
        return redirect(url_for('request_hub.intern_view_request', request_id=request_id))
    
    # Get or create submission
    submission = req.get_submission(current_user.id)
    if not submission:
        submission = RequestSubmission(
            request_id=request_id,
            user_id=current_user.id
        )
        db.session.add(submission)
    
    # Update text content if required
    if req.requires_text:
        submission.text_content = request.form.get('text_content')
    
    submission.updated_at = datetime.utcnow()
    
    # Handle file uploads
    if req.requires_documents:
        files = request.files.getlist('documents')
        document_names = request.form.getlist('document_names')
        
        # Check current document count
        current_count = submission.get_document_count()
        new_file_count = len([f for f in files if f.filename])
        
        if current_count + new_file_count > req.max_documents:
            flash(f'You can only upload up to {req.max_documents} documents total.', 'danger')
            return redirect(url_for('request_hub.intern_view_request', request_id=request_id))
        
        # Process each file
        upload_folder = os.path.join('app', 'static', 'request_documents')
        os.makedirs(upload_folder, exist_ok=True)
        
        for i, file in enumerate(files):
            if file and file.filename:
                # Secure filename
                original_filename = secure_filename(file.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f"{current_user.id}_{timestamp}_{i}_{original_filename}"
                file_path = os.path.join(upload_folder, filename)
                
                # Save file
                file.save(file_path)
                
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Get document name
                doc_name = document_names[i] if i < len(document_names) else None
                
                # Create document record
                document = RequestDocument(
                    submission_id=submission.id,
                    filename=filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=file.content_type,
                    document_name=doc_name
                )
                db.session.add(document)
    
    db.session.commit()
    
    # Generate PDF receipt
    try:
        receipt_path = generate_submission_receipt(submission)
        flash('Your submission has been saved successfully! Receipt generated.', 'success')
    except Exception as e:
        print(f"Error generating receipt: {e}")
        flash('Your submission has been saved successfully!', 'success')
    
    return redirect(url_for('request_hub.intern_view_request', request_id=request_id))


@request_hub_bp.route('/intern/document/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Intern: Delete a document from their submission"""
    if current_user.role != 'intern':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    document = RequestDocument.query.get_or_404(document_id)
    submission = document.submission
    
    # Check ownership
    if submission.user_id != current_user.id:
        flash('You do not have permission to delete this file.', 'danger')
        return redirect(url_for('request_hub.intern_index'))
    
    # Check deadline
    req = submission.request
    if req.deadline and datetime.utcnow() > req.deadline:
        flash('The deadline has passed. You cannot modify your submission.', 'danger')
        return redirect(url_for('request_hub.intern_view_request', request_id=req.id))
    
    # Delete file
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    db.session.delete(document)
    db.session.commit()
    
    flash('Document deleted successfully!', 'success')
    return redirect(url_for('request_hub.intern_view_request', request_id=req.id))


# Recurring Requests Routes
@request_hub_bp.route('/staff/recurring')
@login_required
@staff_required
def recurring_requests():
    """Staff: View all recurring request templates"""
    recurring = RecurringRequest.query.order_by(RecurringRequest.created_at.desc()).all()
    return render_template('request_hub/recurring_requests.html', recurring_requests=recurring)


@request_hub_bp.route('/staff/recurring/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_recurring_request():
    """Staff: Create a new recurring request template"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        request_type = request.form.get('request_type')
        target_type = request.form.get('target_type')
        target_user_id = request.form.get('target_user_id')
        
        requires_documents = request.form.get('requires_documents') == 'on'
        max_documents = int(request.form.get('max_documents', 5))
        requires_text = request.form.get('requires_text') == 'on'
        text_field_label = request.form.get('text_field_label')
        
        recurrence_pattern = request.form.get('recurrence_pattern')
        recurrence_day = request.form.get('recurrence_day')
        deadline_days_after = int(request.form.get('deadline_days_after', 7))
        
        # Validation
        if not all([title, description, request_type, target_type, recurrence_pattern]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('request_hub.create_recurring_request'))
        
        # Create recurring request
        new_recurring = RecurringRequest(
            title=title,
            description=description,
            request_type=request_type,
            target_type=target_type,
            target_user_id=target_user_id if target_type == 'specific' else None,
            requires_documents=requires_documents,
            max_documents=max_documents,
            requires_text=requires_text,
            text_field_label=text_field_label if requires_text else None,
            recurrence_pattern=recurrence_pattern,
            recurrence_day=int(recurrence_day) if recurrence_day else None,
            deadline_days_after=deadline_days_after,
            created_by_id=current_user.id
        )
        
        # Calculate first creation date
        new_recurring.next_creation_at = new_recurring.calculate_next_creation()
        
        db.session.add(new_recurring)
        db.session.commit()
        
        flash(f'Recurring request "{title}" created successfully!', 'success')
        return redirect(url_for('request_hub.recurring_requests'))
    
    # GET request
    interns = User.query.filter_by(role='intern', is_deleted=False).order_by(User.name, User.surname).all()
    return render_template('request_hub/create_recurring.html', interns=interns)


@request_hub_bp.route('/staff/recurring/<int:recurring_id>/toggle', methods=['POST'])
@login_required
@staff_required
def toggle_recurring_request(recurring_id):
    """Staff: Toggle recurring request active status"""
    recurring = RecurringRequest.query.get_or_404(recurring_id)
    recurring.is_active = not recurring.is_active
    db.session.commit()
    
    status = 'activated' if recurring.is_active else 'deactivated'
    flash(f'Recurring request {status} successfully!', 'success')
    return redirect(url_for('request_hub.recurring_requests'))


@request_hub_bp.route('/staff/recurring/<int:recurring_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_recurring_request(recurring_id):
    """Staff: Delete a recurring request template"""
    recurring = RecurringRequest.query.get_or_404(recurring_id)
    title = recurring.title
    
    db.session.delete(recurring)
    db.session.commit()
    
    flash(f'Recurring request "{title}" deleted successfully!', 'success')
    return redirect(url_for('request_hub.recurring_requests'))


@request_hub_bp.route('/staff/recurring/<int:recurring_id>/create-now', methods=['POST'])
@login_required
@staff_required
def create_from_recurring_now(recurring_id):
    """Staff: Manually trigger creation of a request from recurring template"""
    recurring = RecurringRequest.query.get_or_404(recurring_id)
    
    try:
        new_request = recurring.create_request_instance()
        flash(f'Request "{new_request.title}" created successfully from template!', 'success')
    except Exception as e:
        flash(f'Error creating request: {str(e)}', 'danger')
    
    return redirect(url_for('request_hub.recurring_requests'))


@request_hub_bp.route('/submission/<int:submission_id>/receipt')
@login_required
def download_receipt(submission_id):
    """Download submission receipt"""
    submission = RequestSubmission.query.get_or_404(submission_id)
    
    # Check permissions
    if current_user.role == 'intern' and submission.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('request_hub.intern_index'))
    
    # Check if receipt already exists
    receipt_path = download_submission_receipt(submission_id)
    
    if not receipt_path or not os.path.exists(receipt_path):
        # Generate receipt if it doesn't exist
        try:
            receipt_path = generate_submission_receipt(submission)
        except Exception as e:
            flash(f'Error generating receipt: {str(e)}', 'danger')
            return redirect(request.referrer or url_for('request_hub.intern_index'))
    
    return send_file(receipt_path, 
                    as_attachment=True,
                    download_name=f'submission_receipt_{submission_id}.pdf')
