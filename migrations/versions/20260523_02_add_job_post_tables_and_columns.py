"""add job post tables and application columns

Revision ID: 20260523_02
Revises: 20260523_01
Create Date: 2026-05-23 11:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20260523_02'
down_revision = '20260523_01'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('job_posts'):
        op.create_table(
            'job_posts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('image_path', sa.String(length=500), nullable=True),
            sa.Column('is_open', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('application_deadline', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('closed_at', sa.DateTime(), nullable=True),
            sa.Column('archived_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    if not inspector.has_table('job_post_required_documents'):
        op.create_table(
            'job_post_required_documents',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('job_post_id', sa.Integer(), nullable=False),
            sa.Column('document_code', sa.String(length=50), nullable=False),
            sa.Column('label', sa.String(length=150), nullable=False),
            sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('help_text', sa.String(length=255), nullable=True),
            sa.Column('allowed_extensions', sa.String(length=100), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['job_post_id'], ['job_posts.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('job_post_id', 'document_code', name='uq_job_post_document_code')
        )

    if not inspector.has_table('job_application_settings'):
        op.create_table(
            'job_application_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('applications_open', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    columns = {col['name'] for col in inspector.get_columns('job_applications')} if inspector.has_table('job_applications') else set()
    if 'job_post_id' not in columns:
        op.add_column('job_applications', sa.Column('job_post_id', sa.Integer(), nullable=True))
    if 'applicant_image_path' not in columns:
        op.add_column('job_applications', sa.Column('applicant_image_path', sa.String(length=500), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('job_applications'):
        columns = {col['name'] for col in inspector.get_columns('job_applications')}
        if 'applicant_image_path' in columns:
            op.drop_column('job_applications', 'applicant_image_path')
        if 'job_post_id' in columns:
            op.drop_column('job_applications', 'job_post_id')

    if inspector.has_table('job_application_settings'):
        op.drop_table('job_application_settings')

    if inspector.has_table('job_post_required_documents'):
        op.drop_table('job_post_required_documents')

    if inspector.has_table('job_posts'):
        op.drop_table('job_posts')
