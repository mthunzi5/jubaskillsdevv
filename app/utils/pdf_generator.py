"""Helper functions for generating PDF receipts for request submissions"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
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
