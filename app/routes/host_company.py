from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import current_user, login_required
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from app import db
from app.models.intern_management import HostCompany, InternPlacement, Cohort
from app.models.timesheet import Timesheet
from app.models.notification import Notification
from app.utils.decorators import host_company_required, permission_required
from app.utils.audit import log_audit_event

bp = Blueprint('host_company', __name__, url_prefix='/host-company')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/dashboard')
@login_required
@host_company_required
@permission_required('view_host_dashboard')
def dashboard():
    """Host company dashboard showing assigned interns grouped by cohort."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()

    cohorts_data = {}
    if host:
        # Get all active placements for this host
        placements = (
            InternPlacement.query
            .filter_by(host_company_id=host.id, is_active=True)
            .order_by(InternPlacement.assigned_at.desc())
            .all()
        )
        
        # Group interns by cohort
        for placement in placements:
            cohort = placement.cohort
            if cohort:
                if cohort.id not in cohorts_data:
                    cohorts_data[cohort.id] = {
                        'cohort': cohort,
                        'interns': []
                    }
                cohorts_data[cohort.id]['interns'].append(placement)

    return render_template('host_company/dashboard.html', host=host, cohorts_data=cohorts_data)


@bp.route('/cohorts/<int:cohort_id>/interns')
@login_required
@host_company_required
def cohort_interns(cohort_id):
    """Return active interns for this host in a specific cohort."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        return jsonify({'ok': False, 'message': 'Host company not found'}), 404

    month = (request.args.get('month') or '').strip()

    placements = (
        InternPlacement.query
        .filter_by(host_company_id=host.id, cohort_id=cohort_id, is_active=True)
        .order_by(InternPlacement.assigned_at.desc())
        .all()
    )

    interns = []
    seen = set()
    for placement in placements:
        if not placement.intern or placement.intern.id in seen:
            continue
        seen.add(placement.intern.id)
        existing = None
        if month and len(month) == 7 and '-' in month:
            existing = (
                Timesheet.query
                .filter_by(intern_id=placement.intern.id, submission_month=month, is_deleted=False)
                .order_by(Timesheet.submission_date.desc())
                .first()
            )

        submitted_by = None
        submitted_at = None
        if existing:
            submitted_by = 'host' if existing.host_company_id else 'intern'
            submitted_at = existing.submission_date.strftime('%Y-%m-%d %H:%M') if existing.submission_date else None

        interns.append({
            'id': placement.intern.id,
            'name': placement.intern.name or '',
            'surname': placement.intern.surname or '',
            'id_number': placement.intern.id_number or '',
            'intern_type': placement.intern.intern_type or 'mixed',
            'already_submitted': bool(existing),
            'submitted_by': submitted_by,
            'submitted_at': submitted_at,
        })

    return jsonify({'ok': True, 'interns': interns})


