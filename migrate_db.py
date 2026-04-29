"""
Database migration script to add new fields and tables.
Run this script to update your database with the new fields
"""
from app import create_app, db
from sqlalchemy import inspect, text

from app.models.user import User
from app.models.job_application import JobPost
from app.models.intern_management import InternGroup
from app.models.permission import RolePermission


def ensure_column(connection, table_name, column_name, column_sql):
    """Add a column if it does not exist in the target table."""
    columns = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    existing = {row[1] for row in columns}
    if column_name not in existing:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
        print(f"  - Added column {table_name}.{column_name}")

def migrate_database():
    """Apply schema updates for job posts and intern operations."""
    app = create_app()
    
    with app.app_context():
        # Ensure new tables are created.
        db.create_all()

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        with db.engine.begin() as connection:
            if 'job_applications' in table_names:
                ensure_column(connection, 'job_applications', 'job_post_id', 'job_post_id INTEGER')
                ensure_column(connection, 'job_applications', 'applicant_image_path', 'applicant_image_path VARCHAR(500)')

            if 'job_posts' in table_names:
                ensure_column(connection, 'job_posts', 'is_archived', 'is_archived BOOLEAN DEFAULT 0')
                ensure_column(connection, 'job_posts', 'archived_at', 'archived_at DATETIME')

            if 'intern_groups' in table_names:
                ensure_column(connection, 'intern_groups', 'is_active', 'is_active BOOLEAN DEFAULT 1')
                ensure_column(connection, 'intern_groups', 'archived_at', 'archived_at DATETIME')

            if 'cohorts' in table_names:
                ensure_column(connection, 'cohorts', 'is_active', 'is_active BOOLEAN DEFAULT 1')
                ensure_column(connection, 'cohorts', 'archived_at', 'archived_at DATETIME')

            if 'host_companies' in table_names:
                ensure_column(connection, 'host_companies', 'archived_at', 'archived_at DATETIME')
                ensure_column(connection, 'host_companies', 'login_user_id', 'login_user_id INTEGER')

            if 'notifications' in table_names:
                ensure_column(connection, 'notifications', 'notification_type', "notification_type VARCHAR(50) DEFAULT 'request_created'")
                ensure_column(connection, 'notifications', 'related_type', 'related_type VARCHAR(50)')
                ensure_column(connection, 'notifications', 'related_id', 'related_id INTEGER')

            if 'timesheets' in table_names:
                ensure_column(connection, 'timesheets', 'cohort_id', 'cohort_id INTEGER')
                ensure_column(connection, 'timesheets', 'submitted_by', 'submitted_by INTEGER')
                ensure_column(connection, 'timesheets', 'host_company_id', 'host_company_id INTEGER')

        print("✅ Database schema updated successfully!")
        print("\nNew/updated areas:")
        print("  - Job posts and configurable required documents")
        print("  - Intern groups, cohorts, host companies, and placements")
        print("  - Job applications linked to specific job posts")

        # Seed one default job post if there are no existing records.
        if JobPost.query.count() == 0:
            post = JobPost(
                title='General Internship Intake',
                summary='Default post created during migration.',
                description='Use staff dashboard to edit and create targeted job posts.',
                is_open=True,
            )
            db.session.add(post)
            db.session.commit()
            print("  - Seeded default job post: General Internship Intake")

        # Seed explicit defaults for matrix only if none exist.
        if RolePermission.query.count() == 0:
            print("  - Permission matrix table ready (no overrides yet; defaults apply)")

        # Normalize missing intern types and ensure fixed type groups exist.
        updated_users = User.query.filter(User.role == 'intern', User.intern_type.is_(None)).all()
        for user in updated_users:
            user.intern_type = 'mixed'

        fixed_groups = [
            ('VARSITY', 'varsity'),
            ('TVET', 'tvet'),
            ('MIXED', 'mixed'),
        ]
        for name, education_type in fixed_groups:
            group = InternGroup.query.filter_by(education_type=education_type, is_active=True).first()
            if not group:
                db.session.add(InternGroup(name=name, education_type=education_type, description=f'Fixed intern type group: {name}'))

        if updated_users:
            print(f"  - Normalized {len(updated_users)} intern record(s) to intern_type='mixed'")

        db.session.commit()

        print("\n🎉 Migration complete.")

if __name__ == '__main__':
    migrate_database()
