"""add sub_rtsp_url and stream_metadata to cameras

Revision ID: 004
Revises: 003
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cameras', sa.Column('sub_rtsp_url', sa.String(512), nullable=True))
    op.add_column('cameras', sa.Column('stream_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('cameras', 'stream_metadata')
    op.drop_column('cameras', 'sub_rtsp_url')
