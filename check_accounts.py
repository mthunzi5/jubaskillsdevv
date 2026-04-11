#!/usr/bin/env python3
"""Script to check and create default accounts for testing"""

from app import create_app, db
from app.models.user import User

def main():
    app = create_app()
    with app.app_context():
        print("Checking existing accounts...")

        # Check admin
        admin = User.query.filter_by(role='admin').first()
        if admin:
            print(f"✅ Admin account exists: {admin.email}")
        else:
            print("❌ No admin account found")

        # Check staff
        staff = User.query.filter_by(role='staff').first()
        if staff:
            print(f"✅ Staff account exists: {staff.email}")
        else:
            print("📝 Creating staff account...")
            staff = User(
                email='staff@juba.ac.za',
                role='staff',
                name='Staff',
                surname='Member',
                is_profile_complete=True,
                first_login=False
            )
            staff.set_password('Staff@2025')
            db.session.add(staff)
            db.session.commit()
            print("✅ Created staff account: staff@juba.ac.za / Staff@2025")

        print("\n" + "="*50)
        print("LOGIN CREDENTIALS:")
        print("="*50)
        print("Admin: admin@juba.ac.za / Admin@2025")
        print("Staff: staff@juba.ac.za / Staff@2025")
        print("Intern default password: JUBASKILLS")
        print("="*50)

if __name__ == "__main__":
    main()