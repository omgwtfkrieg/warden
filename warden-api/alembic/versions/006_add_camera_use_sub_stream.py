"""add camera use_sub_stream

Revision ID: 006
Revises: 005
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cameras', sa.Column('use_sub_stream', sa.Boolean(), nullable=False, server_default='1'))


def downgrade():
    op.drop_column('cameras', 'use_sub_stream')
