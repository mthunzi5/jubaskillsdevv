# Request Hub Feature - Implementation Summary

## Overview
The Request Hub is a comprehensive document request and submission system that allows staff to request documents or information from interns (individually, by type, or all), and enables interns to submit multiple documents with optional text responses.

## Key Features

### For Staff
1. **Create Requests**
   - Define request title, description, and type (timesheet, ID document, certificates, etc.)
   - Target specific users or groups (all interns, varsity only, TVET only, or specific intern)
   - Set optional deadlines
   - Configure document requirements (up to 25 files per submission)
   - Add optional text field for additional information
   
2. **Manage Requests**
   - View all requests with completion statistics
   - Track submissions (submitted vs. expected)
   - Toggle request active/inactive status
   - Delete requests (removes all submissions and files)
   
3. **Review Submissions**
   - View all submissions for a request
   - Filter by status (all, submitted, pending)
   - Download submitted documents
   - Approve or reject submissions with feedback notes
   - View submission history and review details

### For Interns
1. **View Assigned Requests**
   - See all requests assigned to them (based on target type)
   - Check submission status (not submitted, pending review, approved, rejected)
   - View deadlines and overdue status
   - Read staff feedback on reviewed submissions
   
2. **Submit Responses**
   - Upload multiple documents (up to the limit set by staff)
   - Name each document for easy identification
   - Provide text responses if required
   - Update submissions before deadline
   - Delete uploaded documents before deadline
   
3. **Track Submission Status**
   - View submission date and time
   - See review status and staff feedback
   - Download previously uploaded documents
   - Monitor deadline compliance

## Technical Implementation

### Database Models
- **Request**: Main request model with targeting, deadline, and document settings
- **RequestSubmission**: Individual intern submissions for requests
- **RequestDocument**: Uploaded documents with metadata (filename, size, mime type, custom name)

### Routes
**Staff Routes** (`/request-hub/staff/`):
- `GET /` - List all requests with stats
- `GET/POST /create` - Create new request
- `GET /<id>` - View request details and submissions
- `GET /<submission_id>` - View specific submission
- `POST /<submission_id>/review` - Approve/reject submission
- `POST /<id>/toggle` - Activate/deactivate request
- `POST /<id>/delete` - Delete request and all data

**Intern Routes** (`/request-hub/intern/`):
- `GET /` - View assigned requests
- `GET /request/<id>` - View request details and submit
- `POST /request/<id>/submit` - Submit or update submission
- `POST /document/<id>/delete` - Delete uploaded document

**Shared Routes**:
- `GET /download/<document_id>` - Download a document

### Features
1. **Smart Targeting**
   - Specific user selection
   - All interns
   - Varsity interns only
   - TVET interns only
   
2. **Multi-File Upload**
   - Up to 25 documents per submission (configurable)
   - Custom naming for each document
   - File type detection with icons
   - Size tracking and formatted display
   
3. **Deadline Management**
   - Optional deadline setting
   - Automatic overdue detection
   - Prevents submissions after deadline
   - Locks editing after deadline
   
4. **Review System**
   - Approve/reject submissions
   - Add review notes/feedback
   - Track reviewer and review date
   - Display feedback to interns
   
5. **Progress Tracking**
   - Real-time completion rates
   - Visual progress bars
   - Expected vs. submitted counts
   - Status badges (pending, approved, rejected)

## File Storage
- Documents stored in `app/static/request_documents/`
- Filename format: `{user_id}_{timestamp}_{index}_{original_filename}`
- Automatic directory creation
- Secure filename handling with werkzeug

## UI Features
1. **Staff Interface**
   - Card-based request list with stats
   - Tabbed submission view (all, submitted, pending)
   - Color-coded status badges
   - Responsive design with Bootstrap 5
   
2. **Intern Interface**
   - Card-based request cards with submission status
   - Dynamic file input (add/remove files)
   - Document naming support
   - Deadline warnings and overdue indicators
   
3. **Navigation**
   - Staff: "Request Hub" in sidebar
   - Interns: "My Requests" in sidebar
   - Active state highlighting

## Request Types
Predefined types include:
- Timesheet
- ID Document
- Proof of Registration
- Certificate
- Report
- Proof of Residence
- Other

## Security
- Role-based access control (staff can create/review, interns can submit)
- Ownership verification for document operations
- Deadline enforcement for submissions
- File upload validation
- Path traversal prevention with secure_filename

## Usage Scenarios

### Example 1: Monthly Timesheets
Staff creates a request:
- Title: "Submit November Timesheets"
- Type: Timesheet
- Target: All Interns
- Deadline: December 5, 2025
- Max Documents: 5
- All interns see the request and submit their timesheets
- Staff reviews and approves/rejects each submission

### Example 2: Proof of Registration (Varsity Only)
Staff creates a request:
- Title: "Submit Proof of Registration for 2025"
- Type: Proof of Registration
- Target: Varsity Interns Only
- Max Documents: 3
- Only varsity interns see and submit
- Staff verifies registration documents

### Example 3: Specific Intern Document Request
Staff creates a request:
- Title: "Submit Updated ID Copy"
- Type: ID Document
- Target: Specific Intern (John Doe)
- Max Documents: 2
- Only John Doe sees the request
- John submits updated ID documents

## Files Created/Modified

### New Files
1. `app/models/request_hub.py` - Request, RequestSubmission, RequestDocument models
2. `app/routes/request_hub.py` - All request hub routes
3. `app/templates/request_hub/staff_index.html` - Staff request list
4. `app/templates/request_hub/create_request.html` - Create request form
5. `app/templates/request_hub/view_request.html` - Request details with submissions
6. `app/templates/request_hub/view_submission.html` - Individual submission view
7. `app/templates/request_hub/intern_index.html` - Intern request list
8. `app/templates/request_hub/intern_view_request.html` - Intern submission form
9. `app/static/request_documents/` - Document upload directory

### Modified Files
1. `app/models/__init__.py` - Added Request Hub model imports
2. `app/__init__.py` - Registered request_hub blueprint
3. `app/templates/base.html` - Added Request Hub navigation links

## Testing Checklist
- [x] Staff can create requests with all target types
- [x] Staff can view requests and submissions
- [x] Staff can approve/reject submissions
- [x] Staff can toggle request status
- [x] Staff can delete requests
- [x] Interns see only assigned requests
- [x] Interns can submit documents (up to limit)
- [x] Interns can name documents
- [x] Interns can update submissions before deadline
- [x] Interns can delete documents before deadline
- [x] Deadline enforcement works correctly
- [x] File downloads work for both staff and interns
- [x] Progress tracking displays correctly
- [x] Navigation links work properly

## Future Enhancements (Optional)
- Email notifications when requests are created
- Email reminders before deadlines
- Bulk approval/rejection
- Export submissions to ZIP
- Request templates
- Document version history
- Comment threads on submissions
- Mobile app support
- Request scheduling (auto-create monthly)
- Analytics dashboard

## Server Information
- Development server running on: http://127.0.0.1:5000
- Database: SQLite (auto-creates tables on first run)
- Python version: 3.x
- Flask version: 3.0.0
