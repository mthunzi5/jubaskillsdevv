from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from app.models.timesheet import Timesheet
from app.models.user import User
from app.utils.decorators import staff_required
from datetime import datetime
import os
from io import BytesIO
from zipfile import ZipFile

bp = Blueprint('staff', __name__, url_prefix='/staff')

@bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    """Staff dashboard"""
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
    
    return render_template('staff/timesheets.html',
                         timesheets=timesheets,
                         month_filter=month_filter,
                         intern_type_filter=intern_type_filter,
                         available_months=available_months)

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
            timesheet.file_path,
            as_attachment=True,
            download_name=timesheet.original_filename
        )
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
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
    
    timesheets = query.all()
    
    if not timesheets:
        flash('No timesheets found for the selected filters.', 'warning')
        return redirect(url_for('staff.timesheets'))
    
    # Create ZIP file in memory
    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for timesheet in timesheets:
            if os.path.exists(timesheet.file_path):
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
                
                zf.write(timesheet.file_path, zip_filename)
    
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
