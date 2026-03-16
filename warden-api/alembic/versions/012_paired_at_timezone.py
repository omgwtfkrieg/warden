"""make paired_at timezone-aware

Revision ID: 012
Revises: 011
Create Date: 2026-03-16
"""
import sqlalchemy as sa
from alembic import op

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite: column type affinity doesn't change storage format, but this
    # ensures SQLAlchemy processes timezone-aware datetimes consistently.
    # For Postgres migration readiness: TIMESTAMP -> TIMESTAMP WITH TIME ZONE.
    with op.batch_alter_table('app_devices') as batch_op:
        batch_op.alter_column(
            'paired_at',
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table('app_devices') as batch_op:
        batch_op.alter_column(
            'paired_at',
            type_=sa.DateTime(timezone=False),
            existing_nullable=False,
        )
