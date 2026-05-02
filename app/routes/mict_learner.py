from flask import Blueprint, Response, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.mict_learner import MictLearnerProfile
from app.utils.decorators import staff_required
from datetime import datetime
import csv
import io
import re
import time

bp = Blueprint('mict_learner', __name__, url_prefix='/mict-learner')

SA_ID_REGEX = re.compile(r'^\d{13}$')
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_ALLOWED_REGEX = re.compile(r'^\+?[0-9\s\-()]+$')
RATE_LIMIT_STATE = {}


def _get_client_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _is_rate_limited(scope, limit_count, window_seconds):
    """Simple in-memory sliding window limiter keyed by IP and route scope."""
    now = time.time()
    ip = _get_client_ip()
    key = f'{scope}:{ip}'
    entries = RATE_LIMIT_STATE.get(key, [])
    recent_entries = [ts for ts in entries if now - ts < window_seconds]
    if len(recent_entries) >= limit_count:
        RATE_LIMIT_STATE[key] = recent_entries
        return True
    recent_entries.append(now)
    RATE_LIMIT_STATE[key] = recent_entries
    return False


def _is_valid_sa_id(id_number):
    return bool(SA_ID_REGEX.match(id_number))


def _is_valid_email(value):
    return bool(EMAIL_REGEX.match(value))


def _is_valid_phone(value):
    if not PHONE_ALLOWED_REGEX.match(value):
        return False
    digits_only = re.sub(r'\D', '', value)
    return 10 <= len(digits_only) <= 15


def _build_profile_query(search_text=None):
    query = MictLearnerProfile.query
    if search_text:
        like = f'%{search_text}%'
        query = query.filter(
            db.or_(
                MictLearnerProfile.id_number.ilike(like),
                MictLearnerProfile.first_name.ilike(like),
                MictLearnerProfile.last_name.ilike(like),
                MictLearnerProfile.contact_email.ilike(like),
            )
        )
    return query

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ROUTES  (no login required)
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/', methods=['GET', 'POST'])
def lookup():
    """Public landing page. Learner enters their SA ID to start / continue."""
    if request.method == 'POST':
        if _is_rate_limited('mict_learner_lookup', limit_count=25, window_seconds=600):
            flash('Too many requests. Please wait a few minutes and try again.', 'warning')
            return redirect(url_for('mict_learner.lookup'))

        id_number = (request.form.get('id_number') or '').strip()
        if not id_number:
            flash('Please enter your ID number.', 'warning')
            return redirect(url_for('mict_learner.lookup'))
        if not _is_valid_sa_id(id_number):
            flash('SA ID number must be exactly 13 digits.', 'warning')
            return redirect(url_for('mict_learner.lookup'))
        return redirect(url_for('mict_learner.submit_form', id_number=id_number))
    return render_template('mict_learner/lookup.html')


