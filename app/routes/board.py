import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.communication import CommunicationPost, PostAttachment
from app.utils.decorators import admin_required, staff_required

bp = Blueprint('board', __name__, url_prefix='/board')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext in {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}:
        return 'document'
    return 'other'

@bp.route('/')
@login_required
def board():
    """Main communication board view"""
    post_type_filter = request.args.get('type', 'all')
    
    query = CommunicationPost.query.filter_by(is_deleted=False)
    
    if post_type_filter != 'all':
        query = query.filter_by(post_type=post_type_filter)
    
    # Pinned posts first, then by created_at descending
    posts = query.order_by(CommunicationPost.is_pinned.desc(), CommunicationPost.created_at.desc()).all()
    
    return render_template('board/board.html', posts=posts, post_type_filter=post_type_filter)

@bp.route('/create', methods=['POST'])
@login_required
def create_post():
    """Create a new post"""
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    post_type = request.form.get('post_type', 'general')
    external_link = request.form.get('external_link', '').strip()
    
    if not title or not content:
        flash('Title and content are required.', 'danger')
        return redirect(url_for('board.board'))
    
    # Create post
    post = CommunicationPost(
        title=title,
        content=content,
        post_type=post_type,
        external_link=external_link if external_link else None,
        author_id=current_user.id
    )
    
    db.session.add(post)
    db.session.flush()  # Get post.id for attachments
    
    # Handle file uploads
    if 'attachments' in request.files:
        files = request.files.getlist('attachments')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                
                # Create upload directory if it doesn't exist
                upload_dir = os.path.join(current_app.root_path, 'static', 'board_attachments')
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                
                # Save attachment record
                attachment = PostAttachment(
                    post_id=post.id,
                    file_name=filename,
                    file_path=f'/static/board_attachments/{unique_filename}',
                    file_type=get_file_type(filename),
                    file_size=os.path.getsize(file_path)
                )
                db.session.add(attachment)
    
    db.session.commit()
    flash('Post created successfully!', 'success')
    return redirect(url_for('board.board'))

@bp.route('/edit/<int:post_id>', methods=['POST'])
@login_required
def edit_post(post_id):
    """Edit a post (only within 5 minutes)"""
    post = CommunicationPost.query.get_or_404(post_id)
    
    # Check permissions
    if post.author_id != current_user.id:
        flash('You can only edit your own posts.', 'danger')
        return redirect(url_for('board.board'))
    
    if not post.can_edit():
        flash('This post can no longer be edited (5-minute window expired).', 'warning')
        return redirect(url_for('board.board'))
    
    # Update post
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    external_link = request.form.get('external_link', '').strip()
    
    if not title or not content:
        flash('Title and content are required.', 'danger')
        return redirect(url_for('board.board'))
    
    post.title = title
    post.content = content
    post.external_link = external_link if external_link else None
    post.updated_at = datetime.utcnow()
    
    # Handle new file uploads
    if 'attachments' in request.files:
        files = request.files.getlist('attachments')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                
                upload_dir = os.path.join(current_app.root_path, 'static', 'board_attachments')
                os.makedirs(upload_dir, exist_ok=True)
                
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                
                attachment = PostAttachment(
                    post_id=post.id,
                    file_name=filename,
                    file_path=f'/static/board_attachments/{unique_filename}',
                    file_type=get_file_type(filename),
                    file_size=os.path.getsize(file_path)
                )
                db.session.add(attachment)
    
    db.session.commit()
    flash('Post updated successfully!', 'success')
    return redirect(url_for('board.board'))

@bp.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    """Delete a post (only within 5 minutes by author, or by admin anytime)"""
    post = CommunicationPost.query.get_or_404(post_id)
    
    # Check permissions
    is_author = post.author_id == current_user.id
    is_admin = current_user.role == 'admin'
    
    if not is_admin and not is_author:
        flash('You can only delete your own posts.', 'danger')
        return redirect(url_for('board.board'))
    
    if not is_admin and not post.can_edit():
        flash('This post can no longer be deleted (5-minute window expired).', 'warning')
        return redirect(url_for('board.board'))
    
    # Soft delete
    post.is_deleted = True
    post.deleted_at = datetime.utcnow()
    post.deleted_by_id = current_user.id
    
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('board.board'))

@bp.route('/pin/<int:post_id>', methods=['POST'])
@login_required
@admin_required
def pin_post(post_id):
    """Pin/unpin a post (admin only)"""
    post = CommunicationPost.query.get_or_404(post_id)
    
    if post.is_pinned:
        post.is_pinned = False
        post.pinned_by_id = None
        post.pinned_at = None
        flash('Post unpinned.', 'info')
    else:
        post.is_pinned = True
        post.pinned_by_id = current_user.id
        post.pinned_at = datetime.utcnow()
        flash('Post pinned to top.', 'success')
    
    db.session.commit()
    return redirect(url_for('board.board'))

@bp.route('/attachment/delete/<int:attachment_id>', methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    """Delete an attachment (only within 5 minutes)"""
    attachment = PostAttachment.query.get_or_404(attachment_id)
    post = attachment.post
    
    # Check permissions
    if post.author_id != current_user.id:
        flash('You can only delete attachments from your own posts.', 'danger')
        return redirect(url_for('board.board'))
    
    if not post.can_edit():
        flash('Attachments can no longer be deleted (5-minute window expired).', 'warning')
        return redirect(url_for('board.board'))
    
    # Delete file from filesystem
    try:
        file_path = os.path.join(current_app.root_path, 'static', 'board_attachments', 
                                 os.path.basename(attachment.file_path))
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {e}")
    
    # Delete database record
    db.session.delete(attachment)
    db.session.commit()
    
    flash('Attachment deleted.', 'success')
    return redirect(url_for('board.board'))

@bp.route('/download/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    """Download an attachment"""
    attachment = PostAttachment.query.get_or_404(attachment_id)
    
    file_path = os.path.join(current_app.root_path, 'static', 'board_attachments',
                             os.path.basename(attachment.file_path))
    
    if not os.path.exists(file_path):
        flash('File not found.', 'danger')
        return redirect(url_for('board.board'))
    
    return send_file(file_path, as_attachment=True, download_name=attachment.file_name)
