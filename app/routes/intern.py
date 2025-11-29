from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.timesheet import Timesheet
from app.utils.decorators import intern_required, profile_complete_required
from app.utils.helpers import allowed_file, generate_filename, format_month_year, create_soft_delete_request
from datetime import datetime
import os

bp = Blueprint('intern', __name__, url_prefix='/intern')

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
    if request.method == 'POST':
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
        timesheet = Timesheet(
            intern_id=current_user.id,
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            submission_month=format_month_year(submission_date),
            submission_year=submission_date.year,
            submission_date=submission_date
        )
        
        db.session.add(timesheet)
        db.session.commit()
        
        flash('Timesheet submitted successfully!', 'success')
        return redirect(url_for('intern.timesheets'))
    
    return render_template('intern/submit_timesheet.html')

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
