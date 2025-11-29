# Quick Start Guide - Juba Skills LMS

## Getting Started (5 Minutes)

### 1. Navigate to the Application
Open your browser and go to: **http://localhost:5000**

### 2. Login as Admin
Use these default credentials:
- **Email**: `admin@juba.ac.za`
- **Password**: `Admin@2025`

⚠️ **IMPORTANT**: Change this password immediately after first login!

### 3. Create Your First Users

#### Add an Intern:
1. Click "Users" in the sidebar
2. Click "Add User" button
3. Select "Intern" as role
4. Enter 13-digit ID number (e.g., `9801015800089`)
5. Select intern type: Varsity or TVET
6. Click "Create User"
7. Intern can now login with their ID number and password: `JubaFuture2025`

#### Add Staff Member:
1. Click "Users" in the sidebar
2. Click "Add User" button
3. Select "Staff" as role
4. Enter email, name, and password
5. Click "Create User"

### 4. Intern First Login
When an intern logs in for the first time:
1. They'll be prompted to complete their profile
2. Must enter: Name, Surname, Email, Phone
3. Can optionally change their password
4. After completion, they can submit timesheets

### 5. Submit a Timesheet (as Intern)
1. Login as intern
2. Click "Submit Timesheet" from dashboard or sidebar
3. Choose a PDF file (max 16MB)
4. Click "Submit Timesheet"
5. Timesheet is now visible to staff

### 6. View Timesheets (as Staff)
1. Login as staff member
2. Click "Timesheets" in sidebar
3. Filter by month or intern type
4. Download individual files or bulk download as ZIP

## Common Tasks

### Deleting a User (Admin)
1. Go to "Users"
2. Click trash icon next to user
3. **Must provide a reason** for deletion
4. User is immediately deleted
5. Deletion is recorded in history

### Deleting a Timesheet (Intern)
1. Go to "My Timesheets"
2. Click "Delete" button
3. **Must provide a reason**
4. Timesheet is hidden from intern's view
5. Admin must approve for permanent deletion

### Approving Deletions (Admin)
1. Click "Pending Approvals" in sidebar
2. Review deletion request and reason
3. Either:
   - Approve: Permanently deletes the item
   - Reject: Restores the item

### Viewing Deletion History (Admin)
1. Click "Deletion History" in sidebar
2. See all deletions with:
   - Who deleted it
   - What was deleted
   - When it was deleted
   - Reason for deletion
   - Whether it was permanent or soft delete

## User Roles Summary

| Feature | Admin | Staff | Intern |
|---------|-------|-------|--------|
| Create users | ✅ | ❌ | ❌ |
| View all users | ✅ | ❌ | ❌ |
| Delete users | ✅ | ❌ | ❌ |
| View all timesheets | ❌ | ✅ | Own only |
| Download timesheets | ❌ | ✅ | ❌ |
| Submit timesheets | ❌ | ❌ | ✅ |
| Approve deletions | ✅ | ❌ | ❌ |
| View deletion history | ✅ | ❌ | ❌ |

## Login Credentials

### Admin (Default)
- Email: `admin@juba.ac.za`
- Password: `Admin@2025`

### Staff (Created by admin)
- Email: As specified by admin
- Password: As specified by admin

### Intern (Created by admin)
- Login: 13-digit ID number
- Password: `JubaFuture2025` (can be changed after first login)

## Stopping the Server
Press `CTRL+C` in the terminal where the server is running.

## Restarting the Server
```powershell
C:/Users/Mthunzi/jubalmss/.venv/Scripts/python.exe run.py
```

## Troubleshooting

### Can't Login
- Verify you're using the correct credentials
- Interns: Use ID number (not email)
- Check caps lock is off

### File Upload Fails
- Ensure file is PDF format
- File must be under 16MB
- Check file isn't corrupted

### Port 5000 Already in Use
Edit `run.py` and change the port number in the last line.

## Need Help?
- Check the full README.md for detailed documentation
- Contact system administrator
- Review deletion history for troubleshooting

---
**Pro Tip**: Always provide clear, descriptive reasons when deleting items - this helps with auditing and future reference!
