"""add device_commands table

Revision ID: 010
Revises: 009
Create Date: 2026-03-13
"""
import sqlalchemy as sa
from alembic import op

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'device_commands',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('app_devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('command', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_device_commands_device_id', 'device_commands', ['device_id'])


def downgrade():
    op.drop_index('ix_device_commands_device_id', 'device_commands')
    op.drop_table('device_commands')
