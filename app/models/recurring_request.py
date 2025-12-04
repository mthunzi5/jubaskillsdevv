from app import db
from datetime import datetime

class RecurringRequest(db.Model):
    """Template for auto-creating requests on a schedule"""
    __tablename__ = 'recurring_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Request template fields
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    request_type = db.Column(db.String(50), nullable=False)
    
    # Target audience
    target_type = db.Column(db.String(20), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Document settings
    requires_documents = db.Column(db.Boolean, default=True)
    max_documents = db.Column(db.Integer, default=5)
    requires_text = db.Column(db.Boolean, default=False)
    text_field_label = db.Column(db.String(200), nullable=True)
    
    # Recurrence settings
    recurrence_pattern = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, quarterly
    recurrence_day = db.Column(db.Integer, nullable=True)  # Day of month (1-31) for monthly
    deadline_days_after = db.Column(db.Integer, default=7)  # Deadline X days after creation
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_created_at = db.Column(db.DateTime, nullable=True)
    next_creation_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='recurring_requests')
    target_user = db.relationship('User', foreign_keys=[target_user_id])
    
    def calculate_next_creation(self):
        """Calculate when the next request should be created"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        base_date = self.last_created_at if self.last_created_at else datetime.utcnow()
        
        if self.recurrence_pattern == 'daily':
            return base_date + timedelta(days=1)
        elif self.recurrence_pattern == 'weekly':
            return base_date + timedelta(weeks=1)
        elif self.recurrence_pattern == 'monthly':
            next_date = base_date + relativedelta(months=1)
            if self.recurrence_day:
                try:
                    next_date = next_date.replace(day=self.recurrence_day)
                except ValueError:
                    # Handle months with fewer days
                    pass
            return next_date
        elif self.recurrence_pattern == 'quarterly':
            return base_date + relativedelta(months=3)
        
        return None
    
    def create_request_instance(self):
        """Create a new Request from this recurring template"""
        from app.models.request_hub import Request
        from datetime import timedelta
        
        # Calculate deadline
        deadline = datetime.utcnow() + timedelta(days=self.deadline_days_after) if self.deadline_days_after else None
        
        # Create the request
        new_request = Request(
            title=self.title,
            description=self.description,
            request_type=self.request_type,
            target_type=self.target_type,
            target_user_id=self.target_user_id,
            requires_documents=self.requires_documents,
            max_documents=self.max_documents,
            requires_text=self.requires_text,
            text_field_label=self.text_field_label,
            deadline=deadline,
            created_by_id=self.created_by_id,
            is_active=True
        )
        
        db.session.add(new_request)
        
        # Update last created and calculate next
        self.last_created_at = datetime.utcnow()
        self.next_creation_at = self.calculate_next_creation()
        
        db.session.commit()
        
        # Send notifications
        from app.models.notification import Notification
        Notification.notify_request_created(new_request)
        
        return new_request
    
    @staticmethod
    def process_due_recurring_requests():
        """Process all recurring requests that are due to be created"""
        now = datetime.utcnow()
        due_requests = RecurringRequest.query.filter(
            RecurringRequest.is_active == True,
            RecurringRequest.next_creation_at <= now
        ).all()
        
        created_count = 0
        for recurring in due_requests:
            try:
                recurring.create_request_instance()
                created_count += 1
            except Exception as e:
                print(f"Error creating recurring request {recurring.id}: {e}")
        
        return created_count
