from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.deletion_history import DeletionHistory
from app.models.soft_delete import SoftDelete
from app.models.timesheet import Timesheet
from app.utils.decorators import admin_required
from app.utils.helpers import save_deletion_history
from datetime import datetime
import json

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    total_users = User.query.filter_by(is_deleted=False).count()
    total_admins = User.query.filter_by(role='admin', is_deleted=False).count()
    total_staff = User.query.filter_by(role='staff', is_deleted=False).count()
    total_interns = User.query.filter_by(role='intern', is_deleted=False).count()
    pending_approvals = SoftDelete.query.filter_by(approved=False).count()
    
    recent_deletions = DeletionHistory.query.order_by(DeletionHistory.deletion_date.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_admins=total_admins,
                         total_staff=total_staff,
                         total_interns=total_interns,
                         pending_approvals=pending_approvals,
                         recent_deletions=recent_deletions)

@bp.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    role_filter = request.args.get('role', 'all')
    
    query = User.query.filter_by(is_deleted=False)
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, role_filter=role_filter)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user"""
    if request.method == 'POST':
        role = request.form.get('role')
        
        if role == 'intern':
            # Create intern
            id_number = request.form.get('id_number')
            intern_type = request.form.get('intern_type')
            
            # Validate ID number
            if len(id_number) != 13 or not id_number.isdigit():
                flash('ID number must be exactly 13 digits.', 'danger')
                return redirect(url_for('admin.create_user'))
            
            # Check if ID already exists
            existing = User.query.filter_by(id_number=id_number).first()
            if existing:
                flash('Intern with this ID number already exists.', 'danger')
                return redirect(url_for('admin.create_user'))
            
            user = User(
                id_number=id_number,
                intern_type=intern_type,
                role='intern',
                first_login=True,
                is_profile_complete=False,
                created_by=current_user.id
            )
            user.set_password('JubaFuture2025')
            
        else:
            # Create admin or staff
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            
            # Check if email already exists
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('User with this email already exists.', 'danger')
                return redirect(url_for('admin.create_user'))
            
            user = User(
                email=email,
                name=name,
                role=role,
                is_profile_complete=True,
                first_login=False,
                created_by=current_user.id
            )
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'{role.capitalize()} created successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/create_user.html')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.surname = request.form.get('surname')
        user.email = request.form.get('email') if user.role != 'intern' else user.email
        user.phone = request.form.get('phone')
        
        if user.role == 'intern':
            user.intern_type = request.form.get('intern_type')
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/edit_user.html', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user with reason"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason')
    
    if not reason:
        flash('Deletion reason is required.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Save user details before deletion
    user_details = user.to_dict()
    
    # Mark as deleted
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()
    
    # Save deletion history
    save_deletion_history(
        deleted_by=current_user.id,
        item_type='user',
        item_id=user.id,
        reason=reason,
        item_details=user_details,
        is_permanent=True
    )
    
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/deletion-history')
@login_required
@admin_required
def deletion_history():
    """View deletion history"""
    history = DeletionHistory.query.order_by(DeletionHistory.deletion_date.desc()).all()
    return render_template('admin/deletion_history.html', history=history)

@bp.route('/pending-deletions')
@login_required
@admin_required
def pending_deletions():
    """View pending deletion approvals"""
    pending = SoftDelete.query.filter_by(approved=False).order_by(SoftDelete.deleted_at.desc()).all()
    
    # Get associated items
    pending_items = []
    for item in pending:
        if item.item_type == 'timesheet':
            timesheet = Timesheet.query.get(item.item_id)
            if timesheet:
                pending_items.append({
                    'soft_delete': item,
                    'item': timesheet,
                    'type': 'timesheet'
                })
    
    return render_template('admin/pending_deletions.html', pending_items=pending_items)

@bp.route('/pending-deletions/<int:soft_delete_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_deletion(soft_delete_id):
    """Approve permanent deletion"""
    soft_delete = SoftDelete.query.get_or_404(soft_delete_id)
    
    if soft_delete.item_type == 'timesheet':
        timesheet = Timesheet.query.get(soft_delete.item_id)
        if timesheet:
            # Save to deletion history
            save_deletion_history(
                deleted_by=soft_delete.deleted_by,
                item_type='timesheet',
                item_id=timesheet.id,
                reason=soft_delete.deletion_reason,
                item_details=timesheet.to_dict(),
                is_permanent=True
            )
            
            # Permanently delete
            db.session.delete(timesheet)
    
    # Mark as approved
    soft_delete.approved = True
    soft_delete.approved_by = current_user.id
    soft_delete.approved_at = datetime.utcnow()
    
    db.session.commit()
    flash('Deletion approved and item permanently deleted.', 'success')
    return redirect(url_for('admin.pending_deletions'))

@bp.route('/pending-deletions/<int:soft_delete_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_deletion(soft_delete_id):
    """Reject deletion request"""
    soft_delete = SoftDelete.query.get_or_404(soft_delete_id)
    
    if soft_delete.item_type == 'timesheet':
        timesheet = Timesheet.query.get(soft_delete.item_id)
        if timesheet:
            # Restore item
            timesheet.is_deleted = False
            timesheet.deleted_at = None
            timesheet.pending_permanent_delete = False
    
    # Remove soft delete request
    db.session.delete(soft_delete)
    db.session.commit()
    
    flash('Deletion request rejected and item restored.', 'success')
    return redirect(url_for('admin.pending_deletions'))
