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
    """Decorator to require staff or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not (current_user.is_staff() or current_user.is_admin()):
            flash('Staff or admin access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def host_company_required(f):
    """Decorator to require host company role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        if not current_user.is_host_company():
            flash('Host company access required.', 'danger')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    """Decorator to require a specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            if not current_user.has_permission(permission):
                flash('You do not have permission to perform this action.', 'danger')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

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
