from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user

def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin():
            flash('Admin access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Decorator to require staff role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_staff():
            flash('Staff access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def intern_required(f):
    """Decorator to require intern role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_intern():
            flash('Intern access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def profile_complete_required(f):
    """Decorator to require complete profile"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_profile_complete and current_user.first_login:
            flash('Please complete your profile first.', 'info')
            return redirect(url_for('auth.complete_profile'))
        
        return f(*args, **kwargs)
    return decorated_function
