# AI Coding Agent Instructions for AI Job Scraper

## Architecture Overview

**Stack**: Flask (web) + Celery (async) + SQLAlchemy ORM + Selenium (scraping) + React(Frontend )

**Key Components**:
- **Web Server** (`src/app/api.py`): Flask blueprints expose REST endpoints. Uses `render_template` for HTML and `jsonify` for JSON responses.
- **Async Tasks** (`src/app/tasks.py`): Celery tasks run in worker processes. `init_celery()` handles dual initialization: Flask app context (web process) vs environment variables (worker process). **Critical**: Tasks import lazily to avoid circular dependencies at module load.
- **Database** (`src/app/models.py`): SQLAlchemy models (User, ScrapeJob, SavedSearch). Migrations via Alembic in `migrations/versions/`.
- **Scrapers** (`src/app/scraper.py`): Selenium-based extraction with retry logic (`@retry` decorator from tenacity). Headless Chrome with `--no-sandbox` for containerized environments.
- **Encryption** (`src/app/utils.py`): Fernet symmetric encryption for sensitive data (OpenAI keys stored in `User.encrypted_openai_key`).

**Data Flow**:
1. Resume uploaded → `/upload` endpoint validates & stores to `uploads/` folder
2. Celery task `async_scrape_and_match()` queued with resume bytes + search params
3. Worker deduplicates via `dedup_hash` (resume + query:location), creates `ScrapeJob` record
4. Scraper extracts jobs (currently naukri.com stub), writes JSON to `outputs/`
5. Results fetched via `/job/<id>` endpoint

## Authentication & User Management

### Google OAuth Login (Recommended for Production)
Current auth is demo-only (first user in DB). To implement Google OAuth:

1. **Install package**: Add `flask-login==0.6.3` and `google-auth-oauthlib==1.1.0` to `requirements.txt`
2. **Setup Google Cloud**:
   - Create OAuth 2.0 credentials (Web Application) at console.cloud.google.com
   - Authorized redirect URIs: `http://localhost:5000/auth/google/callback` (dev), `https://yourdomain.com/auth/google/callback` (prod)
   - Store `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in environment
3. **Update User model** (`models.py`):
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    google_id = db.Column(db.String(256), unique=True, nullable=True)  # NEW
    password_hash = db.Column(db.String(256), nullable=True)
    encrypted_openai_key = db.Column(db.LargeBinary, nullable=True)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.FREE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```
4. **Implement OAuth flow** in `auth.py`:
```python
from flask_login import LoginManager, login_user, logout_user, current_user
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests

login_manager = LoginManager()
login_manager.login_view = 'auth.google_login'

@bp.route('/google_login')
def google_login():
    flow = Flow.from_client_secrets_file(
        os.getenv('GOOGLE_CLIENT_SECRETS_FILE'),
        scopes=['https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email']
    )
    flow.redirect_uri = url_for('auth.google_callback', _external=True)
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes=True)
    session['state'] = state
    return redirect(auth_url)

@bp.route('/google_callback')
def google_callback():
    flow = Flow.from_client_secrets_file(...)
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    google_request = google.auth.transport.requests.Request()
    id_info = credentials.id_token
    
    user = User.query.filter_by(google_id=id_info['sub']).first()
    if not user:
        user = User(email=id_info['email'], google_id=id_info['sub'])
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('api.home'))
```
5. **Initialize LoginManager** in `__init__.py`:
```python
from flask_login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
```
6. **Protect routes**: Use `@login_required` decorator from flask_login on `/upload` and sensitive endpoints.

## Developer Workflows

### Local Development
```bash
# Set up environment
$env:FERNET_KEY = python -c "from src.app.utils import generate_fernet_key; print(generate_fernet_key())"
python -m flask --app src.app db upgrade  # Apply migrations
python -m flask --app src.app run        # Start web on :5000
```

### Run with Docker Compose
```bash
docker-compose up  # Starts web, worker, redis
```

### Testing
- Tests live in `src/tests/`. Fixtures in `conftest.py` (currently empty—add test database setup).
- **Pattern**: Use Flask's test client for API endpoints; mock Celery tasks in unit tests.

### Database Migrations
```bash
flask db migrate -m "add google_id to User"
flask db upgrade
```
Alembic configs in `migrations/alembic.ini`; revision history in `migrations/versions/`. Always run migrations in production via deployment pipeline.

**Example migration for Google OAuth**:
```python
def upgrade():
    op.add_column('user', sa.Column('google_id', sa.String(256), nullable=True))
    op.create_unique_constraint('uq_user_google_id', 'user', ['google_id'])
```

## Critical Patterns & Conventions

