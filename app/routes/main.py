import os

from flask import Blueprint, render_template, redirect, url_for, send_file, flash
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
    elif current_user.is_host_company():
        return redirect(url_for('host_company.dashboard'))
    else:
        return redirect(url_for('auth.login'))


@bp.route('/timesheets/template/download')
@login_required
def download_timesheet_template():
    """Download currently active timesheet template for interns/hosts/staff."""
    template = (
        TimesheetTemplate.query
        .filter_by(is_active=True)
        .order_by(TimesheetTemplate.created_at.desc())
        .first()
    )

    if not template:
        flash('No timesheet template is available yet. Please ask admin to upload one.', 'warning')
        return redirect(url_for('main.dashboard'))

    abs_path = os.path.abspath(template.file_path)
    if not os.path.exists(abs_path):
        flash('The active timesheet template file could not be found on the server.', 'danger')
        return redirect(url_for('main.dashboard'))

    return send_file(abs_path, as_attachment=True, download_name=template.original_filename)
