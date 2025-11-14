# src/app/tasks.py
"""
Celery configuration and tasks.

This version configures Celery either:
 - from a Flask app via init_celery(app), OR
 - from environment variables when run in the celery worker process.
"""
import os
import json
import logging
from celery import Celery

LOG = logging.getLogger(__name__)
celery = Celery(__name__)

def init_celery(app=None):
    """
    Configure the celery instance.

    If `app` is provided, configure from app.config and set ContextTask so
    tasks run inside the Flask application context.

    If `app` is None (running as a worker), configure the celery instance
    using environment variables (CELERY_BROKER_URL, CELERY_RESULT_BACKEND).
    """
    # Prefer Flask app config when available
    if app:
        broker = app.config.get('CELERY_BROKER_URL')
        backend = app.config.get('CELERY_RESULT_BACKEND')
        celery.conf.broker_url = broker
        celery.conf.result_backend = backend
        celery.conf.task_serializer = 'json'
        celery.conf.result_expires = app.config.get('CELERY_RESULT_EXPIRES', 3600)
        celery.conf.task_always_eager = app.config.get('CELERY_ALWAYS_EAGER', True)
        celery.conf.task_eager_propagates = True

        # Ensure tasks run with Flask app context
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return super().__call__(*args, **kwargs)
        celery.Task = ContextTask

        LOG.info("Celery initialized from Flask app config: broker=%s (eager=%s)", broker, celery.conf.task_always_eager)
        return celery

    # No app provided — configure from environment for worker processes
    broker_env = os.getenv('CELERY_BROKER_URL')
    backend_env = os.getenv('CELERY_RESULT_BACKEND')
    if broker_env:
        celery.conf.broker_url = broker_env
    if backend_env:
        celery.conf.result_backend = backend_env

    # sensible defaults if env not set
    celery.conf.task_serializer = 'json'
    celery.conf.result_expires = int(os.getenv('CELERY_RESULT_EXPIRES', '3600'))
    celery.conf.task_always_eager = os.getenv('CELERY_ALWAYS_EAGER', 'true').lower() in ('true', '1')
    celery.conf.task_eager_propagates = True

    LOG.info("Celery initialized from environment: broker=%s (eager=%s)", celery.conf.broker_url, celery.conf.task_always_eager)
    return celery


@celery.task(bind=True)
def async_scrape_and_match(self, scrape_job_id, user_id, job_titles, location, resume_bytes, resume_filename, years_of_experience=None, skills=None):
    LOG.info("Task started for scrape_job_id=%s user_id=%s job_titles=%s", scrape_job_id, user_id, job_titles)

    # Lazy imports (avoid import-time circular deps)
    from . import db
    from .models import ScrapeJob, User
    from .scraper import scrape_naukri
    from pathlib import Path

    try:
        # Fetch the ScrapeJob record (already created by API endpoint)
        job = ScrapeJob.query.get(scrape_job_id)
        if not job:
            LOG.error("ScrapeJob not found: %s", scrape_job_id)
            return {"status": "error", "job_id": scrape_job_id, "message": "scrape_job_not_found"}

        # Update progress: 25% (job started)
        job.progress = 25
        job.status = 'running'
        db.session.commit()
        LOG.info("Progress: 25%% - job started")

        # Call scraper to extract jobs from job board
        # Replace with real scrapers in production. This may call Selenium (ensure chromedriver).
        jobs = scrape_naukri(job_titles, location, max_pages=2)
        LOG.info("Scraped %d jobs for %s in %s", len(jobs), job_titles, location)

        # Update progress: 60% (scraping completed)
        job.progress = 60
        db.session.commit()
        LOG.info("Progress: 60%% - scraping completed")

        # Convert jobs to JSON for OpenAI matching
        jobs_json = json.dumps(jobs, indent=2)
        
        # Queue GPT matching task (non-blocking, runs in background)
        match_jobs_with_gpt.apply_async(args=[job.id, jobs_json, resume_bytes], countdown=1)

        # Update progress: 90% (matching queued)
        job.progress = 90
        db.session.commit()
        LOG.info("Progress: 90%% - OpenAI matching task queued")

        # Write intermediate results (unscored jobs) to output folder
        out_dir = Path(os.getenv('OUTPUT_FOLDER', 'outputs'))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"result_{job.id}.json"
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump({"jobs": jobs, "query": job_titles, "location": location}, fh, indent=2)

        job.results_path = str(out_path)
        
        # Update progress: 100% (completed)
        job.progress = 100
        job.status = 'completed'
        db.session.commit()
        LOG.info("Progress: 100%% - task completed for job %s", job.id)

        # Schedule auto-delete of uploaded resume (7 days)
        auto_delete_resume.apply_async(args=[resume_filename], countdown=3600*24*7)

        return {"status": "ok", "job_id": job.id, "jobs_count": len(jobs)}

    except Exception as exc:
        LOG.exception("Task failed: %s", exc)
        try:
            job = ScrapeJob.query.get(scrape_job_id)
            if job:
                job.status = 'failed'
                job.progress = 0
                db.session.commit()
        except Exception as db_exc:
            LOG.error("Failed to update job status on error: %s", db_exc)
        raise

@celery.task
def match_jobs_with_gpt(job_id, jobs_json):
    """
    Match jobs with resume using GPT-4 Turbo.
    Reads resume from ScrapeJob record, performs server-side analysis.
    """
    LOG.info("Starting GPT matching for job_id=%s", job_id)
    
    try:
        from . import db
        from .models import ScrapeJob, User
        from .utils import decrypt_key
        from openai import OpenAI
        from flask import current_app
        import os
        
        job = ScrapeJob.query.get(job_id)
        if not job:
            LOG.error("Job not found: %s", job_id)
            return {"status": "error", "message": "job_not_found"}
        
        user = User.query.get(job.user_id)
        if not user:
            LOG.error("User not found for job: %s", job_id)
            return {"status": "error", "message": "user_not_found"}
        
        # Get OpenAI API key from environment (recommended) or user's encrypted key
        openai_key = current_app.config.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
        
        if not openai_key and user.encrypted_openai_key:
            try:
                openai_key = decrypt_key(user.encrypted_openai_key, current_app.config['FERNET_KEY'])
            except Exception as e:
                LOG.warning("Failed to decrypt user's OpenAI key: %s", e)
        
        if not openai_key:
            LOG.error("No OpenAI API key available for user %s", user.id)
            return {"status": "error", "message": "no_openai_key"}
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_key)
        
        # Call GPT-4 for job matching
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a job matching assistant. Analyze the provided resume against job postings. "
                              "For each job, provide a match score (0-100), top 3 matching skills, and top 3 skill gaps. "
                              "Return the response as valid JSON with array of {title, score, matching_skills, skill_gaps}."
                },
                {
                    "role": "user",
                    "content": f"Please analyze these job postings:\n\n{jobs_json}"
                }
            ],
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            match_results = json.loads(result_text)
        except json.JSONDecodeError:
            # If not valid JSON, store as string for manual review
            match_results = {"raw_response": result_text}
        
        LOG.info("GPT matching completed for job_id=%s", job_id)
        return {"status": "ok", "job_id": job_id, "results": match_results}
        
    except Exception as e:
        LOG.exception("Error in match_jobs_with_gpt: %s", e)
        return {"status": "error", "message": str(e)}

@celery.task
def auto_delete_resume(filename):
    from pathlib import Path
    try:
        p = Path(filename)
        if p.exists():
            p.unlink()
            return True
    except Exception as e:
        LOG.exception("Failed to delete resume %s: %s", filename, e)
    return False
