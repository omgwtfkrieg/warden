"""add device hardware_id and device_model

Revision ID: 008
Revises: 007
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('app_devices', sa.Column('device_model', sa.String(255), nullable=True))
    op.add_column('app_devices', sa.Column('hardware_id', sa.String(255), nullable=True))
    op.create_index('ix_app_devices_hardware_id', 'app_devices', ['hardware_id'])

    op.add_column('pairing_codes', sa.Column('hardware_id', sa.String(255), nullable=True))
    op.add_column('pairing_codes', sa.Column('device_model', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('pairing_codes', 'device_model')
    op.drop_column('pairing_codes', 'hardware_id')

    op.drop_index('ix_app_devices_hardware_id', table_name='app_devices')
    op.drop_column('app_devices', 'hardware_id')
    op.drop_column('app_devices', 'device_model')
