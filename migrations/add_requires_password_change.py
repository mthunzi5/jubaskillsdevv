"""
Migration script to add requires_password_change column to users table
Run this script once to update your database
"""
import sqlite3
import os

# Get database path
db_path = os.path.join('instance', 'juba_lms.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'requires_password_change' in columns:
        print("Column 'requires_password_change' already exists. Skipping migration.")
    else:
        # Add the new column
        cursor.execute("ALTER TABLE users ADD COLUMN requires_password_change BOOLEAN DEFAULT 0")
        conn.commit()
        print("✓ Successfully added 'requires_password_change' column to users table")
    
    conn.close()
    print("Migration completed successfully!")
    
except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")
