from datetime import datetime, timedelta
from app import db

class CommunicationPost(db.Model):
    __tablename__ = 'communication_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(50), default='general')  # general, reminder, announcement
    
    # Author info
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('User', foreign_keys=[author_id], backref=db.backref('posts', lazy='dynamic'))
    
    # Links
    external_link = db.Column(db.String(500))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Pinning
    is_pinned = db.Column(db.Boolean, default=False)
    pinned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    pinned_by = db.relationship('User', foreign_keys=[pinned_by_id])
    pinned_at = db.Column(db.DateTime)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    deleted_by = db.relationship('User', foreign_keys=[deleted_by_id])
    
    # Relationships
    attachments = db.relationship('PostAttachment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    def can_edit(self):
        """Check if post can still be edited (within 5 minutes)"""
        if self.is_deleted:
            return False
        time_elapsed = datetime.utcnow() - self.created_at
        return time_elapsed < timedelta(minutes=5)
    
    def time_remaining_to_edit(self):
        """Get remaining time to edit in seconds"""
        if not self.can_edit():
            return 0
        time_elapsed = datetime.utcnow() - self.created_at
        five_minutes = timedelta(minutes=5)
        remaining = five_minutes - time_elapsed
        return max(0, int(remaining.total_seconds()))
    
    def __repr__(self):
        return f'<CommunicationPost {self.title}>'


class PostAttachment(db.Model):
    __tablename__ = 'post_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('communication_posts.id'), nullable=False)
    
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # document, image, other
    file_size = db.Column(db.Integer)  # in bytes
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_file_type_icon(self):
        """Return Bootstrap icon class based on file type"""
        if self.file_type == 'image':
            return 'bi-file-image'
        elif self.file_type == 'document':
            if self.file_name.endswith('.pdf'):
                return 'bi-file-pdf'
            elif self.file_name.endswith(('.doc', '.docx')):
                return 'bi-file-word'
            elif self.file_name.endswith(('.xls', '.xlsx')):
                return 'bi-file-excel'
            elif self.file_name.endswith(('.ppt', '.pptx')):
                return 'bi-file-ppt'
            return 'bi-file-text'
        return 'bi-file-earmark'
    
    def __repr__(self):
        return f'<PostAttachment {self.file_name}>'
