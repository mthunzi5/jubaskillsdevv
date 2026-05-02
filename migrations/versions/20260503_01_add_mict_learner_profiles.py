"""add mict learner profiles table

Revision ID: 20260503_01
Revises:
Create Date: 2026-05-03 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260503_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('mict_learner_profiles'):
        op.create_table(
            'mict_learner_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('id_number', sa.String(length=20), nullable=False),
            sa.Column('first_name', sa.String(length=100), nullable=True),
            sa.Column('last_name', sa.String(length=100), nullable=True),
            sa.Column('personal_email', sa.String(length=150), nullable=True),
            sa.Column('physical_address_line1', sa.String(length=200), nullable=True),
            sa.Column('physical_address_line2', sa.String(length=200), nullable=True),
            sa.Column('physical_address_line3', sa.String(length=200), nullable=True),
            sa.Column('physical_postal_code', sa.String(length=20), nullable=True),
            sa.Column('postal_address_line1', sa.String(length=200), nullable=True),
            sa.Column('postal_address_line2', sa.String(length=200), nullable=True),
            sa.Column('postal_address_line3', sa.String(length=200), nullable=True),
            sa.Column('postal_postal_code', sa.String(length=20), nullable=True),
            sa.Column('area_type', sa.String(length=50), nullable=True),
            sa.Column('contact_email', sa.String(length=150), nullable=True),
            sa.Column('telephone_number', sa.String(length=20), nullable=True),
            sa.Column('cellphone_number', sa.String(length=20), nullable=True),
            sa.Column('guardian_first_name', sa.String(length=100), nullable=True),
            sa.Column('guardian_last_name', sa.String(length=100), nullable=True),
            sa.Column('guardian_id_type', sa.String(length=50), nullable=True),
            sa.Column('guardian_id_number', sa.String(length=30), nullable=True),
            sa.Column('guardian_telephone', sa.String(length=20), nullable=True),
            sa.Column('guardian_cellphone', sa.String(length=20), nullable=True),
            sa.Column('guardian_home_address', sa.Text(), nullable=True),
            sa.Column('guardian_postal_address', sa.Text(), nullable=True),
            sa.Column('guardian_email', sa.String(length=150), nullable=True),
            sa.Column('highest_nqf_level', sa.String(length=10), nullable=True),
            sa.Column('nqf_other', sa.String(length=200), nullable=True),
            sa.Column('qualification_title', sa.String(length=300), nullable=True),
            sa.Column('has_matriculated', sa.String(length=10), nullable=True),
            sa.Column('matriculated_in_sa', sa.String(length=10), nullable=True),
            sa.Column('matric_province', sa.String(length=100), nullable=True),
            sa.Column('matric_high_school', sa.String(length=200), nullable=True),
            sa.Column('institution_type', sa.String(length=100), nullable=True),
            sa.Column('institution_name', sa.String(length=200), nullable=True),
            sa.Column('submitted_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('submission_count', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('id_number')
        )

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('mict_learner_profiles')}
    index_name = op.f('ix_mict_learner_profiles_id_number')
    if index_name not in existing_indexes:
        op.create_index(index_name, 'mict_learner_profiles', ['id_number'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('mict_learner_profiles'):
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('mict_learner_profiles')}
        index_name = op.f('ix_mict_learner_profiles_id_number')
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name='mict_learner_profiles')
        op.drop_table('mict_learner_profiles')
