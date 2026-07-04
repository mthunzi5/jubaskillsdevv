"""Helper functions for generating PDF receipts for request submissions"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from datetime import datetime
import io
import os


def generate_submission_receipt(submission):
    """
    Generate a PDF receipt for a submission
    Returns the file path of the generated PDF
    """
    # Create receipts directory if it doesn't exist
    receipts_dir = os.path.join('app', 'static', 'submission_receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"receipt_{submission.id}_{timestamp}.pdf"
    filepath = os.path.join(receipts_dir, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#3498db'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    title = Paragraph("SUBMISSION RECEIPT", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Receipt info
    receipt_info = [
        ['Receipt Generated:', datetime.utcnow().strftime('%d %B %Y at %H:%M:%S UTC')],
        ['Receipt ID:', f'#{submission.id}']
    ]
    
    receipt_table = Table(receipt_info, colWidths=[2*inch, 4*inch])
    receipt_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(receipt_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Request details section
    story.append(Paragraph("Request Details", heading_style))
    
    request_data = [
        ['Request Title:', submission.request.title],
        ['Request Type:', submission.request.request_type.replace('_', ' ').title()],
        ['Created By:', f"{submission.request.created_by.name} {submission.request.created_by.surname}"],
    ]
    
    if submission.request.deadline:
        request_data.append(['Deadline:', submission.request.deadline.strftime('%d %B %Y at %H:%M')])
    
    request_table = Table(request_data, colWidths=[2*inch, 4*inch])
    request_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    
    story.append(request_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Submitter details section
    story.append(Paragraph("Submitter Information", heading_style))
    
    submitter_data = [
        ['Name:', f"{submission.user.name} {submission.user.surname}"],
        ['Email:', submission.user.email],
        ['ID Number:', submission.user.id_number],
        ['Submitted At:', submission.submitted_at.strftime('%d %B %Y at %H:%M:%S')],
    ]
    
    submitter_table = Table(submitter_data, colWidths=[2*inch, 4*inch])
    submitter_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    
    story.append(submitter_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Text content if provided
    if submission.text_content:
        story.append(Paragraph("Text Response", heading_style))
        text_para = Paragraph(submission.text_content.replace('\n', '<br/>'), styles['Normal'])
        story.append(text_para)
        story.append(Spacer(1, 0.3*inch))
    
    # Documents section
    documents = submission.documents.all()
    if documents:
        story.append(Paragraph(f"Uploaded Documents ({len(documents)})", heading_style))
        
        doc_data = [['#', 'Document Name', 'File Size']]
        for idx, document in enumerate(documents, 1):
            doc_name = document.document_name if document.document_name else document.original_filename
            doc_data.append([str(idx), doc_name, document.get_file_size_formatted()])
        
        doc_table = Table(doc_data, colWidths=[0.5*inch, 4*inch, 1.5*inch])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(doc_table)
    
    story.append(Spacer(1, 0.5*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    footer_text = """
    <para align=center>
    <b>This is an automatically generated receipt.</b><br/>
    Juba Skills Development Academy and Training - Learning Management System<br/>
    Keep this receipt for your records.
    </para>
    """
    
    story.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(story)
    
    return filepath


def download_submission_receipt(submission_id):
    """Get the path to the most recent receipt for a submission"""
    receipts_dir = os.path.join('app', 'static', 'submission_receipts')
    
    # Find all receipts for this submission
    receipts = [f for f in os.listdir(receipts_dir) if f.startswith(f'receipt_{submission_id}_')]
    
    if not receipts:
        return None
    
    # Return the most recent one
    receipts.sort(reverse=True)
    return os.path.join(receipts_dir, receipts[0])


def generate_certificate_pdf(certificate):
    """Generate a styled one-page certificate PDF on disk and return file path."""
    certs_dir = os.path.join('app', 'static', 'certificates')
    os.makedirs(certs_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"certificate_{certificate.id}_{timestamp}.pdf"
    filepath = os.path.join(certs_dir, filename)

    _render_certificate_canvas(certificate, file_path=filepath)

    return filepath


def generate_certificate_pdf_bytes(certificate):
    """Generate a styled one-page certificate PDF in memory and return bytes."""
    buffer = io.BytesIO()
    _render_certificate_canvas(certificate, output_stream=buffer)
    return buffer.getvalue()


def _render_certificate_canvas(certificate, file_path=None, output_stream=None):
    """Render a visual certificate page that mirrors the LMS certificate style."""
    target = output_stream if output_stream is not None else file_path
    if target is None:
        raise ValueError('Either file_path or output_stream must be provided')

    c = canvas.Canvas(target, pagesize=A4)
    page_width, page_height = A4

    margin = 0.45 * inch
    inner_margin = 0.22 * inch

    # Certificate background and border
    c.setFillColor(colors.HexColor('#f5f7fa'))
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin, fill=1, stroke=0)

    c.setStrokeColor(colors.HexColor('#28a745'))
    c.setLineWidth(4)
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin, fill=0, stroke=1)

    c.setStrokeColor(colors.HexColor('#89c997'))
    c.setLineWidth(1.4)
    c.rect(
        margin + inner_margin,
        margin + inner_margin,
        page_width - 2 * (margin + inner_margin),
        page_height - 2 * (margin + inner_margin),
        fill=0,
        stroke=1,
    )

    # Watermark
    c.saveState()
    c.translate(page_width / 2, page_height / 2)
    c.rotate(30)
    c.setFillColor(colors.Color(0, 0, 0, alpha=0.06))
    c.setFont('Helvetica-Bold', 42)
    c.drawCentredString(0, 0, 'JUBA CONSULTANTS  MICT')
    c.restoreState()

    # Logos
    images_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'static', 'images'))
    left_logo = os.path.join(images_dir, 'logo-footer.png')
    right_logo = os.path.join(images_dir, 'mictt.jfif')

    logo_y = page_height - 1.35 * inch
    logo_h = 0.72 * inch

    _draw_logo(c, left_logo, margin + 0.45 * inch, logo_y, 2.3 * inch, logo_h)
    _draw_logo(c, right_logo, page_width - margin - 2.75 * inch, logo_y, 2.3 * inch, logo_h)

    # Title area
    c.setFillColor(colors.HexColor('#2c3e50'))
    c.setFont('Helvetica-Bold', 29)
    c.drawCentredString(page_width / 2, page_height - 2.1 * inch, 'Certificate of Completion')

    c.setFillColor(colors.HexColor('#5f6d7a'))
    c.setFont('Helvetica', 12)
    c.drawCentredString(page_width / 2, page_height - 2.45 * inch, 'Juba Skills Development Academy')

    c.setStrokeColor(colors.HexColor('#28a745'))
    c.setLineWidth(1.6)
    c.line(margin + 0.7 * inch, page_height - 2.7 * inch, page_width - margin - 0.7 * inch, page_height - 2.7 * inch)

    # Recipient block
    c.setFillColor(colors.HexColor('#4b5563'))
    c.setFont('Helvetica', 14)
    c.drawCentredString(page_width / 2, page_height - 3.2 * inch, 'This is to certify that')

    c.setFillColor(colors.HexColor('#1f2937'))
    c.setFont('Times-Bold', 30)
    c.drawCentredString(page_width / 2, page_height - 3.85 * inch, (certificate.intern_name or '').strip())

    c.setStrokeColor(colors.HexColor('#28a745'))
    c.setLineWidth(1.2)
    c.line(page_width / 2 - 2.35 * inch, page_height - 3.95 * inch, page_width / 2 + 2.35 * inch, page_height - 3.95 * inch)

    learner_id = certificate.intern.id_number if certificate.intern and certificate.intern.id_number else 'N/A'
    c.setFillColor(colors.HexColor('#6b7280'))
    c.setFont('Helvetica', 11)
    c.drawCentredString(page_width / 2, page_height - 4.28 * inch, f'Learner ID: {learner_id}')

    cohort_name = _latest_cohort_name(certificate)
    if cohort_name:
        c.drawCentredString(page_width / 2, page_height - 4.5 * inch, f'Cohort: {cohort_name}')

    c.setFillColor(colors.HexColor('#374151'))
    c.setFont('Helvetica', 13)
    c.drawCentredString(page_width / 2, page_height - 4.95 * inch, 'has successfully completed')

    c.setFillColor(colors.HexColor('#1f2937'))
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(page_width / 2, page_height - 5.38 * inch, certificate.program_name or 'Skills Development Program')

    completion_text = certificate.completion_date.strftime('%B %d, %Y') if certificate.completion_date else 'N/A'
    c.setFillColor(colors.HexColor('#374151'))
    c.setFont('Helvetica', 12)
    c.drawCentredString(page_width / 2, page_height - 5.85 * inch, f'Completion Date: {completion_text}')

    c.setStrokeColor(colors.HexColor('#28a745'))
    c.setLineWidth(1.6)
    c.line(margin + 0.7 * inch, page_height - 6.18 * inch, page_width - margin - 0.7 * inch, page_height - 6.18 * inch)

    # Signature row
    sign_y = page_height - 7.05 * inch
    left_x = margin + 0.95 * inch
    mid_x = page_width / 2
    right_x = page_width - margin - 0.95 * inch

    for x in (left_x, mid_x, right_x):
        c.setStrokeColor(colors.HexColor('#111111'))
        c.setLineWidth(1)
        c.line(x - 1.12 * inch, sign_y, x + 1.12 * inch, sign_y)

    issuer_name = _full_name(certificate.issuer) or 'Issuer'
    approver_name = certificate.admin_signature or _full_name(certificate.approver) or 'Pending Admin Signature'
    issue_text = certificate.issue_date.strftime('%B %d, %Y') if certificate.issue_date else 'N/A'

    c.setFillColor(colors.HexColor('#111111'))
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(left_x, sign_y - 0.2 * inch, issuer_name)
    c.drawCentredString(mid_x, sign_y - 0.2 * inch, approver_name)
    c.drawCentredString(right_x, sign_y - 0.2 * inch, issue_text)

    c.setFillColor(colors.HexColor('#6b7280'))
    c.setFont('Helvetica', 9)
    issuer_role = (certificate.issuer.role.title() if certificate.issuer and certificate.issuer.role else 'Issued By')
    c.drawCentredString(left_x, sign_y - 0.36 * inch, f'{issuer_role} (Issued By)')
    c.drawCentredString(mid_x, sign_y - 0.36 * inch, 'Administrator (Approved)')
    c.drawCentredString(right_x, sign_y - 0.36 * inch, 'Date Issued')

    # Footer details
    c.setFillColor(colors.HexColor('#6b7280'))
    c.setFont('Helvetica', 9)
    cert_number = certificate.certificate_number or 'N/A'
    c.drawCentredString(page_width / 2, margin + 0.35 * inch, f'Certificate Number: {cert_number}')

    c.showPage()
    c.save()


def _draw_logo(pdf_canvas, path, x, y, width, height):
    """Draw a logo image safely if available and decodable."""
    if not os.path.exists(path):
        return
    try:
        reader = ImageReader(path)
        pdf_canvas.drawImage(reader, x, y, width=width, height=height, preserveAspectRatio=True, anchor='c', mask='auto')
    except Exception:
        # Keep certificate generation resilient if a logo file has decode issues.
        return


def _full_name(user):
    if not user:
        return ''
    return f"{(user.name or '').strip()} {(user.surname or '').strip()}".strip()


def _latest_cohort_name(certificate):
    """Best-effort lookup for latest cohort name from learner memberships."""
    intern = getattr(certificate, 'intern', None)
    memberships = getattr(intern, 'cohort_memberships', None)
    if not memberships:
        return None

    try:
        latest_membership = memberships[-1]
    except Exception:
        latest_membership = None

    if latest_membership and getattr(latest_membership, 'cohort', None):
        return latest_membership.cohort.name
    return None
