from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

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