### Lazy Imports (Anti-Circular Dependencies)
Celery tasks and route handlers import models/tasks inside function bodies, not at module level:
```python
# ❌ WRONG (circular import at startup)
from .tasks import async_scrape_and_match

# ✅ RIGHT (lazy import inside route)
def upload_and_queue():
    from .tasks import async_scrape_and_match
    task = async_scrape_and_match.apply_async(...)
```

### Celery Dual Initialization
`tasks.init_celery(app=None)`:
- **With Flask app**: Configures from app.config, wraps tasks in ContextTask to run inside app context.
- **Without app (worker process)**: Reads CELERY_BROKER_URL, CELERY_RESULT_BACKEND from environment.

Do NOT skip Flask context—queries and extensions fail without it.

### File Storage & Cleanup
- **Uploads**: Stored in `current_app.config['UPLOAD_FOLDER']` (default `uploads/`)
- **Results**: JSON written to `current_app.config['OUTPUT_FOLDER']` (default `outputs/`)
- **Auto-cleanup**: `auto_delete_resume` task scheduled for 7 days post-upload via `apply_async(countdown=...)`

### Encryption / Secret Handling
- Sensitive keys encrypted via `encrypt_key(plain, fernet_key)` before DB storage.
- Decryption in route: `decrypt_key(token, current_app.config['FERNET_KEY'])`
- FERNET_KEY must be generated once and stored in environment: `from src.app.utils import generate_fernet_key()`

### Configuration Management
`src/app/config.py` BaseConfig class:
- Env vars override defaults (e.g., `DATABASE_URL`, `CELERY_BROKER_URL`)
- Sensible defaults for dev: SQLite, local Redis (must exist for production)
- Limits: 5MB upload max, 100 free jobs/month (configurable)
- **Auth config** (add when implementing Google OAuth):
  - `GOOGLE_CLIENT_ID` - OAuth client ID from Google Cloud
  - `GOOGLE_CLIENT_SECRET` - OAuth client secret
  - `GOOGLE_CLIENT_SECRETS_FILE` - Path to credentials JSON file
- **OpenAI config**: `OPENAI_API_KEY` - API key for server-side job matching

## Integration Points & External Dependencies

### Redis
- Broker: `redis://redis:6379/0` (Celery task queue)
- Result backend: `redis://redis:6379/1` (task results)
- Rate limit storage: `redis://redis:6379/2` (per-user limits)

Must be running for Celery tasks (docker-compose provides it).

### Selenium / Chromedriver
Scrapers use headless Chrome. Docker image must include chromedriver (or use remote Selenium).

### Flask-Limiter
Rate limiting configured per app via `RATELIMIT_DEFAULT = "60 per minute"` (see config.py). Limiter instantiated in `__init__.py`.

### Stripe (Stub)
`STRIPE_SECRET_KEY` in config—currently unused but referenced for future billing integration.

### OpenAI (Server-Side Integration)
`/proxy/openai_match` endpoint currently returns hardcoded stub response. To implement real matching:

1. **Install OpenAI client**: Add `openai>=1.0.0` to `requirements.txt`
2. **Implement in tasks.py** (not api.py—do server-side matching):
```python
@celery.task
def match_jobs_with_gpt(job_id, jobs_json, resume_text):
    from . import db
    from .models import ScrapeJob, User
    from openai import OpenAI
    import os
    
    job = ScrapeJob.query.get(job_id)
    user = User.query.get(job.user_id)
    
    # Decrypt user's OpenAI key (if storing per-user)
    # OR use OPENAI_API_KEY from environment (recommended)
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a job matching assistant. Analyze resume vs job postings and return JSON with match scores and skill gaps."},
            {"role": "user", "content": f"Resume:\n{resume_text}\n\nJobs:\n{jobs_json}"}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content
```
3. **Update async_scrape_and_match()**: After scraping, call `match_jobs_with_gpt.apply_async()` instead of stub scoring.
4. **API endpoint** (`/proxy/openai_match`): Query completed job and return cached results instead of calling OpenAI inline.

## Common Modification Points

1. **Add new scraper**: Create function in `src/app/scraper.py` following `scrape_naukri()` pattern (retry decorator, headless driver).
2. **Add API endpoint**: Create route in `src/app/api.py` or new blueprint, register in `create_app()`.
3. **Modify task flow**: Edit `async_scrape_and_match()` in `tasks.py`; remember lazy imports for db/models.
4. **Add database field**: Update `src/app/models.py`, run `flask db migrate`, commit to `migrations/versions/`.
5. **Add scheduled task**: Create new `@celery.task` in `tasks.py`; schedule via `apply_async(countdown=...)` or Celery Beat (not yet configured).

## Testing Strategy
- API integration tests: Mock Celery with `CELERY_ALWAYS_EAGER = True` in test config.
- Unit tests for utils: Encryption/decryption, hashing functions.
- Scraper tests: Mock Selenium driver to avoid real HTTP calls.
- DB tests: Use in-memory SQLite (`sqlite:///:memory:`).
