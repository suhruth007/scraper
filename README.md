
# AI Job Scraper

A Flask-based web application that scrapes job postings and matches them against resumes using AI.

## Features

- **Resume Upload & Processing**: Upload resumes for intelligent job matching
- **Multi-Source Job Scraping**: Scrape jobs from multiple platforms (naukri.com stub included)
- **AI Job Matching**: GPT-powered resume-to-job matching with skill gap analysis
- **User Authentication**: Google OAuth login (production-ready)
- **Async Processing**: Celery-powered background tasks for long-running operations
- **Rate Limiting**: Per-user job scraping limits (100 jobs/month on free tier)
- **Encrypted Secret Storage**: Secure storage of API keys using Fernet encryption
- **Deduplication**: Prevents duplicate job scraping based on resume + query hash

## Architecture

**Tech Stack**: Flask (web) + Celery (async) + SQLAlchemy ORM + Selenium (scraping) + React (frontend)

### Core Components

- **Web Server** (`src/app/api.py`): Flask blueprints exposing REST endpoints
- **Async Tasks** (`src/app/tasks.py`): Celery workers for scraping and matching
- **Database** (`src/app/models.py`): SQLAlchemy models (User, ScrapeJob, SavedSearch)
- **Scrapers** (`src/app/scraper.py`): Selenium-based job extraction with retry logic
- **Encryption** (`src/app/utils.py`): Fernet symmetric encryption for sensitive data

### Data Flow

1. Resume uploaded → `/upload` endpoint validates & stores
2. Celery task queued with resume + search parameters
3. Deduplication via `dedup_hash`
4. Scraper extracts jobs, writes JSON to `outputs/`
5. GPT matching analyzes results
6. Results fetched via REST API

## Tools & Dependencies

- **Flask 2.3+**: Web framework
- **Celery + Redis**: Async task queue
- **SQLAlchemy + Alembic**: ORM and migrations
- **Selenium**: Web scraping automation
- **Google Auth**: OAuth 2.0 authentication
- **OpenAI**: Resume-to-job matching intelligence
- **Flask-Limiter**: Rate limiting
- **Cryptography (Fernet)**: Encryption

## Quick Start

```bash
# Setup environment
$env:FERNET_KEY = python -c "from src.app.utils import generate_fernet_key; print(generate_fernet_key())"

# Run migrations
python -m flask --app src.app db upgrade

# Start development server
python -m flask --app src.app run
```

## Docker Compose

```bash
docker-compose up  # Starts web, worker, Redis
```
