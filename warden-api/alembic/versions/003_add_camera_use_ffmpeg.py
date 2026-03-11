"""add camera use_ffmpeg flag

Revision ID: 003
Revises: 002
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cameras', sa.Column('use_ffmpeg', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('cameras', 'use_ffmpeg')
