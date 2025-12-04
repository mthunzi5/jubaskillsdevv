# Request Hub Enhancement Features

This document outlines the 5 major enhancements implemented for the Request Hub system.

## Overview
The Request Hub allows staff to create document requests and interns to submit their responses. These enhancements add automation, notifications, analytics, and better document management capabilities.

---

## 1. Bulk Download for Staff ✅

### Description
Staff can now download all submissions for a request as a single ZIP file, with documents organized by intern folders.

### Features
- **One-click download**: Single button to download all submissions
- **Organized structure**: Each intern gets their own folder in the ZIP
- **Automatic naming**: Folders named with intern names for easy identification
- **All documents included**: Includes all submitted documents from all interns

### Implementation
- Route: `/staff/request/<request_id>/download-all`
- Template: "Download All Submissions" button in `view_request.html`
- Uses Python's `zipfile` module for ZIP creation

### Usage
1. Navigate to a request as staff
2. Click "Download All Submissions" button
3. ZIP file downloads with structure: `{intern_name}/{documents...}`

---

## 2. Notification System ✅

### Description
Real-time in-app notification system that alerts users about request events.

### Features
- **Notification bell icon**: Always visible in sidebar with unread badge count
- **Real-time updates**: Badge updates every 30 seconds via AJAX
- **Notification center**: Dedicated page to view and manage all notifications
- **Filtering tabs**: View All, Unread, or Read notifications
- **Mark as read**: Individual or bulk mark all as read
- **Linked notifications**: Click to jump directly to related request

### Notification Types
1. **New Request Assigned**: Interns notified when staff creates a request for them
2. **Submission Reviewed**: Interns notified when their submission is approved/rejected

### Implementation
- Model: `Notification` with user_id, title, message, notification_type, is_read
- Routes: 
  - `/notifications` - View notification center
  - `/api/notifications/unread-count` - API endpoint for badge count
  - `/notification/<id>/mark-read` - Mark single as read
  - `/notifications/mark-all-read` - Bulk mark all as read
- Templates: 
  - `notifications.html` - Notification center
  - `base.html` - Bell icon with badge in sidebar

### Usage
1. Bell icon shows unread count badge
2. Click bell to view notification center
3. Click notification title to view related request
4. Mark individual or all as read

---

## 3. Request Statistics Dashboard ✅

### Description
Analytics dashboard showing key metrics and performance indicators for the Request Hub.

### Features
- **6 Key Metrics**:
  1. **Total Requests**: Count of all requests created
  2. **Completion Rate**: Percentage of fully completed requests
  3. **Most Popular Type**: Most frequently used request type
  4. **Average Response Time**: How long interns take to respond (in hours)
  5. **Active Requests**: Requests currently open/pending
  6. **Overdue Submissions**: Count of submissions past deadline

- **Visual Cards**: Each metric displayed in color-coded card
- **Chart Integration**: Ready for Chart.js visualizations

### Implementation
- Route: `/staff/analytics`
- Template: `analytics.html` with 6 stat cards
- Complex SQL queries for aggregations and calculations
- Uses `db.session.execute()` for raw SQL queries

### Usage
1. Navigate to Request Hub as staff
2. Click "Analytics" button
3. View dashboard with all 6 metrics

---

## 4. Recurring Requests ✅

### Description
Automated request creation system using templates with scheduling patterns.

### Features
- **Frequency Patterns**: Weekly, Monthly, or Quarterly
- **Template Storage**: Save all request details as reusable template
- **Auto-generation**: System creates new requests based on schedule
- **Active/Inactive Toggle**: Enable or disable recurring templates
- **Manual Trigger**: Create request from template immediately
- **Next Run Tracking**: Shows when next request will be created

### Implementation
- Model: `RecurringRequest` with frequency, next_run_date, template fields
- Routes:
  - `/staff/recurring` - List all recurring templates
  - `/staff/recurring/create` - Create new template
  - `/staff/recurring/<id>/toggle` - Activate/deactivate
  - `/staff/recurring/<id>/delete` - Delete template
  - `/staff/recurring/<id>/create-now` - Manual trigger
- Templates:
  - `recurring_requests.html` - Template list
  - `create_recurring.html` - Template creation form

### Usage
1. Click "Recurring Requests" from staff dashboard
2. Create new recurring template with frequency
3. System will auto-create requests based on schedule
4. Toggle active/inactive or manually trigger creation

**Note**: Requires background scheduler (cron job) to be implemented for automatic creation.

---

## 5. Submission Receipts (PDF) ✅

### Description
Professional PDF receipts generated for each submission as proof of submission.

### Features
- **Automatic Generation**: PDF created on-demand when downloaded
- **Professional Formatting**: Clean layout with tables and styling
- **Complete Information**:
  - Request details (title, type, deadline)
  - Submitter information (name, student number)
  - Submission timestamp
  - List of all uploaded documents with filenames
  - Review status and comments (if reviewed)
  - Reviewer information
- **Download Options**: 
  - Interns: "Download Receipt" button on their submission view
  - Staff: PDF icon next to each submission in staff view

