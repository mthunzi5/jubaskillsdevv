import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
jwt = JWTManager()
migrate = Migrate()


def _ensure_runtime_schema_compatibility():
    """Apply minimal non-destructive schema fixes for older SQLite deployments."""
    inspector = inspect(db.engine)
    patch_statements = []

    def queue_missing_columns(table_name, columns_to_add):
        if not inspector.has_table(table_name):
            return set()

        existing = {column['name'] for column in inspector.get_columns(table_name)}
        for column_name, ddl in columns_to_add.items():
            if column_name not in existing:
                patch_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")
        return existing

    user_columns = queue_missing_columns('users', {
        'is_terminated': 'BOOLEAN DEFAULT 0',
        'termination_date': 'DATETIME',
        'requires_password_change': 'BOOLEAN DEFAULT 0',
        'last_login': 'DATETIME',
        'intern_type': 'VARCHAR(20)',
        'is_profile_complete': 'BOOLEAN DEFAULT 0',
        'first_login': 'BOOLEAN DEFAULT 1',
        'created_by': 'INTEGER',
    })

    queue_missing_columns('intern_groups', {
        'education_type': "VARCHAR(20) DEFAULT 'mixed'",
        'description': 'TEXT',
        'is_active': 'BOOLEAN DEFAULT 1',
        'archived_at': 'DATETIME',
        'created_by': 'INTEGER',
        'created_at': 'DATETIME',
    })

    cohort_columns = queue_missing_columns('cohorts', {
        'group_id': 'INTEGER',
        'status': "VARCHAR(20) DEFAULT 'active'",
        'start_date': 'DATE',
        'end_date': 'DATE',
        'notes': 'TEXT',
        'is_active': 'BOOLEAN DEFAULT 1',
        'archived_at': 'DATETIME',
        'created_by': 'INTEGER',
        'created_at': 'DATETIME',
    })

    host_columns = queue_missing_columns('host_companies', {
        'company_name': 'VARCHAR(150)',
        'contact_person': 'VARCHAR(120)',
        'contact_email': 'VARCHAR(120)',
        'contact_phone': 'VARCHAR(30)',
        'address': 'VARCHAR(255)',
        'is_active': 'BOOLEAN DEFAULT 1',
        'archived_at': 'DATETIME',
        'login_user_id': 'INTEGER',
        'created_by': 'INTEGER',
        'created_at': 'DATETIME',
    })

    queue_missing_columns('cohort_members', {
        'created_at': 'DATETIME',
        'created_by': 'INTEGER',
    })

    queue_missing_columns('intern_placements', {
        'cohort_id': 'INTEGER',
        'is_active': 'BOOLEAN DEFAULT 1',
        'assigned_at': 'DATETIME',
        'ended_at': 'DATETIME',
        'assigned_by': 'INTEGER',
    })

    with db.engine.begin() as connection:
        for statement in patch_statements:
            connection.execute(text(statement))

        # Backfill legacy naming so host companies remain visible in current UI.
        if 'company_name' in host_columns and 'name' in host_columns:
            connection.execute(text("""
                UPDATE host_companies
                SET company_name = name
                WHERE (company_name IS NULL OR TRIM(company_name) = '')
                  AND name IS NOT NULL
            """))

        # Ensure existing rows are active where older schemas had no active flag.
        if 'is_active' in cohort_columns:
            connection.execute(text("""
                UPDATE cohorts
                SET is_active = 1
                WHERE is_active IS NULL
            """))
        if 'is_active' in host_columns:
            connection.execute(text("""
                UPDATE host_companies
                SET is_active = 1
                WHERE is_active IS NULL
            """))
        if 'is_terminated' in user_columns:
            connection.execute(text("""
                UPDATE users
                SET is_terminated = 0
                WHERE is_terminated IS NULL
            """))

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Add custom template filter for datetime
    @app.template_filter('datetime')
    def datetime_filter(value):
        if value == 'now':
            return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return value
    
    # Add custom template filter for line breaks
    @app.template_filter('nl2br')
    def nl2br_filter(value):
        if not value:
            return value
        return value.replace('\n', '<br>\n')
    
    # Add template context processor to make datetime.utcnow available as 'now'
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.routes import (
        auth,
        admin,
        staff,
        intern,
        main,
        lms,
        board,
        request_hub,
        job_applications,
        intern_management,
        host_company,
    )
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(staff.bp)
    app.register_blueprint(intern.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(lms.lms_bp)
    app.register_blueprint(board.bp)
    app.register_blueprint(request_hub.request_hub_bp)
    app.register_blueprint(job_applications.bp)
    app.register_blueprint(intern_management.bp)
    app.register_blueprint(host_company.bp)
    
    # Register error handlers
    from flask import render_template
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Create tables
    with app.app_context():
        db.create_all()
        _ensure_runtime_schema_compatibility()
        # Create default admin if none exists
        from app.utils.helpers import create_default_admin
        create_default_admin()
    
    return app
