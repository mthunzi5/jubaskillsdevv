import os

from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user

from app.models.timesheet import TimesheetTemplate

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('public_home.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard redirect"""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_staff():
        return redirect(url_for('staff.dashboard'))
    elif current_user.is_intern():
        return redirect(url_for('intern.dashboard'))
    else:
        return redirect(url_for('auth.login'))

@bp.route('/timesheet-template/download')
@login_required
def download_timesheet_template():
    """Download the active timesheet template for a cohort (interns and host companies)."""
    cohort_id = request.args.get('cohort_id', type=int)
    fallback = request.referrer or url_for('main.dashboard')

    if not cohort_id:
        flash('No cohort selected for the timesheet template.', 'danger')
        return redirect(fallback)

    template = TimesheetTemplate.query.filter_by(cohort_id=cohort_id, is_active=True).first()
    if not template:
        flash('No active timesheet template found for this cohort.', 'danger')
        return redirect(fallback)

    abs_path = os.path.abspath(template.file_path)
    if not os.path.exists(abs_path):
        flash('Template file not found.', 'danger')
        return redirect(fallback)

    return send_file(abs_path, as_attachment=True, download_name=template.original_filename)
