from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import TrainingMaterial, Task, Progress, Certificate, Evaluation, User, TaskDeletionRequest, TaskDeletionHistory, TaskV2, TaskAssignment, QuizQuestion, QuizAnswer, MaterialDeletionRequest, MaterialDeletionHistory
from app.utils.decorators import admin_required, staff_required
from datetime import datetime
import os

lms_bp = Blueprint('lms', __name__, url_prefix='/lms')

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'xlsx', 'xls', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============= TRAINING MATERIALS =============

@lms_bp.route('/materials')
@login_required
def materials_list():
    """View all training materials"""
    category = request.args.get('category', 'all')
    
    query = TrainingMaterial.query.filter_by(is_active=True)
    if category != 'all':
        query = query.filter_by(category=category)
    
    materials = query.order_by(TrainingMaterial.created_at.desc()).all()
    categories = db.session.query(TrainingMaterial.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('lms/materials_list.html', 
                         materials=materials, 
                         categories=categories,
                         current_category=category)

@lms_bp.route('/materials/upload', methods=['GET', 'POST'])
@login_required
@staff_required
def upload_material():
    """Upload new training material (staff only)"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Create materials directory if it doesn't exist
            materials_dir = os.path.join('app', 'static', 'materials')
            os.makedirs(materials_dir, exist_ok=True)
            
            filepath = os.path.join(materials_dir, unique_filename)
            file.save(filepath)
            
            # Get file size
            file_size = os.path.getsize(filepath)
            file_type = filename.rsplit('.', 1)[1].lower()
            
            # Save to database
            material = TrainingMaterial(
                title=title,
                description=description,
                category=category,
                file_path=f'materials/{unique_filename}',
                file_type=file_type,
                file_size=file_size,
                uploaded_by=current_user.id
            )
            
            db.session.add(material)
            db.session.commit()
            
            flash(f'Training material "{title}" uploaded successfully!', 'success')
            return redirect(url_for('lms.materials_list'))
        else:
            flash('Invalid file type. Allowed types: PDF, DOC, DOCX, PPT, PPTX, TXT, XLSX, XLS, ZIP', 'danger')
    
    return render_template('lms/upload_material.html')

@lms_bp.route('/materials/<int:material_id>/download')
@login_required
def download_material(material_id):
    """Download a training material"""
    material = TrainingMaterial.query.get_or_404(material_id)
    # file_path already contains the full path from static folder
    filepath = os.path.join(current_app.root_path, 'static', material.file_path)
    
    return send_file(filepath, as_attachment=True, download_name=f"{material.title}.{material.file_type}")

@lms_bp.route('/materials/<int:material_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_material(material_id):
    """Request deletion of a training material (requires admin approval)"""
    material = TrainingMaterial.query.get_or_404(material_id)
    reason = request.form.get('reason', '').strip()
    
    if not reason:
        flash('Please provide a reason for deletion.', 'error')
        return redirect(url_for('lms.materials'))
    
    # Create deletion request
    deletion_request = MaterialDeletionRequest(
        material_id=material_id,
        requested_by_id=current_user.id,
        reason=reason,
        status='pending'
    )
    
    db.session.add(deletion_request)
    db.session.commit()
    
    flash('Deletion request submitted. Awaiting admin approval.', 'info')
    return redirect(url_for('lms.materials_list'))

# ============= TASKS =============

@lms_bp.route('/tasks')
@login_required
def tasks_list():
    """Redirect to V2 tasks"""
    status_filter = request.args.get('status', 'all')
    return redirect(url_for('lms.tasks_list_v2', status=status_filter))

@lms_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_task():
    """Redirect to V2 task creation"""
    return redirect(url_for('lms.create_task_v2'))

@lms_bp.route('/tasks/create_old', methods=['GET', 'POST'])
@login_required
@staff_required
def create_task_old():
    """Create new task (staff only)"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        assign_type = request.form.get('assign_type')
        due_date_str = request.form.get('due_date')
        priority = request.form.get('priority', 'medium')
        
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        
        # Determine which interns to assign based on assignment type
        if assign_type == 'all':
            interns = User.query.filter_by(role='intern', is_deleted=False).all()
            intern_ids = [intern.id for intern in interns]
        elif assign_type == 'varsity':
            interns = User.query.filter_by(role='intern', intern_type='varsity', is_deleted=False).all()
            intern_ids = [intern.id for intern in interns]
        elif assign_type == 'tvet':
            interns = User.query.filter_by(role='intern', intern_type='tvet', is_deleted=False).all()
            intern_ids = [intern.id for intern in interns]
        elif assign_type == 'individual':
            assigned_to_list = request.form.getlist('assigned_to')
            intern_ids = [int(id) for id in assigned_to_list]
        else:
            flash('Please select an assignment type', 'danger')
            return redirect(request.url)
        
        if not intern_ids:
            flash('No interns found for the selected assignment type', 'warning')
            return redirect(request.url)
        
        # Create task for each selected intern
        tasks_created = 0
        for intern_id in intern_ids:
            task = Task(
                title=title,
                description=description,
                category=category,
                assigned_to=intern_id,
                assigned_by=current_user.id,
                due_date=due_date,
                priority=priority,
                status='pending'
            )
            db.session.add(task)
            tasks_created += 1
            
            # Create progress record if needed
            progress = Progress.query.filter_by(intern_id=intern_id).first()
            if not progress:
                progress = Progress(intern_id=intern_id)
                db.session.add(progress)
        
        # Commit tasks first
        db.session.commit()
        
        # Now update progress for each intern
        for intern_id in intern_ids:
            progress = Progress.query.filter_by(intern_id=intern_id).first()
            if progress:
                progress.update_progress()
        
        db.session.commit()
        
        assignment_type_name = {
            'all': 'all',
            'varsity': 'varsity',
            'tvet': 'TVET',
            'individual': 'selected'
        }.get(assign_type, 'selected')
        
        flash(f'Task "{title}" assigned to {tasks_created} {assignment_type_name} intern(s) successfully!', 'success')
        return redirect(url_for('lms.tasks_list'))
    
    # Get all interns for assignment
    interns = User.query.filter_by(role='intern', is_deleted=False).all()
    return render_template('lms/create_task.html', interns=interns)

@lms_bp.route('/tasks/<int:task_id>')
@login_required
def view_task(task_id):
    """View task details"""
    task = Task.query.get_or_404(task_id)
    
    # Check permissions
    if current_user.role == 'intern' and task.assigned_to != current_user.id:
        flash('You do not have permission to view this task', 'danger')
        return redirect(url_for('lms.tasks_list'))
    
    return render_template('lms/view_task.html', task=task)

@lms_bp.route('/tasks/<int:task_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_task(task_id):
    """Submit task (intern only)"""
    task = Task.query.get_or_404(task_id)
    
    if task.assigned_to != current_user.id:
        flash('You do not have permission to submit this task', 'danger')
        return redirect(url_for('lms.tasks_list'))
    
    if request.method == 'POST':
        submission_text = request.form.get('submission_text')
        
        task.submission_text = submission_text
        task.status = 'submitted'
        task.submitted_at = datetime.utcnow()
        
        # Handle file upload
        if 'submission_file' in request.files:
            file = request.files['submission_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"submission_{task_id}_{timestamp}_{filename}"
                
                submissions_dir = os.path.join('app', 'static', 'submissions')
                os.makedirs(submissions_dir, exist_ok=True)
                
                filepath = os.path.join(submissions_dir, unique_filename)
                file.save(filepath)
                
                task.submission_file = f'submissions/{unique_filename}'
        
        db.session.commit()
        
        flash('Task submitted successfully!', 'success')
        return redirect(url_for('lms.view_task', task_id=task_id))
    
    return render_template('lms/submit_task.html', task=task)

@lms_bp.route('/tasks/<int:task_id>/delete', methods=['GET', 'POST'])
@login_required
@staff_required
def delete_task(task_id):
    """Request task deletion (staff) or delete immediately (admin)"""
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        reason = request.form.get('reason')
        
        if not reason or len(reason.strip()) < 10:
            flash('Please provide a detailed reason (at least 10 characters)', 'danger')
            return render_template('lms/delete_task.html', task=task)
        
        if current_user.is_admin():
            # Admin can delete immediately
            # Create deletion history
            history = TaskDeletionHistory(
                task_id=task.id,
                task_title=task.title,
                task_description=task.description,
                task_category=task.category,
                assigned_to_name=task.intern.full_name,
                assigned_by_name=task.assigner.full_name,
                task_status=task.status,
                task_grade=task.grade,
                deletion_reason=reason,
                deleted_by=current_user.id,
                approved_by=current_user.id,
                approved_at=datetime.utcnow()
            )
            db.session.add(history)
            
            # Permanently delete
            db.session.delete(task)
            db.session.commit()
            
            # Update progress
            progress = Progress.query.filter_by(intern_id=task.assigned_to).first()
            if progress:
                progress.update_progress()
                db.session.commit()
            
            flash('Task deleted permanently!', 'success')
        else:
            # Staff must request approval
            # Check if deletion request already exists
            existing_request = TaskDeletionRequest.query.filter_by(
                task_id=task_id, 
                status='pending'
            ).first()
            
            if existing_request:
                flash('Task deleted successfully!', 'success')
                return redirect(url_for('lms.tasks_list'))
            
            # Create deletion request
            deletion_request = TaskDeletionRequest(
                task_id=task_id,
                reason=reason,
                requested_by=current_user.id
            )
            db.session.add(deletion_request)
            
            # Hide task from staff view (soft delete)
            task.is_active = False
            db.session.commit()
            
            flash('Task deleted successfully!', 'success')
        
        return redirect(url_for('lms.tasks_list'))
    
    return render_template('lms/delete_task.html', task=task)

@lms_bp.route('/tasks/<int:task_id>/grade', methods=['GET', 'POST'])
@login_required
@staff_required
def grade_task(task_id):
    """Grade a submitted task (staff only)"""
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        grade = float(request.form.get('grade'))
        feedback = request.form.get('feedback')
        
        task.grade = grade
        task.feedback = feedback
        task.status = 'completed'
        task.graded_by = current_user.id
        task.graded_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update progress
        progress = Progress.query.filter_by(intern_id=task.assigned_to).first()
        if progress:
            progress.update_progress()
            db.session.commit()
        
        flash('Task graded successfully!', 'success')
        return redirect(url_for('lms.view_task', task_id=task_id))
    
    return render_template('lms/grade_task.html', task=task)

# ============= PROGRESS TRACKING =============

@lms_bp.route('/progress')
@login_required
def progress_dashboard():
    """View progress (interns see their own, staff see all)"""
    if current_user.role == 'intern':
        progress = Progress.query.filter_by(intern_id=current_user.id).first()
        if not progress:
            progress = Progress(intern_id=current_user.id)
            db.session.add(progress)
            db.session.commit()
        
        progress.update_progress()
        db.session.commit()
        
        return render_template('lms/intern_progress.html', progress=progress, intern=current_user)
    else:
        # Staff view - show all interns
        interns = User.query.filter_by(role='intern', is_deleted=False).all()
        progress_data = []
        
        for intern in interns:
            progress = Progress.query.filter_by(intern_id=intern.id).first()
            if not progress:
                progress = Progress(intern_id=intern.id)
                db.session.add(progress)
            
            progress.update_progress()
            progress_data.append({
                'intern': intern,
                'progress': progress
            })
        
        db.session.commit()
        
        return render_template('lms/progress_dashboard.html', progress_data=progress_data)

# ============= CERTIFICATES =============

@lms_bp.route('/certificates')
@login_required
def certificates_list():
    """View certificates"""
    if current_user.role == 'intern':
        certificates = Certificate.query.filter_by(intern_id=current_user.id, is_active=True).all()
    else:
        certificates = Certificate.query.filter_by(is_active=True).order_by(Certificate.issue_date.desc()).all()
    
    return render_template('lms/certificates_list.html', certificates=certificates)

@lms_bp.route('/certificates/generate/<int:intern_id>', methods=['POST'])
@login_required
@staff_required
def generate_certificate(intern_id):
    """Generate certificate for eligible intern (staff only)"""
    intern = User.query.get_or_404(intern_id)
    progress = Progress.query.filter_by(intern_id=intern_id).first()
    
    if not progress or not progress.is_eligible_for_certificate:
        flash('Intern is not eligible for certificate yet', 'warning')
        return redirect(url_for('lms.progress_dashboard'))
    
    if progress.certificate_issued:
        flash('Certificate already issued for this intern', 'info')
        return redirect(url_for('lms.certificates_list'))
    
    # Generate certificate
    cert_number = Certificate.generate_certificate_number()
    
    certificate = Certificate(
        certificate_number=cert_number,
        intern_id=intern_id,
        intern_name=f"{intern.name} {intern.surname}",
        total_hours=progress.total_hours_logged,
        final_grade=progress.average_grade,
        tasks_completed=progress.completed_tasks,
        issued_by=current_user.id
    )
    
    db.session.add(certificate)
    
    # Update progress
    progress.certificate_issued = True
    
    db.session.commit()
    
    flash(f'Certificate generated successfully! Certificate Number: {cert_number}', 'success')
    return redirect(url_for('lms.view_certificate', cert_id=certificate.id))

@lms_bp.route('/certificates/<int:cert_id>')
@login_required
def view_certificate(cert_id):
    """View certificate details"""
    certificate = Certificate.query.get_or_404(cert_id)
    
    # Check permissions
    if current_user.role == 'intern' and certificate.intern_id != current_user.id:
        flash('You do not have permission to view this certificate', 'danger')
        return redirect(url_for('lms.certificates_list'))
    
    return render_template('lms/view_certificate.html', certificate=certificate)

@lms_bp.route('/certificates/<int:cert_id>/approve', methods=['POST'])
@login_required
def approve_certificate(cert_id):
    """Admin approves and signs certificate"""
    from app.utils.decorators import admin_required
    
    if current_user.role != 'admin':
        flash('Only administrators can approve certificates', 'danger')
        return redirect(url_for('lms.certificates_list'))
    
    certificate = Certificate.query.get_or_404(cert_id)
    
    if certificate.is_approved:
        flash('Certificate is already approved', 'info')
        return redirect(url_for('lms.view_certificate', cert_id=cert_id))
    
    # Approve and sign the certificate
    certificate.is_approved = True
    certificate.approved_by = current_user.id
    certificate.approved_at = datetime.utcnow()
    certificate.admin_signature = f"{current_user.name} {current_user.surname}"
    certificate.admin_notes = request.form.get('admin_notes', '')
    
    db.session.commit()
    
    flash('Certificate approved and signed successfully!', 'success')
    return redirect(url_for('lms.view_certificate', cert_id=cert_id))

@lms_bp.route('/certificates/<int:cert_id>/reject', methods=['POST'])
@login_required
def reject_certificate(cert_id):
    """Admin rejects certificate"""
    if current_user.role != 'admin':
        flash('Only administrators can reject certificates', 'danger')
        return redirect(url_for('lms.certificates_list'))
    
    certificate = Certificate.query.get_or_404(cert_id)
    
    if certificate.is_approved:
        flash('Cannot reject an already approved certificate', 'warning')
        return redirect(url_for('lms.view_certificate', cert_id=cert_id))
    
    # Deactivate the certificate
    certificate.is_active = False
    certificate.admin_notes = request.form.get('rejection_reason', 'Certificate rejected by admin')
    
    db.session.commit()
    
    flash('Certificate rejected', 'success')
    return redirect(url_for('lms.certificates_list'))

@lms_bp.route('/certificates/award/<int:intern_id>', methods=['GET', 'POST'])
@login_required
def award_certificate_direct(intern_id):
    """Admin awards certificate directly without completion check"""
    if current_user.role != 'admin':
        flash('Only administrators can directly award certificates', 'danger')
        return redirect(url_for('lms.progress_dashboard'))
    
    intern = User.query.get_or_404(intern_id)
    
    if intern.role != 'intern':
        flash('Can only award certificates to interns', 'warning')
        return redirect(url_for('lms.progress_dashboard'))
    
    if request.method == 'POST':
        # Get form data
        program_name = request.form.get('program_name', 'Skills Development Program')
        total_hours = float(request.form.get('total_hours', 0))
        final_grade = float(request.form.get('final_grade', 0))
        tasks_completed = int(request.form.get('tasks_completed', 0))
        admin_notes = request.form.get('admin_notes', '')
        
        # Generate certificate number
        cert_number = Certificate.generate_certificate_number()
        
        # Create certificate
        certificate = Certificate(
            certificate_number=cert_number,
            intern_id=intern_id,
            intern_name=f"{intern.name} {intern.surname}",
            program_name=program_name,
            total_hours=total_hours,
            final_grade=final_grade,
            tasks_completed=tasks_completed,
            issued_by=current_user.id,
            is_approved=True,  # Auto-approved since admin is awarding directly
            approved_by=current_user.id,
            approved_at=datetime.utcnow(),
            admin_signature=f"{current_user.name} {current_user.surname}",
            admin_notes=admin_notes
        )
        
        db.session.add(certificate)
        
        # Update progress if exists
        progress = Progress.query.filter_by(intern_id=intern_id).first()
        if progress:
            progress.certificate_issued = True
        
        db.session.commit()
        
        flash(f'Certificate awarded successfully! Certificate Number: {cert_number}', 'success')
        return redirect(url_for('lms.view_certificate', cert_id=certificate.id))
    
    # GET request - show form
    progress = Progress.query.filter_by(intern_id=intern_id).first()
    return render_template('lms/award_certificate.html', intern=intern, progress=progress)

# ============= EVALUATIONS =============

@lms_bp.route('/evaluations')
@login_required
def evaluations_list():
    """View evaluations"""
    if current_user.role == 'intern':
        evaluations = Evaluation.query.filter_by(intern_id=current_user.id, is_active=True).all()
    else:
        evaluations = Evaluation.query.filter_by(is_active=True).order_by(Evaluation.evaluation_date.desc()).all()
    
    return render_template('lms/evaluations_list.html', evaluations=evaluations)

@lms_bp.route('/evaluations/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_evaluation():
    """Create evaluation for intern (staff only)"""
    if request.method == 'POST':
        intern_id = request.form.get('intern_id')
        period = request.form.get('period')
        
        # Get ratings
        technical_skills = int(request.form.get('technical_skills'))
        communication = int(request.form.get('communication'))
        teamwork = int(request.form.get('teamwork'))
        problem_solving = int(request.form.get('problem_solving'))
        punctuality = int(request.form.get('punctuality'))
        initiative = int(request.form.get('initiative'))
        professionalism = int(request.form.get('professionalism'))
        
        # Get feedback
        strengths = request.form.get('strengths')
        areas_for_improvement = request.form.get('areas_for_improvement')
        additional_comments = request.form.get('additional_comments')
        recommendations = request.form.get('recommendations')
        
        evaluation = Evaluation(
            intern_id=intern_id,
            evaluator_id=current_user.id,
            period=period,
            technical_skills=technical_skills,
            communication=communication,
            teamwork=teamwork,
            problem_solving=problem_solving,
            punctuality=punctuality,
            initiative=initiative,
            professionalism=professionalism,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            additional_comments=additional_comments,
            recommendations=recommendations
        )
        
        evaluation.calculate_overall_rating()
        
        db.session.add(evaluation)
        db.session.commit()
        
        flash('Evaluation submitted successfully!', 'success')
        return redirect(url_for('lms.view_evaluation', eval_id=evaluation.id))
    
    # Get all interns for evaluation
    interns = User.query.filter_by(role='intern', is_deleted=False).all()
    return render_template('lms/create_evaluation.html', interns=interns)

@lms_bp.route('/evaluations/<int:eval_id>')
@login_required
def view_evaluation(eval_id):
    """View evaluation details"""
    evaluation = Evaluation.query.get_or_404(eval_id)
    
    # Check permissions
    if current_user.role == 'intern' and evaluation.intern_id != current_user.id:
        flash('You do not have permission to view this evaluation', 'danger')
        return redirect(url_for('lms.evaluations_list'))
    
    return render_template('lms/view_evaluation.html', evaluation=evaluation)

# ============= TASK DELETION MANAGEMENT =============

@lms_bp.route('/tasks/deletion-requests')
@login_required
@admin_required
def task_deletion_requests():
    """View pending task deletion requests (admin only)"""
    pending_requests = TaskDeletionRequest.query.filter_by(status='pending').order_by(TaskDeletionRequest.requested_at.desc()).all()
    return render_template('lms/task_deletion_requests.html', requests=pending_requests)

@lms_bp.route('/tasks/deletion-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_task_deletion(request_id):
    """Approve task deletion request (admin only)"""
    deletion_request = TaskDeletionRequest.query.get_or_404(request_id)
    task = deletion_request.task
    
    # Create deletion history
    history = TaskDeletionHistory(
        task_id=task.id,
        task_title=task.title,
        task_description=task.description,
        task_category=task.category,
        assigned_to_name=f"{task.intern.name} {task.intern.surname}",
        assigned_by_name=f"{task.assigner.name} {task.assigner.surname}",
        task_status=task.status,
        task_grade=task.grade,
        deletion_reason=deletion_request.reason,
        deleted_by=deletion_request.requested_by,
        approved_by=current_user.id,
        approved_at=datetime.utcnow()
    )
    db.session.add(history)
    
    # Delete the deletion request and task together
    db.session.delete(deletion_request)
    db.session.delete(task)
    db.session.commit()
    
    # Update progress
    progress = Progress.query.filter_by(intern_id=task.assigned_to).first()
    if progress:
        progress.update_progress()
        db.session.commit()
    
    flash('Task deletion approved and task permanently deleted!', 'success')
    return redirect(url_for('lms.task_deletion_requests'))

@lms_bp.route('/tasks/deletion-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_task_deletion(request_id):
    """Reject task deletion request (admin only)"""
    deletion_request = TaskDeletionRequest.query.get_or_404(request_id)
    task = deletion_request.task
    
    review_comment = request.form.get('comment', '')
    
    # Update deletion request status
    deletion_request.status = 'rejected'
    deletion_request.reviewed_by = current_user.id
    deletion_request.reviewed_at = datetime.utcnow()
    deletion_request.review_comment = review_comment
    
    # Restore task visibility
    task.is_active = True
    db.session.commit()
    
    flash('Task deletion request rejected and task restored!', 'info')
    return redirect(url_for('lms.task_deletion_requests'))

@lms_bp.route('/tasks/deletion-history')
@login_required
@admin_required
def task_deletion_history():
    """View task deletion history (admin only)"""
    history = TaskDeletionHistory.query.order_by(TaskDeletionHistory.deleted_at.desc()).all()
    return render_template('lms/task_deletion_history.html', history=history)


# ============= ENHANCED TASKS V2 (Multi-step with type-specific content) =============

@lms_bp.route('/v2/tasks')
@login_required
def tasks_list_v2():
    """View tasks V2 - single task assigned to multiple interns"""
    status_filter = request.args.get('status', 'all')
    
    if current_user.role == 'intern':
        # Get assignments for this intern
        assignments = TaskAssignment.query.filter_by(intern_id=current_user.id).all()
        if status_filter != 'all':
            assignments = [a for a in assignments if a.status == status_filter]
        
        # Get tasks from assignments
        tasks = [a.task for a in assignments if a.task.is_active]
        
        return render_template('lms/tasks_list_v2.html', 
                             tasks=tasks,
                             assignments={a.task_id: a for a in assignments},
                             current_status=status_filter)
    else:
        # Staff/Admin see all tasks
        query = TaskV2.query.filter_by(is_active=True)
        tasks = query.order_by(TaskV2.due_date.asc()).all()
        
        return render_template('lms/tasks_list_v2.html', 
                             tasks=tasks,
                             assignments=None,
                             current_status=status_filter)

@lms_bp.route('/v2/tasks/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_task_v2():
    """Create new task V2 with multi-step process"""
    if request.method == 'POST':
        # Step 1: Basic Info
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        due_date_str = request.form.get('due_date')
        priority = request.form.get('priority', 'medium')
        
        # Step 2: Assignment
        assign_type = request.form.get('assign_type')
        
        # Step 3: Type-specific content
        passing_score = request.form.get('passing_score', 70.0)
        auto_grade = request.form.get('auto_grade') == 'on'
        
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        
        # Determine interns to assign
        if assign_type == 'all':
            interns = User.query.filter_by(role='intern', is_deleted=False).all()
        elif assign_type == 'varsity':
            interns = User.query.filter_by(role='intern', intern_type='varsity', is_deleted=False).all()
        elif assign_type == 'tvet':
            interns = User.query.filter_by(role='intern', intern_type='tvet', is_deleted=False).all()
        elif assign_type == 'individual':
            assigned_to_list = request.form.getlist('assigned_to')
            interns = User.query.filter(User.id.in_(assigned_to_list)).all()
        else:
            flash('Please select an assignment type', 'danger')
            return redirect(request.url)
        
        if not interns:
            flash('No interns found for the selected assignment type', 'warning')
            return redirect(request.url)
        
        # Handle file upload
        reference_file = None
        if 'reference_file' in request.files:
            file = request.files['reference_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                upload_folder = os.path.join('app', 'static', 'uploads', 'tasks')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                reference_file = filename
        
        # Create single task
        task = TaskV2(
            title=title,
            description=description,
            category=category,
            assigned_by=current_user.id,
            assign_type=assign_type,
            due_date=due_date,
            priority=priority,
            reference_file=reference_file,
            has_auto_grading=auto_grade if category == 'Quiz' else False,
            passing_score=float(passing_score) if category == 'Quiz' else 70.0
        )
        db.session.add(task)
        db.session.flush()  # Get task ID
        
        # Create assignments for each intern
        for intern in interns:
            assignment = TaskAssignment(
                task_id=task.id,
                intern_id=intern.id,
                status='pending'
            )
            db.session.add(assignment)
        
        # Handle Quiz questions
        if category == 'Quiz':
            question_count = int(request.form.get('question_count', 0))
            for i in range(1, question_count + 1):
                question_text = request.form.get(f'question_text_{i}')
                if question_text:
                    question = QuizQuestion(
                        task_id=task.id,
                        question_text=question_text,
                        question_type=request.form.get(f'question_type_{i}', 'multiple_choice'),
                        option_a=request.form.get(f'option_a_{i}'),
                        option_b=request.form.get(f'option_b_{i}'),
                        option_c=request.form.get(f'option_c_{i}'),
                        option_d=request.form.get(f'option_d_{i}'),
                        correct_answer=request.form.get(f'correct_answer_{i}'),
                        points=float(request.form.get(f'points_{i}', 1.0)),
                        question_order=i
                    )
                    db.session.add(question)
        
        db.session.commit()
        
        flash(f'Task "{title}" created and assigned to {len(interns)} intern(s) successfully!', 'success')
        return redirect(url_for('lms.tasks_list_v2'))
    
    # GET request
    interns = User.query.filter_by(role='intern', is_deleted=False).all()
    return render_template('lms/create_task_v2.html', interns=interns)

@lms_bp.route('/v2/tasks/<int:task_id>')
@login_required
def view_task_v2(task_id):
    """View task V2 details"""
    task = TaskV2.query.get_or_404(task_id)
    
    assignment = None
    if current_user.role == 'intern':
        assignment = task.get_intern_assignment(current_user.id)
        if not assignment:
            flash('You do not have permission to view this task', 'danger')
            return redirect(url_for('lms.tasks_list_v2'))
    
    return render_template('lms/view_task_v2.html', task=task, assignment=assignment)

@lms_bp.route('/v2/tasks/<int:task_id>/submit', methods=['GET', 'POST'])
@login_required
def submit_task_v2(task_id):
    """Submit task V2 (intern only)"""
    task = TaskV2.query.get_or_404(task_id)
    assignment = task.get_intern_assignment(current_user.id)
    
    if not assignment:
        flash('You do not have permission to submit this task', 'danger')
        return redirect(url_for('lms.tasks_list_v2'))
    
    # Check if task is open for submissions
    if not task.is_open:
        flash('This task is currently closed for submissions', 'warning')
        return redirect(url_for('lms.view_task_v2', task_id=task_id))
    
    if request.method == 'POST':
        if task.category == 'Quiz':
            # Handle quiz submission
            total_points = 0
            earned_points = 0
            
            for question in task.quiz_questions:
                answer_text = request.form.get(f'answer_{question.id}')
                
                # Check if correct
                is_correct = False
                if question.question_type == 'multiple_choice':
                    is_correct = answer_text == question.correct_answer
                elif question.question_type == 'true_false':
                    is_correct = answer_text == question.correct_answer
                elif question.question_type == 'short_answer':
                    # Simple keyword matching (can be improved)
                    is_correct = question.correct_answer.lower() in answer_text.lower()
                
                points = question.points if is_correct else 0
                
                quiz_answer = QuizAnswer(
                    assignment_id=assignment.id,
                    question_id=question.id,
                    answer=answer_text,
                    is_correct=is_correct,
                    points_earned=points
                )
                db.session.add(quiz_answer)
                
                total_points += question.points
                earned_points += points
            
            # Calculate grade
            grade = (earned_points / total_points * 100) if total_points > 0 else 0
            assignment.grade = grade
            assignment.status = 'completed' if grade >= task.passing_score else 'submitted'
            assignment.submitted_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Quiz submitted! Score: {grade:.1f}%', 'success')
            return redirect(url_for('lms.view_task_v2', task_id=task_id))
        else:
            # Handle regular submission
            submission_text = request.form.get('submission_text')
            
            # Handle file upload
            if 'submission_file' in request.files:
                file = request.files['submission_file']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    upload_folder = os.path.join('app', 'static', 'uploads', 'submissions')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    assignment.submission_file = filename
            
            assignment.submission_text = submission_text
            assignment.status = 'submitted'
            assignment.submitted_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Task submitted successfully!', 'success')
            return redirect(url_for('lms.tasks_list_v2'))
    
    return render_template('lms/submit_task_v2.html', task=task, assignment=assignment)

@lms_bp.route('/v2/tasks/<int:task_id>/grade/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def grade_task_v2(task_id, assignment_id):
    """Grade task V2 submission (staff only)"""
    task = TaskV2.query.get_or_404(task_id)
    assignment = TaskAssignment.query.get_or_404(assignment_id)
    
    if request.method == 'POST':
        grade = float(request.form.get('grade'))
        feedback = request.form.get('feedback')
        
        assignment.grade = grade
        assignment.feedback = feedback
        assignment.graded_by = current_user.id
        assignment.graded_at = datetime.utcnow()
        assignment.status = 'completed'
        
        db.session.commit()
        
        # Update progress
        progress = Progress.query.filter_by(intern_id=assignment.intern_id).first()
        if progress:
            progress.update_progress()
            db.session.commit()
        
        flash('Task graded successfully!', 'success')
        return redirect(url_for('lms.view_task_v2', task_id=task_id))
    
    return render_template('lms/grade_task_v2.html', task=task, assignment=assignment)

@lms_bp.route('/v2/tasks/<int:task_id>/submissions')
@login_required
@staff_required
def view_submissions(task_id):
    """View all submissions for a task (staff only)"""
    task = TaskV2.query.get_or_404(task_id)
    
    # Calculate statistics
    stats = {
        'total': len(task.assignments),
        'pending': sum(1 for a in task.assignments if a.status == 'pending'),
        'submitted': sum(1 for a in task.assignments if a.status == 'submitted'),
        'completed': sum(1 for a in task.assignments if a.status == 'completed')
    }
    
    return render_template('lms/view_submissions.html', task=task, stats=stats)

# Material Deletion Management Routes

@lms_bp.route('/materials/deletion-requests')
@login_required
@staff_required
def material_deletion_requests():
    """View material deletion requests (staff can see their own, admin sees all)"""
    if current_user.is_admin():
        requests = MaterialDeletionRequest.query.filter_by(status='pending').order_by(MaterialDeletionRequest.requested_at.desc()).all()
    else:
        requests = MaterialDeletionRequest.query.filter_by(requested_by_id=current_user.id).order_by(MaterialDeletionRequest.requested_at.desc()).all()
    
    return render_template('lms/material_deletion_requests.html', requests=requests)

@lms_bp.route('/materials/deletion-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_material_deletion(request_id):
    """Approve a material deletion request (admin only)"""
    deletion_request = MaterialDeletionRequest.query.get_or_404(request_id)
    
    if deletion_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('lms.material_deletion_requests'))
    
    review_comment = request.form.get('comment', '').strip()
    material = deletion_request.material
    
    # Create history record
    history = MaterialDeletionHistory(
        material_title=material.title,
        material_description=material.description,
        material_category=material.category,
        file_path=material.file_path,
        file_type=material.file_type,
        uploaded_by_id=material.uploaded_by,
        uploaded_at=material.uploaded_at,
        deleted_by_id=current_user.id,
        deletion_reason=deletion_request.reason
    )
    
    # Update request status
    deletion_request.status = 'approved'
    deletion_request.reviewed_by_id = current_user.id
    deletion_request.reviewed_at = datetime.utcnow()
    deletion_request.review_comment = review_comment
    
    # Delete the material
    material.is_active = False
    
    db.session.add(history)
    db.session.commit()
    
    flash('Material deletion approved and executed.', 'success')
    return redirect(url_for('lms.material_deletion_requests'))

@lms_bp.route('/materials/deletion-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_material_deletion(request_id):
    """Reject a material deletion request (admin only)"""
    deletion_request = MaterialDeletionRequest.query.get_or_404(request_id)
    
    if deletion_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('lms.material_deletion_requests'))
    
    review_comment = request.form.get('comment', '').strip()
    
    if not review_comment:
        flash('Please provide a reason for rejection.', 'error')
        return redirect(url_for('lms.material_deletion_requests'))
    
    # Update request status
    deletion_request.status = 'rejected'
    deletion_request.reviewed_by_id = current_user.id
    deletion_request.reviewed_at = datetime.utcnow()
    deletion_request.review_comment = review_comment
    
    db.session.commit()
    
    flash('Material deletion request rejected.', 'info')
    return redirect(url_for('lms.material_deletion_requests'))

@lms_bp.route('/materials/deletion-history')
@login_required
@admin_required
def material_deletion_history():
    """View history of deleted materials (admin only)"""
    history = MaterialDeletionHistory.query.order_by(MaterialDeletionHistory.deleted_at.desc()).all()
    return render_template('lms/material_deletion_history.html', history=history)

@lms_bp.route('/v2/tasks/<int:task_id>/toggle-status', methods=['POST'])
@login_required
@staff_required
def toggle_task_status(task_id):
    """Toggle task open/closed status (staff only)"""
    task = TaskV2.query.get_or_404(task_id)
    
    task.is_open = not task.is_open
    db.session.commit()
    
    status = 'opened' if task.is_open else 'closed'
    flash(f'Task {status} successfully!', 'success')
    
    return redirect(url_for('lms.view_task_v2', task_id=task_id))
