from datetime import datetime
from app import db


INDUCTION_DOC_FIELDS = {
    'id_copy': {
        'label': 'ID Copy',
        'path_attr': 'id_copy_path',
        'name_attr': 'id_copy_filename',
        'size_attr': 'id_copy_size',
        'uploaded_attr': 'id_copy_uploaded_at',
    },
    'qualification': {
        'label': 'Certificate / Qualification',
        'path_attr': 'qualification_path',
        'name_attr': 'qualification_filename',
        'size_attr': 'qualification_size',
        'uploaded_attr': 'qualification_uploaded_at',
    },
    'affidavit': {
        'label': 'Affidavit',
        'path_attr': 'affidavit_path',
        'name_attr': 'affidavit_filename',
        'size_attr': 'affidavit_size',
        'uploaded_attr': 'affidavit_uploaded_at',
    },
    'additional_1': {
        'label': 'Additional 1',
        'path_attr': 'additional_1_path',
        'name_attr': 'additional_1_filename',
        'size_attr': 'additional_1_size',
        'uploaded_attr': 'additional_1_uploaded_at',
    },
    'additional_2': {
        'label': 'Additional 2',
        'path_attr': 'additional_2_path',
        'name_attr': 'additional_2_filename',
        'size_attr': 'additional_2_size',
        'uploaded_attr': 'additional_2_uploaded_at',
    },
}


class InductionSubmission(db.Model):
    """Stores required induction documents submitted by an intern."""
    __tablename__ = 'induction_submissions'

    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=True, index=True)

    # Lock/submission state
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    is_submitted = db.Column(db.Boolean, default=False, nullable=False)
    locked_at = db.Column(db.DateTime, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)

    id_copy_path = db.Column(db.String(500), nullable=True)
    id_copy_filename = db.Column(db.String(255), nullable=True)
    id_copy_size = db.Column(db.Integer, nullable=True)
    id_copy_uploaded_at = db.Column(db.DateTime, nullable=True)

    qualification_path = db.Column(db.String(500), nullable=True)
    qualification_filename = db.Column(db.String(255), nullable=True)
    qualification_size = db.Column(db.Integer, nullable=True)
    qualification_uploaded_at = db.Column(db.DateTime, nullable=True)

    affidavit_path = db.Column(db.String(500), nullable=True)
    affidavit_filename = db.Column(db.String(255), nullable=True)
    affidavit_size = db.Column(db.Integer, nullable=True)
    affidavit_uploaded_at = db.Column(db.DateTime, nullable=True)

    additional_1_path = db.Column(db.String(500), nullable=True)
    additional_1_filename = db.Column(db.String(255), nullable=True)
    additional_1_size = db.Column(db.Integer, nullable=True)
    additional_1_uploaded_at = db.Column(db.DateTime, nullable=True)

    additional_2_path = db.Column(db.String(500), nullable=True)
    additional_2_filename = db.Column(db.String(255), nullable=True)
    additional_2_size = db.Column(db.Integer, nullable=True)
    additional_2_uploaded_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    intern = db.relationship('User', backref=db.backref('induction_submission', uselist=False))
    cohort = db.relationship('Cohort', backref=db.backref('induction_submissions', cascade='all'))

    def has_document(self, doc_key):
        if doc_key not in INDUCTION_DOC_FIELDS:
            return False
        path_attr = INDUCTION_DOC_FIELDS[doc_key]['path_attr']
        return bool(getattr(self, path_attr))

    def missing_documents(self):
        missing = []
        for key, meta in INDUCTION_DOC_FIELDS.items():
            if not self.has_document(key):
                missing.append(meta['label'])
        return missing

    def is_complete(self):
        return len(self.missing_documents()) == 0

    def __repr__(self):
        return f'<InductionSubmission intern_id={self.intern_id}>'


class InductionPortalSettings(db.Model):
    """Global induction portal open/close state."""
    __tablename__ = 'induction_portal_settings'

    id = db.Column(db.Integer, primary_key=True)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings record."""
        settings = cls.query.first()
        if not settings:
            settings = cls(is_open=True)
            db.session.add(settings)
            db.session.commit()
        return settings

    def toggle_open_close(self):
        """Toggle the portal open/closed state and update timestamps."""
        self.is_open = not self.is_open
        if self.is_open:
            self.opened_at = datetime.utcnow()
            self.closed_at = None
        else:
            self.closed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<InductionPortalSettings is_open={self.is_open}>'


class InductionExportAuditLog(db.Model):
    """Audit trail for induction document ZIP exports."""
    __tablename__ = 'induction_export_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    export_type = db.Column(db.String(50), nullable=False)  # doc_key like 'id_copy', 'qualification', etc.
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=True, index=True)
    file_count = db.Column(db.Integer, default=0, nullable=False)
    exported_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship('User', backref=db.backref('induction_export_audits'))
    cohort = db.relationship('Cohort', backref=db.backref('induction_export_audits'))

    def __repr__(self):
        return f'<InductionExportAuditLog user_id={self.user_id} export_type={self.export_type} file_count={self.file_count}>'