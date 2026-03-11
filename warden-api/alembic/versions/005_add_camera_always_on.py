"""add camera always_on

Revision ID: 005
Revises: 004
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cameras', sa.Column('always_on', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('cameras', 'always_on')
