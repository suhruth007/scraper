# src/app/api.py
import os
import json
import logging
from flask import Blueprint, render_template, request, current_app, jsonify, send_file, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .utils import encrypt_key, decrypt_key
from .models import User, ScrapeJob
from . import db
from flask_limiter import Limiter

LOG = logging.getLogger(__name__)
bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== FLOW ROUTES ====================

@bp.route('/', methods=['GET'])
def landing():
    """Landing page - marketing and CTA"""
    return render_template('landing.html')

@bp.route('/login', methods=['GET'])
def login():
    """Login page - Google OAuth + skip option"""
    return render_template('login.html')

@bp.route('/details', methods=['GET'])
def details():
    """Job details form - collect job title, location, experience, skills, resume"""
    return render_template('details.html')

@bp.route('/analyzing/<task_id>', methods=['GET'])
def analyzing(task_id):
    """Analyzing page - real-time task progress"""
    return render_template('analyzing.html', task_id=task_id)

@bp.route('/results/<task_id>', methods=['GET'])
def results(task_id):
    """Results page - job cards with match scores and skill gaps"""
    return render_template('results.html', task_id=task_id)

# ==================== API ENDPOINTS ====================

@bp.route('/upload', methods=['POST'])
def upload_and_queue():
    """
    Upload resume and queue scraping task.
    Accepts both authenticated users and guests.
    """
    # Get or create guest user
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        # Create temporary guest user
        import uuid
        guest_session = str(uuid.uuid4())
        guest_email = f"{guest_session}@guest.local"
        user = User.query.filter_by(email=guest_email).first()
        if not user:
            user = User(email=guest_email)
            db.session.add(user)
            db.session.commit()
        user_id = user.id

    if 'resume' not in request.files:
        return jsonify({'error': 'no file'}), 400
    f = request.files['resume']
    if f.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    if not allowed_file(f.filename):
        return jsonify({'error': 'file type not allowed'}), 400

    raw = f.read()
    if len(raw) > current_app.config['MAX_CONTENT_LENGTH']:
        return jsonify({'error': 'file too large'}), 413

    # Save resume
    filename = secure_filename(f.filename)
    timestamp = int(__import__('time').time())
    filename_unique = f"{timestamp}_{filename}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_unique)
    with open(upload_path, 'wb') as fh:
        fh.write(raw)

    # Create ScrapeJob record
    job_titles = request.form.get('job_titles', 'developer')
    location = request.form.get('location', 'india')
    years_of_experience = request.form.get('years_of_experience', type=int)
    skills = request.form.get('skills', '')

    from .utils import hash_file_bytes
    dedup_hash = hash_file_bytes(raw + f"{job_titles}:{location}".encode())

    scrape_job = ScrapeJob(
        user_id=user_id,
        job_titles=job_titles,
        location=location,
        years_of_experience=years_of_experience,
        skills=skills,
        resume_filename=filename_unique,
        status='queued',
        progress=0,
        dedup_hash=dedup_hash
    )
    db.session.add(scrape_job)
    db.session.commit()

    # Queue Celery task
    from .tasks import async_scrape_and_match
    task = async_scrape_and_match.apply_async(args=[
        scrape_job.id,
        user_id,
        job_titles,
        location,
        raw,
        upload_path
    ])

    LOG.info(f"Task queued: {task.id} for ScrapeJob {scrape_job.id}")
    return jsonify({'task_id': scrape_job.id}), 202

@bp.route('/task/<int:task_id>/status', methods=['GET'])
def task_status(task_id):
    """Get task status and progress from Redis"""
    scrape_job = ScrapeJob.query.get(task_id)
    if not scrape_job:
        return jsonify({'error': 'task not found'}), 404

    return jsonify({
        'status': scrape_job.status,
        'progress': scrape_job.progress,
        'message': f'{scrape_job.status}...'
    }), 200

@bp.route('/task/<int:task_id>/results', methods=['GET'])
def task_results(task_id):
    """Get task results (jobs list)"""
    scrape_job = ScrapeJob.query.get(task_id)
    if not scrape_job:
        return jsonify({'error': 'task not found'}), 404

    if scrape_job.status != 'completed':
        return jsonify({'error': 'task not completed yet', 'status': scrape_job.status}), 202

    if scrape_job.results_path and os.path.exists(scrape_job.results_path):
        try:
            with open(scrape_job.results_path, 'r') as f:
                data = json.load(f)
                return jsonify(data), 200
        except Exception as e:
            LOG.error(f"Error reading results: {e}")
            return jsonify({'error': 'failed to read results'}), 500
    
    return jsonify({'error': 'no results'}), 404

@bp.route('/job/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """Retrieve job results file - requires authentication."""
    job = ScrapeJob.query.get_or_404(job_id)
    
    # Verify user owns this job
    if job.user_id != current_user.id:
        return jsonify({'error': 'unauthorized'}), 403
    
    if job.results_path and os.path.exists(job.results_path):
        return send_file(job.results_path, as_attachment=True)
    return jsonify({'error': 'no results'}), 404

@bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """User dashboard - requires authentication."""
    return render_template('dashboard.html', user=current_user)

@bp.route('/proxy/openai_match', methods=['POST'])
def proxy_openai_match():
    """
    Server-side OpenAI proxy for job matching.
    Can be called by authenticated or guest users.
    """
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'empty payload'}), 400
    job_id = payload.get('job_id')
    job = ScrapeJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'job_not_found'}), 404
    
    # Verify user owns this job (if authenticated)
    if current_user.is_authenticated and job.user_id != current_user.id:
        return jsonify({'error': 'unauthorized'}), 403
    
    # For now, return pending status
    # In production, query the match_jobs_with_gpt task result from Celery
    return jsonify({'status': 'pending', 'message': 'matching in progress'}), 202
