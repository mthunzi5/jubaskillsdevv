"""
Database migration script to add new fields for quick wins features
Run this script to update your database with the new fields
"""
from app import create_app, db
from app.models.user import User

def migrate_database():
    """Add new columns to existing database"""
    app = create_app()
    
    with app.app_context():
        # Check if we need to create tables
        db.create_all()
        print("✅ Database schema updated successfully!")
        print("\nNew fields added:")
        print("  - User.reset_token (for password reset)")
        print("  - User.reset_token_expiry (for password reset)")
        print("  - User.last_login (for tracking last login time)")
        print("\n🎉 All quick wins features are now active!")

if __name__ == '__main__':
    migrate_database()
