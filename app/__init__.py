import os
from datetime import datetime
from flask import Flask, redirect, request, url_for
from flask_login import current_user, logout_user
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
    login_manager.session_protection = 'strong'

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('auth.login', next=request.url))
    
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['INDUCTION_UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.routes import auth, admin, staff, intern, main, lms, board, request_hub, job_applications, intern_management, host_company, mict_learner
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
    app.register_blueprint(mict_learner.bp)
    
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

    @app.before_request
    def reject_deleted_or_invalid_sessions():
        if current_user.is_authenticated and getattr(current_user, 'is_deleted', False):
            logout_user()
            return redirect(url_for('auth.login'))

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        response.headers.setdefault('Pragma', 'no-cache')
        response.headers.setdefault('Expires', '0')
        return response
    
    # Create tables
    with app.app_context():
        db.create_all()

        # Backfill induction columns for existing databases where the table already exists.
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        def ensure_columns(table_name, column_statements):
            if table_name not in table_names:
                return False

            existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
            pending = [stmt for name, stmt in column_statements if name not in existing_cols]

            for stmt in pending:
                db.session.execute(text(stmt))

            return bool(pending)

        schema_changed = False

        schema_changed = ensure_columns('induction_submissions', [
            ('cohort_id', "ALTER TABLE induction_submissions ADD COLUMN cohort_id INTEGER"),
            ('is_locked', "ALTER TABLE induction_submissions ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT 0"),
            ('is_submitted', "ALTER TABLE induction_submissions ADD COLUMN is_submitted BOOLEAN NOT NULL DEFAULT 0"),
            ('locked_at', "ALTER TABLE induction_submissions ADD COLUMN locked_at DATETIME"),
            ('submitted_at', "ALTER TABLE induction_submissions ADD COLUMN submitted_at DATETIME"),
        ]) or schema_changed

        schema_changed = ensure_columns('host_companies', [
            ('login_user_id', "ALTER TABLE host_companies ADD COLUMN login_user_id INTEGER"),
        ]) or schema_changed

        schema_changed = ensure_columns('notifications', [
            ('notification_type', "ALTER TABLE notifications ADD COLUMN notification_type VARCHAR(50) DEFAULT 'request_created'"),
            ('related_type', "ALTER TABLE notifications ADD COLUMN related_type VARCHAR(50)"),
            ('related_id', "ALTER TABLE notifications ADD COLUMN related_id INTEGER"),
        ]) or schema_changed

        if schema_changed:
            db.session.commit()

        # Create default admin if none exists
        from app.utils.helpers import create_default_admin
        create_default_admin()
    
    return app
