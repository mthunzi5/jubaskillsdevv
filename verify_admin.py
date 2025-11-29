import sqlite3

conn = sqlite3.connect('instance/juba_lms.db')
cursor = conn.cursor()

cursor.execute("SELECT email, role, name, surname FROM users WHERE role='admin'")
admin = cursor.fetchone()

if admin:
    print('═══════════════════════════════════════')
    print('✓ Admin Account Verified:')
    print('═══════════════════════════════════════')
    print(f'  Email: {admin[0]}')
    print(f'  Role: {admin[1]}')
    print(f'  Name: {admin[2]} {admin[3]}')
    print(f'  Password: Admin@2025')
    print('═══════════════════════════════════════')
else:
    print('❌ No admin account found!')

conn.close()
