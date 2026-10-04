"""hardware_device_lifecycle_columns

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-10-03 05:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())

    with op.batch_alter_table('devices') as batch_op:
        batch_op.add_column(sa.Column('public_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('provision_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('certificate', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('heartbeat_interval', sa.Integer(), nullable=True, server_default='60'))
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('health_score', sa.Float(), nullable=False, server_default='100.0'))
        batch_op.add_column(sa.Column('battery_level', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('signal_strength', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('event_history', json_type, nullable=False, server_default=sa.text("'[]'::jsonb" if not is_sqlite else "'[]'")))


def downgrade() -> None:
    with op.batch_alter_table('devices') as batch_op:
        batch_op.drop_column('event_history')
        batch_op.drop_column('signal_strength')
        batch_op.drop_column('battery_level')
        batch_op.drop_column('health_score')
        batch_op.drop_column('last_seen_at')
        batch_op.drop_column('heartbeat_interval')
        batch_op.drop_column('certificate')
        batch_op.drop_column('provision_token')
        batch_op.drop_column('public_key')
