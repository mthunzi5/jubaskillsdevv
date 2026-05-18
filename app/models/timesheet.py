from datetime import datetime
from app import db

class Timesheet(db.Model):
    """Timesheet model for intern submissions"""
    __tablename__ = 'timesheets'
    
    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    
    # Month organization
    submission_month = db.Column(db.String(7), nullable=False)  # Format: YYYY-MM
    submission_year = db.Column(db.Integer, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Host company submission tracking
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # host user who submitted
    host_company_id = db.Column(db.Integer, db.ForeignKey('host_companies.id'), nullable=True)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Permanent delete approval
    pending_permanent_delete = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - intern relationship is defined in User model with backref
    deleter = db.relationship('User', foreign_keys=[deleted_by])
    cohort = db.relationship('Cohort', backref='timesheets')
    submitter = db.relationship('User', foreign_keys=[submitted_by], backref='submitted_timesheets')
    host_company = db.relationship('HostCompany', backref='timesheets')
    
    def to_dict(self):
        """Convert timesheet to dictionary"""
        return {
            'id': self.id,
            'intern_id': self.intern_id,
            'intern_name': f"{self.intern.name} {self.intern.surname}" if self.intern else "Unknown",
            'intern_type': self.intern.intern_type if self.intern else None,
            'cohort_id': self.cohort_id,
            'cohort_name': self.cohort.name if self.cohort else None,
            'host_company_id': self.host_company_id,
            'host_company_name': self.host_company.company_name if self.host_company else None,
            'filename': self.original_filename,
            'file_size': self.file_size,
            'submission_month': self.submission_month,
            'submission_date': self.submission_date.isoformat() if self.submission_date else None,
            'is_deleted': self.is_deleted,
            'pending_permanent_delete': self.pending_permanent_delete
        }
    
    def __repr__(self):
        return f'<Timesheet {self.id} - {self.original_filename}>'


class TimesheetTemplate(db.Model):
    """Admin-managed template that learners/hosts can download for monthly submissions."""
    __tablename__ = 'timesheet_templates'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship('User', backref='uploaded_timesheet_templates', foreign_keys=[created_by])

    def __repr__(self):
        return f'<TimesheetTemplate {self.id} - {self.original_filename}>'


class TimesheetPolicySettings(db.Model):
    """Admin-governed rules controlling which timesheet months can be submitted."""
    __tablename__ = 'timesheet_policy_settings'

    id = db.Column(db.Integer, primary_key=True)
    block_future_months = db.Column(db.Boolean, default=False, nullable=False)
    lock_before_month = db.Column(db.String(7), nullable=True)  # Optional YYYY-MM lower boundary
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    updater = db.relationship('User', backref='updated_timesheet_policy_settings', foreign_keys=[updated_by])

    @staticmethod
    def get_settings():
        settings = TimesheetPolicySettings.query.first()
        if not settings:
            settings = TimesheetPolicySettings(block_future_months=False, lock_before_month=None)
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self):
        return f'<TimesheetPolicySettings future={self.block_future_months} lock_before={self.lock_before_month}>'


class TimesheetNonWorkingMonth(db.Model):
    """Tracks interns marked as not working for a host/cohort/month with reason."""
    __tablename__ = 'timesheet_non_working_months'

    id = db.Column(db.Integer, primary_key=True)
    host_company_id = db.Column(db.Integer, db.ForeignKey('host_companies.id'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submission_month = db.Column(db.String(7), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    host_company = db.relationship('HostCompany', backref='non_working_months')
    cohort = db.relationship('Cohort', backref='non_working_months')
    intern = db.relationship('User', foreign_keys=[intern_id], backref='non_working_months')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_non_working_months')

    __table_args__ = (
        db.UniqueConstraint('host_company_id', 'cohort_id', 'intern_id', 'submission_month', name='uq_non_working_month'),
    )

    def __repr__(self):
        return f'<TimesheetNonWorkingMonth host={self.host_company_id} intern={self.intern_id} month={self.submission_month}>'


class HostInternMonthlyFeedback(db.Model):
    """Monthly host feedback scores/comments per intern, visible to staff."""
    __tablename__ = 'host_intern_monthly_feedback'

    id = db.Column(db.Integer, primary_key=True)
    host_company_id = db.Column(db.Integer, db.ForeignKey('host_companies.id'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submission_month = db.Column(db.String(7), nullable=False)

    attendance_rating = db.Column(db.Integer, nullable=True)
    punctuality_rating = db.Column(db.Integer, nullable=True)
    communication_rating = db.Column(db.Integer, nullable=True)
    task_quality_rating = db.Column(db.Integer, nullable=True)
    comments = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    host_company = db.relationship('HostCompany', backref='monthly_feedback')
    cohort = db.relationship('Cohort', backref='monthly_feedback')
    intern = db.relationship('User', foreign_keys=[intern_id], backref='monthly_host_feedback')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_monthly_host_feedback')

    __table_args__ = (
        db.UniqueConstraint('host_company_id', 'cohort_id', 'intern_id', 'submission_month', name='uq_host_feedback_month'),
    )

    def __repr__(self):
        return f'<HostInternMonthlyFeedback host={self.host_company_id} intern={self.intern_id} month={self.submission_month}>'