### Implementation
- Utility: `app/utils/pdf_generator.py` using reportlab library
- Functions:
  - `generate_submission_receipt(submission)` - Creates PDF file
  - `download_submission_receipt(submission_id)` - Finds existing PDF
- Route: `/submission/<submission_id>/receipt` - Download endpoint
- Templates:
  - `intern_view_request.html` - Receipt button in status alert
  - `view_request.html` - PDF icon in submissions table

### Technical Details
- Uses reportlab library for PDF generation
- PDFs saved to `app/static/submission_receipts/`
- Filename pattern: `receipt_{submission_id}_{timestamp}.pdf`
- Professional styling with colors, tables, headers, footers

### Usage
**For Interns:**
1. View your submission
2. Click "Download Receipt" button in status alert
3. PDF downloads with submission proof

**For Staff:**
1. View request submissions
2. Click PDF icon next to any submission
3. Download receipt for that intern's submission

---

## Dependencies Added

```
reportlab==4.0.7        # PDF generation
python-dateutil==2.8.2  # Date calculations for recurring requests
```

---

## Database Models Created

1. **Notification**
   - `id`, `user_id`, `title`, `message`, `notification_type`
   - `is_read`, `related_request_id`, `created_at`

2. **RecurringRequest**
   - `id`, `title`, `description`, `request_type`, `frequency`
   - `target_type`, `target_id`, `requires_documents`, `requires_text`
   - `text_field_label`, `max_documents`, `deadline_days`
   - `is_active`, `next_run_date`, `last_run_date`
   - `created_by`, `created_at`

---

## Routes Added

### Notification Routes
- `GET /request-hub/notifications` - Notification center
- `POST /request-hub/notification/<id>/mark-read` - Mark as read
- `POST /request-hub/notifications/mark-all-read` - Bulk mark read
- `GET /request-hub/api/notifications/unread-count` - API endpoint

### Analytics Route
- `GET /request-hub/staff/analytics` - Statistics dashboard

### Recurring Request Routes
- `GET /request-hub/staff/recurring` - List templates
- `GET /request-hub/staff/recurring/create` - Create form
- `POST /request-hub/staff/recurring/create` - Submit template
- `POST /request-hub/staff/recurring/<id>/toggle` - Toggle active
- `POST /request-hub/staff/recurring/<id>/delete` - Delete template
- `POST /request-hub/staff/recurring/<id>/create-now` - Manual trigger

### Receipt Route
- `GET /request-hub/submission/<id>/receipt` - Download PDF receipt

### Bulk Download Route
- `GET /request-hub/staff/request/<id>/download-all` - Download all as ZIP

---

## Templates Created/Modified

### New Templates
1. `app/templates/request_hub/notifications.html` - Notification center
2. `app/templates/request_hub/analytics.html` - Analytics dashboard
3. `app/templates/request_hub/recurring_requests.html` - Template list
4. `app/templates/request_hub/create_recurring.html` - Template form

### Modified Templates
1. `app/templates/base.html` - Added notification bell with badge
2. `app/templates/request_hub/staff_index.html` - Added Analytics & Recurring buttons
3. `app/templates/request_hub/view_request.html` - Added bulk download & receipt buttons
4. `app/templates/request_hub/intern_view_request.html` - Added receipt download button

---

## Future Enhancements (Not Yet Implemented)

1. **Email Notifications**: Send email alerts in addition to in-app notifications
2. **Deadline Reminders**: Automated reminders 24 hours before deadline
3. **Recurring Scheduler**: Background job to process recurring request templates
4. **Request Templates**: Quick-create requests from pre-saved templates
5. **Batch Actions**: Approve/reject multiple submissions at once
6. **Comments System**: Discussion thread on submissions
7. **File Type Restrictions**: Limit allowed file formats
8. **File Size Limits**: Set maximum upload sizes
9. **Document Preview**: View documents in browser without downloading

---

## Testing Checklist

- [ ] Create a request and verify bulk download works
- [ ] Submit as intern and check notification appears
- [ ] Test notification bell badge updates
- [ ] View analytics dashboard and verify metrics
- [ ] Create recurring template and verify storage
- [ ] Download PDF receipt as intern
- [ ] Download PDF receipt as staff
- [ ] Test mark as read for notifications
- [ ] Toggle recurring request active/inactive
- [ ] Manually trigger recurring request creation

---

## Deployment Notes

1. Install new dependencies: `pip install -r requirements.txt`
2. Database tables will auto-create on restart (SQLAlchemy)
3. Create `app/static/submission_receipts/` directory (auto-created by code)
4. For production: Set up background scheduler for recurring requests
5. For production: Configure email settings for email notifications

---

## Summary

All 5 requested enhancements have been successfully implemented:

✅ **Bulk Download** - ZIP all submissions with organized folders  
✅ **Notification System** - Real-time in-app notifications with bell icon  
✅ **Analytics Dashboard** - 6 key metrics for request performance  
✅ **Recurring Requests** - Automated request creation with templates  
✅ **Submission Receipts** - Professional PDF receipts with reportlab  

The system is now ready for testing. Some features (email notifications, recurring scheduler) require additional background job setup for full automation.
