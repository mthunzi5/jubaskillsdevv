from app import db
from datetime import datetime


class MictLearnerProfile(db.Model):
    """MICT SETA learner profile submitted via the public registration form."""
    __tablename__ = 'mict_learner_profiles'

    id = db.Column(db.Integer, primary_key=True)

    # --- Personal Information ---
    id_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    personal_email = db.Column(db.String(150), nullable=True)

    # --- Contact & Address ---
    physical_address_line1 = db.Column(db.String(200), nullable=True)
    physical_address_line2 = db.Column(db.String(200), nullable=True)
    physical_address_line3 = db.Column(db.String(200), nullable=True)
    physical_postal_code = db.Column(db.String(20), nullable=True)

    postal_address_line1 = db.Column(db.String(200), nullable=True)
    postal_address_line2 = db.Column(db.String(200), nullable=True)
    postal_address_line3 = db.Column(db.String(200), nullable=True)
    postal_postal_code = db.Column(db.String(20), nullable=True)

    area_type = db.Column(db.String(50), nullable=True)          # Urban / Rural / Peri-urban
    contact_email = db.Column(db.String(150), nullable=True)
    telephone_number = db.Column(db.String(20), nullable=True)
    cellphone_number = db.Column(db.String(20), nullable=True)

    # --- Parent / Guardian ---
    guardian_first_name = db.Column(db.String(100), nullable=True)
    guardian_last_name = db.Column(db.String(100), nullable=True)
    guardian_id_type = db.Column(db.String(50), nullable=True)   # SA ID / Passport
    guardian_id_number = db.Column(db.String(30), nullable=True)
    guardian_telephone = db.Column(db.String(20), nullable=True)
    guardian_cellphone = db.Column(db.String(20), nullable=True)
    guardian_home_address = db.Column(db.Text, nullable=True)
    guardian_postal_address = db.Column(db.Text, nullable=True)
    guardian_email = db.Column(db.String(150), nullable=True)

    # --- Education ---
    highest_nqf_level = db.Column(db.String(10), nullable=True)
    nqf_other = db.Column(db.String(200), nullable=True)
    qualification_title = db.Column(db.String(300), nullable=True)
    has_matriculated = db.Column(db.String(10), nullable=True)    # Yes / No
    matriculated_in_sa = db.Column(db.String(10), nullable=True)  # Yes / No
    matric_province = db.Column(db.String(100), nullable=True)
    matric_high_school = db.Column(db.String(200), nullable=True)
    institution_type = db.Column(db.String(100), nullable=True)
    institution_name = db.Column(db.String(200), nullable=True)

    # --- Meta ---
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submission_count = db.Column(db.Integer, default=1)          # increments on each re-submit

    def __repr__(self):
        return f'<MictLearnerProfile {self.id_number} – {self.first_name} {self.last_name}>'

    @property
    def full_name(self):
        parts = [p for p in [self.first_name, self.last_name] if p]
        return ' '.join(parts) if parts else '—'
