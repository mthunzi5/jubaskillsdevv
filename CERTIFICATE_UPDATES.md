# Certificate System Updates - Admin Approval & Direct Award

## Overview
Updated the certificate system to implement a two-step approval process where staff can issue certificates, but only admins can approve and sign them. Also added functionality for admins to directly award certificates bypassing normal completion requirements.

---

## Database Changes

### Certificate Model Updates
Added new fields to `Certificate` model:

```python
# Admin Approval and Signing
is_approved = db.Column(db.Boolean, default=False)
approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
approved_at = db.Column(db.DateTime, nullable=True)
admin_signature = db.Column(db.String(200), nullable=True)
admin_notes = db.Column(db.Text, nullable=True)
```

**New Relationship:**
```python
approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_certificates')
```

---

## New Routes

### 1. Approve Certificate
**Route:** `POST /lms/certificates/<cert_id>/approve`  
**Access:** Admin only  
**Purpose:** Admin approves and signs a certificate issued by staff

**Features:**
- Checks if already approved
- Sets `is_approved = True`
- Records approver details
- Adds admin signature
- Allows optional admin notes

---

### 2. Reject Certificate
**Route:** `POST /lms/certificates/<cert_id>/reject`  
**Access:** Admin only  
**Purpose:** Admin rejects a certificate

**Features:**
- Deactivates the certificate
- Records rejection reason in admin_notes
- Cannot reject already approved certificates

---

### 3. Award Certificate Directly
**Route:** `GET/POST /lms/certificates/award/<intern_id>`  
**Access:** Admin only  
**Purpose:** Admin awards certificate directly without completion checks

**Features:**
- Bypasses normal eligibility requirements
- Shows intern's current progress for reference
- Allows custom program name, hours, grade, tasks
- Auto-approved and signed upon creation
- Supports admin notes for documentation

**Form Fields:**
- Program Name
- Total Hours
- Final Grade (%)
- Tasks Completed
- Admin Notes

---

## Template Updates

### 1. `view_certificate.html`

**Admin Approval Section:**
- Shows approval status at top
- Pending certificates show approval form for admins
- Approved certificates show approval details
- Print button disabled until approved

**Signature Section:**
- Updated to show 3 signatures:
  1. Issuer (Staff who created)
  2. Admin Signature (Approver)
  3. Date Issued
- Pending certificates show "Pending Admin Signature"

**Reject Modal:**
- Modal for rejecting certificates
- Requires rejection reason
- Confirms before rejecting

---

### 2. `certificates_list.html`

**Status Badges:**
- Green badge: "Approved" (with checkmark)
- Yellow badge: "Pending Approval" (with clock icon)

---

### 3. `progress_dashboard.html`

**Admin Award Button:**
- New "Award Certificate (Admin)" button
- Only visible to admins
- Only shown if certificate not yet issued
- Links to direct award form

---

### 4. `award_certificate.html` (NEW)

**Direct Award Form:**
- Displays intern information
- Shows current progress (if exists)
- Form for entering certificate details
- Warning that certificate will be auto-approved
- Pre-fills data from progress tracking

---

## Workflow

### Normal Certificate Issuance (Staff)
1. **Staff** generates certificate when intern meets requirements
2. Certificate created with `is_approved = False`
3. **Admin** reviews certificate
4. **Admin** approves and signs OR rejects
5. If approved, certificate ready for printing

### Direct Award (Admin Only)
1. **Admin** navigates to Progress Dashboard
2. Clicks "Award Certificate (Admin)" for any intern
3. Fills in certificate details
4. Certificate created with `is_approved = True`
5. Auto-signed by admin
6. Immediately ready for printing

---

## Key Features

### Security
- Only admins can approve/reject certificates
- Role check on all admin routes
- Cannot reject already approved certificates

### Flexibility
- Admins can override normal completion requirements
- Custom program names, hours, grades, tasks
- Admin notes for documentation

### Transparency
- Approval status visible to all users
- Approval date and approver recorded
- Clear signature section on certificate

### User Experience
- Print button disabled until approved
- Clear status indicators (badges, alerts)
- Modal confirmation for rejection
- Pre-filled forms with current progress data

---

## Admin Actions Summary

**From Certificate View:**
- ✅ Approve & Sign certificate
- ❌ Reject certificate
- 📝 Add approval notes

**From Progress Dashboard:**
- 🎖️ Award certificate directly (bypass requirements)
- 📊 View current progress before awarding

---

## Testing Checklist

- [ ] Admin can view certificates list with status badges
- [ ] Admin sees approval form on pending certificates
- [ ] Admin can approve certificate with notes
- [ ] Admin signature appears on certificate after approval
- [ ] Admin can reject certificate with reason
- [ ] Print button disabled on unapproved certificates
- [ ] Admin can award certificate directly from progress dashboard
- [ ] Direct award form pre-fills with current progress
- [ ] Directly awarded certificates are auto-approved
- [ ] Staff cannot access admin-only routes
- [ ] Interns see pending status on their certificates

---

## Database Reset

✅ **Old database deleted**  
✅ **Fresh database created with updated schema**  
✅ **Default admin account created:** `admin@juba.ac.za / Admin@2025`

---

## Files Modified

### Models
- `app/models/certificate.py` - Added approval fields and relationship

### Routes
- `app/routes/lms.py` - Added 3 new routes (approve, reject, award_direct)

### Templates
- `app/templates/lms/view_certificate.html` - Admin approval UI and 3-signature layout
- `app/templates/lms/certificates_list.html` - Status badges
- `app/templates/lms/progress_dashboard.html` - Admin award button
- `app/templates/lms/award_certificate.html` - **NEW** direct award form

---

## Next Steps (Optional Enhancements)

1. **Email Notifications**
   - Notify admin when staff issues certificate
   - Notify staff/intern when admin approves/rejects

2. **Certificate Revocation**
   - Allow admin to revoke approved certificates
   - Add revocation reason and date

3. **Bulk Actions**
   - Approve multiple certificates at once
   - Export certificate data to Excel/CSV

4. **Certificate Templates**
   - Multiple certificate designs
   - Custom branding per program

5. **Audit Trail**
   - Log all certificate actions
   - Track who did what and when

---

## Summary

The certificate system now has a robust two-step approval process:
1. **Staff** issue certificates based on completion
2. **Admin** reviews, approves, and signs
3. **Admin** can also directly award certificates for special cases

This ensures proper oversight while maintaining flexibility for exceptional circumstances. All actions are tracked and visible to relevant users.
