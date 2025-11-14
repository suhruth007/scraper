import os
import json
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from .models import User
from . import db
from .utils import encrypt_key

LOG = logging.getLogger(__name__)
bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/google_login')
def google_login():
    """Initiate Google OAuth login flow."""
    secrets_file = current_app.config.get('GOOGLE_CLIENT_SECRETS_FILE')
    if not secrets_file or not os.path.exists(secrets_file):
        LOG.error("Google Client Secrets file not found: %s", secrets_file)
        return redirect(url_for('api.home'))
    
    try:
        flow = Flow.from_client_secrets_file(
            secrets_file,
            scopes=[
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
        )
        flow.redirect_uri = url_for('auth.google_callback', _external=True)
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes=True
        )
        session['state'] = state
        return redirect(auth_url)
    except Exception as e:
        LOG.exception("Error initiating Google OAuth: %s", e)
        return redirect(url_for('api.landing'))

@bp.route('/google_callback')
def google_callback():
    """Handle Google OAuth callback."""
    state = session.get('state')
    if not state:
        LOG.warning("State mismatch in OAuth callback")
        return redirect(url_for('api.landing'))
    
    secrets_file = current_app.config.get('GOOGLE_CLIENT_SECRETS_FILE')
    if not secrets_file or not os.path.exists(secrets_file):
        LOG.error("Google Client Secrets file not found: %s", secrets_file)
        return redirect(url_for('api.home'))
    
    try:
        flow = Flow.from_client_secrets_file(
            secrets_file,
            scopes=[
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
        )
        flow.redirect_uri = url_for('auth.google_callback', _external=True)
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Get user info from ID token
        google_request = google.auth.transport.requests.Request()
        id_info = credentials.id_token
        
        google_id = id_info.get('sub')
        email = id_info.get('email')
        
        # Find or create user
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User(email=email, google_id=google_id)
            db.session.add(user)
            db.session.commit()
            LOG.info("New user created via Google OAuth: %s", email)
        
        login_user(user)
        return redirect(url_for('api.dashboard') if hasattr(current_app, 'dashboard') else url_for('api.landing'))
    except Exception as e:
        LOG.exception("Error in Google OAuth callback: %s", e)
        return redirect(url_for('api.landing'))

@bp.route('/logout')
@login_required
def logout():
    """Logout current user."""
    logout_user()
    return redirect(url_for('api.landing'))

@bp.route('/save_key', methods=['POST'])
@login_required
def save_key():
    """Save OpenAI API key for current user."""
    api_key = request.form.get('openai_key')
    if not api_key:
        return redirect(url_for('api.landing'))
    
    user = current_user
    if user:
        token = encrypt_key(api_key, current_app.config['FERNET_KEY'])
        user.encrypted_openai_key = token
        db.session.commit()
        LOG.info("OpenAI key saved for user %s", user.id)
    
    return redirect(url_for('api.dashboard') if hasattr(current_app, 'dashboard') else url_for('api.landing'))