@bp.route('/timesheets/submit', methods=['GET', 'POST'])
@login_required
@host_company_required
def submit_timesheets():
    """Host company submission of timesheets for a cohort/month."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))
    
    # Get unique cohorts this host has interns in
    active_placements = (
        InternPlacement.query
        .filter_by(host_company_id=host.id, is_active=True)
        .all()
    )
    
    cohort_ids = {p.cohort_id for p in active_placements if p.cohort_id}
    cohorts = Cohort.query.filter(Cohort.id.in_(cohort_ids)).all() if cohort_ids else []
    
    if request.method == 'POST':
        cohort_id = request.form.get('cohort_id', type=int)
        submission_month = request.form.get('submission_month')
        selected_interns = request.form.getlist('interns')
        
        if not cohort_id or not submission_month or not selected_interns:
            flash('Please select cohort, month, and at least one intern.', 'danger')
            return redirect(url_for('host_company.submit_timesheets'))
        
        # Validate cohort belongs to this host
        cohort = Cohort.query.get_or_404(cohort_id)
        host_interns_in_cohort = {
            p.intern_id for p in active_placements
            if p.cohort_id == cohort_id
        }
        
        submitted_count = 0
        errors = []
        
        for intern_id_str in selected_interns:
            try:
                intern_id = int(intern_id_str)
            except ValueError:
                continue
            
            if intern_id not in host_interns_in_cohort:
                errors.append(f'Intern {intern_id} not assigned to this cohort at your host.')
                continue

            existing = (
                Timesheet.query
                .filter_by(intern_id=intern_id, submission_month=submission_month, is_deleted=False)
                .order_by(Timesheet.submission_date.desc())
                .first()
            )
            if existing:
                submitter_label = 'host company' if existing.host_company_id else 'intern'
                errors.append(f'Intern {intern_id} already has a {submission_month} timesheet submitted by {submitter_label}.')
                continue
            
            file = request.files.get(f'timesheet_{intern_id}')
            if not file or file.filename == '':
                errors.append(f'No file selected for intern {intern_id}.')
                continue
            
            if not allowed_file(file.filename):
                errors.append(f'File type not allowed for intern {intern_id}. Use PDF, DOC, DOCX, XLS, XLSX.')
                continue
            
            # Save file using absolute path so DB records are portable
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
            uploads_dir = os.path.join(base_dir, 'app', 'static', 'submissions')
            os.makedirs(uploads_dir, exist_ok=True)
            
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            saved_filename = f"{cohort_id}_{intern_id}_{timestamp}_{filename}"
            file_path = os.path.join(uploads_dir, saved_filename)
            
            file.save(file_path)
            
            # Create timesheet record
            year = int(submission_month.split('-')[0])
            timesheet = Timesheet(
                intern_id=intern_id,
                cohort_id=cohort_id,
                host_company_id=host.id,
                submitted_by=current_user.id,
                filename=saved_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                submission_month=submission_month,
                submission_year=year,
                submission_date=datetime.utcnow()
            )
            db.session.add(timesheet)
            submitted_count += 1
        
        db.session.commit()
        
        # Send notifications to interns
        for intern_id_str in selected_interns:
            try:
                intern_id = int(intern_id_str)
                if intern_id in host_interns_in_cohort:
                    Notification.create_notification(
                        user_id=intern_id,
                        title='Timesheet Submitted',
                        message=f'{host.company_name} submitted your timesheet for {submission_month}.',
                        notification_type='timesheet_submitted',
                        related_type='timesheet',
                        related_id=None,
                    )
            except:
                pass
        
        log_audit_event(
            actor_user_id=current_user.id,
            action='host_submitted_cohort_timesheets',
            entity_type='cohort',
            entity_id=cohort_id,
            details={
                'host_company_id': host.id,
                'submission_month': submission_month,
                'interns_submitted': submitted_count,
                'errors': errors,
            },
        )
        
        flash(f'Submitted {submitted_count} timesheet(s) successfully.', 'success')
        if errors:
            flash('Errors: ' + ' | '.join(errors), 'warning')
        return redirect(url_for('host_company.submit_timesheets'))
    
    return render_template('host_company/submit_timesheets.html', cohorts=cohorts)


@bp.route('/timesheets/view')
@login_required
@host_company_required
def view_timesheets():
    """View submitted timesheets by this host."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))
    
    month_filter = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    cohort_filter = request.args.get('cohort_id', 'all')
    
    query = Timesheet.query.filter_by(host_company_id=host.id, is_deleted=False)

    if month_filter and month_filter != 'all':
        query = query.filter_by(submission_month=month_filter)
    
    if cohort_filter != 'all':
        try:
            cohort_id = int(cohort_filter)
            query = query.filter_by(cohort_id=cohort_id)
        except ValueError:
            pass
    
    timesheets = query.order_by(Timesheet.submission_date.desc()).all()
    
    # Get available months and cohorts
    available_months = db.session.query(Timesheet.submission_month).distinct().filter(
        Timesheet.host_company_id == host.id,
        Timesheet.is_deleted == False
    ).order_by(Timesheet.submission_month.desc()).all()
    available_months = [m[0] for m in available_months]
    
    # Get cohorts this host has submitted timesheets for
    cohorts = db.session.query(Cohort).join(
        Timesheet, Cohort.id == Timesheet.cohort_id
    ).filter(
        Timesheet.host_company_id == host.id,
        Timesheet.is_deleted == False
    ).distinct().all()
    
    return render_template(
        'host_company/view_timesheets.html',
        timesheets=timesheets,
        available_months=available_months,
        cohorts=cohorts,
        month_filter=month_filter,
        cohort_filter=cohort_filter
    )


@bp.route('/timesheets/<int:timesheet_id>/download')
@login_required
@host_company_required
def download_timesheet(timesheet_id):
    """Allow host company to download own submitted timesheets only."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    timesheet = Timesheet.query.get_or_404(timesheet_id)
    if timesheet.host_company_id != host.id:
        flash('You do not have access to this timesheet.', 'danger')
        return redirect(url_for('host_company.view_timesheets'))

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'warning')
        return redirect(url_for('host_company.view_timesheets'))

    try:
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=True,
            download_name=timesheet.original_filename,
        )
    except Exception as exc:
        flash(f'Error downloading file: {exc}', 'danger')
        return redirect(url_for('host_company.view_timesheets'))


@bp.route('/timesheets/<int:timesheet_id>/view')
@login_required
@host_company_required
def view_timesheet(timesheet_id):
    """Allow host company to preview own submitted timesheets only."""
    host = HostCompany.query.filter_by(login_user_id=current_user.id, is_active=True).first()
    if not host:
        flash('Host company not found.', 'danger')
        return redirect(url_for('host_company.dashboard'))

    timesheet = Timesheet.query.get_or_404(timesheet_id)
    if timesheet.host_company_id != host.id:
        flash('You do not have access to this timesheet.', 'danger')
        return redirect(url_for('host_company.view_timesheets'))

    if timesheet.is_deleted:
        flash('This timesheet has been deleted.', 'warning')
        return redirect(url_for('host_company.view_timesheets'))

    try:
        return send_file(
            os.path.abspath(timesheet.file_path),
            as_attachment=False,
            download_name=timesheet.original_filename,
        )
    except Exception as exc:
        flash(f'Error opening file: {exc}', 'danger')
        return redirect(url_for('host_company.view_timesheets'))
