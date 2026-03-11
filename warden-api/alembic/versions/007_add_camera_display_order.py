"""add camera display_order

Revision ID: 007
Revises: 006
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cameras', sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('cameras', 'display_order')
