"""Add cross verification tables

Revision ID: 5a371e075f07
Revises: f62f35c738f2
Create Date: 2026-05-01 07:29:31.089792

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5a371e075f07'
down_revision = 'f62f35c738f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sensor_readings table
    op.create_table('sensor_readings',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('asset_id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('usage_flag', sa.Boolean(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['properties.id'], name='fk_sensor_readings_asset_id_properties'),
        sa.PrimaryKeyConstraint('id', name='pk_sensor_readings'),
    )
    op.create_index('ix_sensor_readings_asset_id', 'sensor_readings', ['asset_id'])

    # Create community_validations table
    op.create_table('community_validations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('asset_id', sa.UUID(), nullable=False),
        sa.Column('validator_id', sa.UUID(), nullable=False),
        sa.Column('response', sa.String(10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['properties.id'], name='fk_community_validations_asset_id_properties'),
        sa.ForeignKeyConstraint(['validator_id'], ['users.id'], name='fk_community_validations_validator_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_community_validations'),
    )
    op.create_index('ix_community_validations_asset_id', 'community_validations', ['asset_id'])
    op.create_index('ix_community_validations_validator_id', 'community_validations', ['validator_id'])

    # Create audit_tasks table
    op.create_table('audit_tasks',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('asset_id', sa.UUID(), nullable=False),
        sa.Column('assigned_agent', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['properties.id'], name='fk_audit_tasks_asset_id_properties'),
        sa.ForeignKeyConstraint(['assigned_agent'], ['users.id'], name='fk_audit_tasks_assigned_agent_users'),
        sa.PrimaryKeyConstraint('id', name='pk_audit_tasks'),
    )
    op.create_index('ix_audit_tasks_asset_id', 'audit_tasks', ['asset_id'])
    op.create_index('ix_audit_tasks_assigned_agent', 'audit_tasks', ['assigned_agent'])


def downgrade() -> None:
    op.drop_table('audit_tasks')
    op.drop_table('community_validations')
    op.drop_table('sensor_readings')
