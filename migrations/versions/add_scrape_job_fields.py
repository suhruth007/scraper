"""Add job details and progress tracking to ScrapeJob and User

Revision ID: add_scrape_job_fields
Revises: add_google_id_1
Create Date: 2025-11-13 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_scrape_job_fields'
down_revision = 'add_google_id_1'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to scrape_job table
    with op.batch_alter_table('scrape_job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('job_titles', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('location', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('years_of_experience', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('skills', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('resume_filename', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('progress', sa.Integer(), nullable=True, server_default='0'))

    # Add new columns to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('years_of_experience', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('preferred_skills', sa.String(length=512), nullable=True))


def downgrade():
    # Remove columns from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('preferred_skills')
        batch_op.drop_column('years_of_experience')

    # Remove columns from scrape_job table
    with op.batch_alter_table('scrape_job', schema=None) as batch_op:
        batch_op.drop_column('progress')
        batch_op.drop_column('resume_filename')
        batch_op.drop_column('skills')
        batch_op.drop_column('years_of_experience')
        batch_op.drop_column('location')
        batch_op.drop_column('job_titles')
