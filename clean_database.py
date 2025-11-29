"""
Clean database script - removes all data except admin user
"""
import sqlite3
import os

db_path = 'instance/juba_lms.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get admin user ID
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    admin = cursor.fetchone()
    admin_id = admin[0] if admin else None
    
    print('Cleaning database...')
    print('')
    
    # Delete all data from tables (keep structure)
    tables = [
        'post_attachments',
        'communication_posts',
        'quiz_answer',
        'quiz_question',
        'task_assignment',
        'tasks_v2',
        'material_deletion_history',
        'material_deletion_request',
        'task_deletion_history',
        'task_deletion_request',
        'evaluation',
        'certificate',
        'progress',
        'task',
        'training_material',
        'timesheet',
        'deletion_history'
    ]
    
    for table in tables:
        try:
            cursor.execute(f'DELETE FROM {table}')
            count = cursor.rowcount
            print(f'✓ Cleared {table} ({count} rows)')
        except Exception as e:
            print(f'⊘ Skipped {table} (table may not exist)')
    
    # Delete non-admin users
    if admin_id:
        cursor.execute(f'DELETE FROM users WHERE id != {admin_id}')
        count = cursor.rowcount
        print(f'✓ Removed {count} non-admin users')
    else:
        print('⚠ No admin user found!')
    
    conn.commit()
    conn.close()
    print('')
    print('═══════════════════════════════════════')
    print('✓ Database cleaned successfully!')
    print('✓ Only admin account remains')
    print('═══════════════════════════════════════')
else:
    print('❌ Database not found at:', db_path)
