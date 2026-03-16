"""add last_seen_at to app_devices

Revision ID: 011
Revises: 010
Create Date: 2026-03-13
"""
import sqlalchemy as sa
from alembic import op

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('app_devices', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('app_devices', 'last_seen_at')