@bp.route('/form', methods=['GET', 'POST'])
def submit_form():
    """Public multi-section form. Pre-fills existing data if the learner has submitted before."""
    id_number = (request.args.get('id_number') or '').strip()

    if not id_number:
        flash('No ID number provided. Please start from the lookup page.', 'warning')
        return redirect(url_for('mict_learner.lookup'))
    if not _is_valid_sa_id(id_number):
        flash('SA ID number must be exactly 13 digits.', 'warning')
        return redirect(url_for('mict_learner.lookup'))

    profile = MictLearnerProfile.query.filter_by(id_number=id_number).first()

    if request.method == 'POST':
        if _is_rate_limited('mict_learner_submit', limit_count=15, window_seconds=600):
            flash('Too many submissions in a short time. Please wait a few minutes and try again.', 'warning')
            return redirect(url_for('mict_learner.submit_form', id_number=id_number))

        # Collect all form data
        data = {
            'first_name': request.form.get('first_name', '').strip() or None,
            'last_name': request.form.get('last_name', '').strip() or None,
            'personal_email': request.form.get('personal_email', '').strip() or None,

            'physical_address_line1': request.form.get('physical_address_line1', '').strip() or None,
            'physical_address_line2': request.form.get('physical_address_line2', '').strip() or None,
            'physical_address_line3': request.form.get('physical_address_line3', '').strip() or None,
            'physical_postal_code': request.form.get('physical_postal_code', '').strip() or None,

            'postal_address_line1': request.form.get('postal_address_line1', '').strip() or None,
            'postal_address_line2': request.form.get('postal_address_line2', '').strip() or None,
            'postal_address_line3': request.form.get('postal_address_line3', '').strip() or None,
            'postal_postal_code': request.form.get('postal_postal_code', '').strip() or None,

            'area_type': request.form.get('area_type', '').strip() or None,
            'contact_email': request.form.get('contact_email', '').strip() or None,
            'telephone_number': request.form.get('telephone_number', '').strip() or None,
            'cellphone_number': request.form.get('cellphone_number', '').strip() or None,

            'guardian_first_name': request.form.get('guardian_first_name', '').strip() or None,
            'guardian_last_name': request.form.get('guardian_last_name', '').strip() or None,
            'guardian_id_type': request.form.get('guardian_id_type', '').strip() or None,
            'guardian_id_number': request.form.get('guardian_id_number', '').strip() or None,
            'guardian_telephone': request.form.get('guardian_telephone', '').strip() or None,
            'guardian_cellphone': request.form.get('guardian_cellphone', '').strip() or None,
            'guardian_home_address': request.form.get('guardian_home_address', '').strip() or None,
            'guardian_postal_address': request.form.get('guardian_postal_address', '').strip() or None,
            'guardian_email': request.form.get('guardian_email', '').strip() or None,

            'highest_nqf_level': request.form.get('highest_nqf_level', '').strip() or None,
            'nqf_other': request.form.get('nqf_other', '').strip() or None,
            'qualification_title': request.form.get('qualification_title', '').strip() or None,
            'has_matriculated': request.form.get('has_matriculated', '').strip() or None,
            'matriculated_in_sa': request.form.get('matriculated_in_sa', '').strip() or None,
            'matric_province': request.form.get('matric_province', '').strip() or None,
            'matric_high_school': request.form.get('matric_high_school', '').strip() or None,
            'institution_type': request.form.get('institution_type', '').strip() or None,
            'institution_name': request.form.get('institution_name', '').strip() or None,
        }

        validation_errors = []
        email_fields = [
            ('personal_email', 'Learner Email'),
            ('contact_email', 'Contact Email'),
            ('guardian_email', 'Guardian Email'),
        ]
        phone_fields = [
            ('telephone_number', 'Telephone Number'),
            ('cellphone_number', 'Cellphone Number'),
            ('guardian_telephone', 'Guardian Telephone'),
            ('guardian_cellphone', 'Guardian Cellphone'),
        ]

        for key, label in email_fields:
            value = data.get(key)
            if value and not _is_valid_email(value):
                validation_errors.append(f'{label} format is invalid.')

        for key, label in phone_fields:
            value = data.get(key)
            if value and not _is_valid_phone(value):
                validation_errors.append(f'{label} must contain 10-15 digits and only valid phone characters.')

        if validation_errors:
            for error in validation_errors:
                flash(error, 'warning')
            return redirect(url_for('mict_learner.submit_form', id_number=id_number))

        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
            profile.submission_count += 1
            profile.updated_at = datetime.utcnow()
            flash('Your details have been updated successfully!', 'success')
        else:
            profile = MictLearnerProfile(id_number=id_number, **data)
            db.session.add(profile)
            flash('Your details have been submitted successfully!', 'success')

        db.session.commit()
        return redirect(url_for('mict_learner.submit_form', id_number=id_number))

    return render_template('mict_learner/form.html', profile=profile, id_number=id_number)


# ─────────────────────────────────────────────────────────────────────────────
# STAFF / ADMIN ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/admin/list')
@login_required
@staff_required
def admin_list():
    """List all submitted learner profiles."""
    search = request.args.get('q', '').strip()
    query = _build_profile_query(search)
    profiles = query.order_by(MictLearnerProfile.submitted_at.desc()).all()
    return render_template('mict_learner/admin_list.html', profiles=profiles, search=search)


@bp.route('/admin/export.csv')
@login_required
@staff_required
def export_csv():
    """Export learner profiles to CSV for batch processing/submission."""
    search = request.args.get('q', '').strip()
    profiles = _build_profile_query(search).order_by(MictLearnerProfile.submitted_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'SA ID Number', 'First Name', 'Last Name', 'Learner Email',
        'Contact Email', 'Telephone', 'Cellphone', 'Guardian First Name',
        'Guardian Last Name', 'Guardian Email', 'Highest NQF Level',
        'Qualification Title', 'Institution Type', 'Institution Name',
        'Submission Count', 'Submitted At', 'Updated At'
    ])

    for p in profiles:
        writer.writerow([
            p.id_number or '', p.first_name or '', p.last_name or '', p.personal_email or '',
            p.contact_email or '', p.telephone_number or '', p.cellphone_number or '',
            p.guardian_first_name or '', p.guardian_last_name or '', p.guardian_email or '',
            p.highest_nqf_level or '', p.qualification_title or '', p.institution_type or '',
            p.institution_name or '', p.submission_count or 0,
            p.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if p.submitted_at else '',
            p.updated_at.strftime('%Y-%m-%d %H:%M:%S') if p.updated_at else '',
        ])

    csv_data = output.getvalue()
    output.close()

    filename = 'mict_learner_profiles.csv' if not search else 'mict_learner_profiles_filtered.csv'
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )


@bp.route('/admin/<int:profile_id>')
@login_required
@staff_required
def admin_detail(profile_id):
    """View full detail of a single learner profile."""
    profile = MictLearnerProfile.query.get_or_404(profile_id)
    return render_template('mict_learner/admin_detail.html', profile=profile)
