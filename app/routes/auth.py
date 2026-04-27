from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


def _is_safe_next_url(target):
    """Allow redirects only to local URLs."""
    if not target:
        return False

    current_host = urlparse(request.host_url)
    target_url = urlparse(target)
    return target_url.scheme in ('', current_host.scheme) and target_url.netloc in ('', current_host.netloc)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email_or_id = request.form.get('email_or_id')
        password = request.form.get('password')
        
        # Validate input
        if not email_or_id or not password:
            flash('Please provide both email/ID number and password.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Try to find user by email or ID number
        user = User.query.filter(
            (User.email == email_or_id) | (User.id_number == email_or_id)
        ).first()
        
        # Check if user exists
        if not user:
            flash('Invalid email/ID number or password.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if password is correct
        if not user.check_password(password):
            flash('Invalid email/ID number or password.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if account is deleted
        if user.is_deleted:
            flash('Your account has been deactivated. Contact administrator.', 'danger')
            return redirect(url_for('auth.login'))

        # Drop any stale session state before creating a fresh login session.
        session.clear()
        
        # Login successful
        login_user(user, fresh=True)
        session.permanent = True
        
        # Update last login time
        user.update_last_login()
        db.session.commit()
        
        # Check if password change is required (after reset)
        if user.requires_password_change:
            flash('Please change your password for security.', 'warning')
            return redirect(url_for('auth.change_password'))
        
        # Check if first login and profile incomplete
        if user.first_login and not user.is_profile_complete:
            return redirect(url_for('auth.complete_profile'))
        
        flash(f'Welcome back, {user.name or "User"}!', 'success')
        next_page = request.args.get('next')
        if next_page and _is_safe_next_url(next_page):
            return redirect(next_page)
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    session.clear()
    logout_user()
    response = redirect(url_for('auth.login'))
    response.delete_cookie(current_app.config.get('REMEMBER_COOKIE_NAME', 'remember_token'))
    flash('You have been logged out successfully.', 'info')
    return response

@bp.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    """Complete profile on first login"""
    if not current_user.first_login or current_user.is_profile_complete:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.surname = request.form.get('surname')
        
        # Only allow interns to change email, and check for duplicates
        if current_user.is_intern():
            new_email = request.form.get('email')
            if new_email != current_user.email:
                # Check if email already exists
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user and existing_user.id != current_user.id:
                    flash('Email address already in use. Please use a different email.', 'danger')
                    return render_template('auth/complete_profile.html')
                current_user.email = new_email
        
        current_user.phone = request.form.get('phone')
        
        # Optional password change
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
        
        current_user.is_profile_complete = True
        current_user.first_login = False
        
        db.session.commit()
        flash('Profile completed successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/complete_profile.html')

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
        elif not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        else:
            current_user.set_password(new_password)
            current_user.requires_password_change = False
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('auth/change_password.html')

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password - reset using last 5 digits of ID number"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email_or_id = request.form.get('email_or_id', '').strip()
        last_5_digits = request.form.get('last_5_digits', '').strip()
        
        if not email_or_id or not last_5_digits:
            flash('Please provide your email/ID number and last 5 digits of ID number.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # Validate last 5 digits is numeric and exactly 5 digits
        if not last_5_digits.isdigit() or len(last_5_digits) != 5:
            flash('Last 5 digits must be exactly 5 numeric digits.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # Find user by email or ID number
        user = User.query.filter(
            ((User.email == email_or_id) | (User.id_number == email_or_id)) &
            (User.is_deleted == False)
        ).first()
        
        if user and user.id_number and user.id_number.endswith(last_5_digits):
            # Reset password to default
            user.set_password('JubaFuture2025')
            user.requires_password_change = True
            db.session.commit()
            
            flash('Password has been reset to: JubaFuture2025. Please login and change your password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid credentials or ID number verification failed.', 'danger')
            return redirect(url_for('auth.forgot_password'))
    
    return render_template('auth/forgot_password.html')

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        else:
            user.set_password(new_password)
            user.clear_reset_token()
            db.session.commit()
            flash('Password reset successfully! You can now login.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)
