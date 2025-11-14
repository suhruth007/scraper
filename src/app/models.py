from . import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
import enum

class RoleEnum(enum.Enum):
    FREE = 'free'
    PRO = 'pro'
    ADMIN = 'admin'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    google_id = db.Column(db.String(256), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    encrypted_openai_key = db.Column(db.LargeBinary, nullable=True)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.FREE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    years_of_experience = db.Column(db.Integer, nullable=True)
    preferred_skills = db.Column(db.String(512), nullable=True)  # CSV list

class SavedSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    query = db.Column(db.String(256))
    location = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ScrapeJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    job_titles = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(128), nullable=True)
    years_of_experience = db.Column(db.Integer, nullable=True)
    skills = db.Column(db.String(512), nullable=True)  # CSV list
    resume_filename = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(32), default='queued')  # queued, running, completed, failed
    progress = db.Column(db.Integer, default=0)  # 0-100
    results_path = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dedup_hash = db.Column(db.String(128), nullable=True)
