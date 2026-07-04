import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _resolve_database_uri(base_dir: str) -> str:
    """Resolve DB URI with safe defaults for SQLite paths."""
    raw_uri = os.environ.get('DATABASE_URI')
    default_sqlite = 'sqlite:///' + os.path.join(base_dir, 'instance', 'juba_lms.db')

    if not raw_uri:
        return default_sqlite

    if not raw_uri.startswith('sqlite:///'):
        return raw_uri

    sqlite_path = raw_uri.replace('sqlite:///', '', 1)
    if not sqlite_path:
        return default_sqlite

    # Absolute paths in SQLite URIs start with '/' after stripping sqlite:///.
    if sqlite_path.startswith('/'):
        return raw_uri

    # Avoid accidental shadow DBs from values like sqlite:///juba_lms.db.
    if os.path.basename(sqlite_path) == sqlite_path:
        fixed_path = os.path.join(base_dir, 'instance', sqlite_path)
        return 'sqlite:///' + fixed_path

    fixed_path = os.path.join(base_dir, sqlite_path)
    return 'sqlite:///' + fixed_path

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    
    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(BASE_DIR)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'timesheets')
    JOB_APPLICATIONS_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'job_applications')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Pagination
    ITEMS_PER_PAGE = 20

    # Email (SMTP)
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'm48209921@gmail.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'm48209921@gmail.com')
    SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Juba Consultants')

    # Backward-compatible names
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
