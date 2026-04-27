from datetime import datetime
from app import db


class InternGroup(db.Model):
    """Logical grouping of interns/learners."""
    __tablename__ = 'intern_groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    education_type = db.Column(db.String(20), nullable=False, default='mixed')  # varsity, tvet, mixed
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cohorts = db.relationship('Cohort', backref='group', lazy='dynamic')
    creator = db.relationship('User', backref='created_intern_groups', foreign_keys=[created_by])

    def __repr__(self):
        return f'<InternGroup {self.name}>'


class Cohort(db.Model):
    """A cohort belongs to an intern group and has many intern members."""
    __tablename__ = 'cohorts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('intern_groups.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, completed, archived
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('CohortMember', backref='cohort', lazy='dynamic', cascade='all, delete-orphan')
    placements = db.relationship('InternPlacement', backref='cohort', lazy='dynamic')
    creator = db.relationship('User', backref='created_cohorts', foreign_keys=[created_by])

    __table_args__ = (
        db.UniqueConstraint('name', 'group_id', name='uq_cohort_name_group'),
    )

    def __repr__(self):
        return f'<Cohort {self.name}>'


class CohortMember(db.Model):
    """Links an intern user to a cohort."""
    __tablename__ = 'cohort_members'

    id = db.Column(db.Integer, primary_key=True)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=False)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    intern = db.relationship('User', foreign_keys=[intern_id], backref='cohort_memberships')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_cohort_memberships')

    __table_args__ = (
        db.UniqueConstraint('cohort_id', 'intern_id', name='uq_cohort_member'),
    )

    def __repr__(self):
        return f'<CohortMember cohort={self.cohort_id} intern={self.intern_id}>'


class HostCompany(db.Model):
    """Host companies where interns are placed."""
    __tablename__ = 'host_companies'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False, unique=True)
    contact_person = db.Column(db.String(120), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)

    login_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    login_user = db.relationship('User', foreign_keys=[login_user_id], backref='host_company_profile')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_host_companies')
    placements = db.relationship('InternPlacement', backref='host_company', lazy='dynamic')

    def __repr__(self):
        return f'<HostCompany {self.company_name}>'


class InternPlacement(db.Model):
    """Current or historical placement of an intern to a host company."""
    __tablename__ = 'intern_placements'

    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    host_company_id = db.Column(db.Integer, db.ForeignKey('host_companies.id'), nullable=False)
    cohort_id = db.Column(db.Integer, db.ForeignKey('cohorts.id'), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    intern = db.relationship('User', foreign_keys=[intern_id], backref='host_placements')
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='assigned_intern_placements')

    def __repr__(self):
        return f'<InternPlacement intern={self.intern_id} host={self.host_company_id} active={self.is_active}>'
