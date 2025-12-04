from app import db
from datetime import datetime

class Notification(db.Model):
    """In-app notifications for users"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notification content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # request_created, deadline_reminder, submission_reviewed
    
    # Related objects
    related_type = db.Column(db.String(50), nullable=True)  # request, submission
    related_id = db.Column(db.Integer, nullable=True)  # ID of related object
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def create_notification(user_id, title, message, notification_type, related_type=None, related_id=None):
        """Helper to create a notification"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_type=related_type,
            related_id=related_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def notify_request_created(request_obj):
        """Notify targeted users when a request is created"""
        from app.models.request_hub import Request
        
        target_users = request_obj.get_target_users()
        for user in target_users:
            Notification.create_notification(
                user_id=user.id,
                title=f"New Request: {request_obj.title}",
                message=f"A new document request has been created by {request_obj.created_by.name} {request_obj.created_by.surname}. "
                        f"{'Deadline: ' + request_obj.deadline.strftime('%d %b %Y, %H:%M') if request_obj.deadline else 'No deadline set.'}",
                notification_type='request_created',
                related_type='request',
                related_id=request_obj.id
            )
    
    @staticmethod
    def notify_submission_reviewed(submission):
        """Notify intern when their submission is reviewed"""
        status_text = "approved" if submission.status == "approved" else "rejected"
        Notification.create_notification(
            user_id=submission.user_id,
            title=f"Submission {status_text.capitalize()}",
            message=f"Your submission for '{submission.request.title}' has been {status_text} by {submission.reviewed_by.name} {submission.reviewed_by.surname}. "
                    f"{submission.review_notes if submission.review_notes else ''}",
            notification_type='submission_reviewed',
            related_type='submission',
            related_id=submission.id
        )
    
    @staticmethod
    def notify_deadline_approaching(request_obj, hours_remaining=24):
        """Notify users who haven't submitted that deadline is approaching"""
        target_users = request_obj.get_target_users()
        for user in target_users:
            # Check if user has already submitted
            if not request_obj.has_submitted(user.id):
                Notification.create_notification(
                    user_id=user.id,
                    title=f"Deadline Reminder: {request_obj.title}",
                    message=f"The deadline for '{request_obj.title}' is approaching! "
                            f"You have approximately {hours_remaining} hours remaining. "
                            f"Deadline: {request_obj.deadline.strftime('%d %b %Y, %H:%M')}",
                    notification_type='deadline_reminder',
                    related_type='request',
                    related_id=request_obj.id
                )
