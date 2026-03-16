"""add platform to app_devices and pairing_codes

Revision ID: 009
Revises: 008
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pairing_codes', sa.Column('platform', sa.String(20), nullable=True))
    op.add_column('app_devices', sa.Column('platform', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('pairing_codes', 'platform')
    op.drop_column('app_devices', 'platform')
