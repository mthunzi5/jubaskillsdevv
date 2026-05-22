import os

from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user

from app.models.intern_management import CohortMember, HostCompany, InternPlacement
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
    """Download active timesheet template for a cohort, scoped by the current user's role."""
    cohort_id = request.args.get('cohort_id', type=int)
    allowed_cohort_ids = set()

    if current_user.is_intern():
        active_placement = (
            InternPlacement.query
            .filter_by(intern_id=current_user.id, is_active=True)
            .order_by(InternPlacement.assigned_at.desc())
            .first()
        )
        if active_placement and active_placement.cohort_id:
            allowed_cohort_ids.add(active_placement.cohort_id)

        if not allowed_cohort_ids:
            latest_membership = (
                CohortMember.query
                .filter_by(intern_id=current_user.id)
                .order_by(CohortMember.created_at.desc())
                .first()
            )
            if latest_membership and latest_membership.cohort_id:
                allowed_cohort_ids.add(latest_membership.cohort_id)

        if not cohort_id and allowed_cohort_ids:
            cohort_id = sorted(allowed_cohort_ids)[0]

    elif current_user.is_host_company():
        host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
        if not host:
            flash('Host company profile not found.', 'danger')
            return redirect(url_for('host_company.dashboard'))

        placements = InternPlacement.query.filter_by(host_company_id=host.id, is_active=True).all()
        allowed_cohort_ids = {p.cohort_id for p in placements if p.cohort_id}

        if not cohort_id and len(allowed_cohort_ids) == 1:
            cohort_id = next(iter(allowed_cohort_ids))

    else:
        flash('Only intern and host company users can download templates from this page.', 'warning')
        return redirect(url_for('main.dashboard'))

    if not cohort_id:
        flash('Please select a cohort before downloading a template.', 'warning')
        return redirect(request.referrer or url_for('main.dashboard'))

    if allowed_cohort_ids and cohort_id not in allowed_cohort_ids:
        flash('You do not have access to templates for this cohort.', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))

    template = (
        TimesheetTemplate.query
        .filter_by(cohort_id=cohort_id, is_active=True)
        .order_by(TimesheetTemplate.created_at.desc())
        .first()
    )

    if not template:
        flash('No active timesheet template found for the selected cohort.', 'warning')
        return redirect(request.referrer or url_for('main.dashboard'))

    abs_path = os.path.abspath(template.file_path)
    if not os.path.exists(abs_path):
        flash('Template file is missing on the server.', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))

    return send_file(abs_path, as_attachment=True, download_name=template.original_filename)
