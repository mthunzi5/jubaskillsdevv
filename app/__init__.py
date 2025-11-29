import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
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
    from app.routes import auth, admin, staff, intern, main, lms, board
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(staff.bp)
    app.register_blueprint(intern.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(lms.lms_bp)
    app.register_blueprint(board.bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
        # Create default admin if none exists
        from app.utils.helpers import create_default_admin
        create_default_admin()
    
    return app
