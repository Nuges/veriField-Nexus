"""add_project_id_to_activities

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-10-09 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = 'b6c7d8e9f0a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    uuid_type = sa.String(36) if is_sqlite else postgresql.UUID(as_uuid=True)

    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('activities')]
    if 'project_id' not in cols:
        op.add_column(
            'activities',
            sa.Column('project_id', uuid_type, sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
        )
        op.create_index(
            op.f('ix_activities_project_id'),
            'activities',
            ['project_id'],
            unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('activities')]
    if 'project_id' in cols:
        op.drop_index(op.f('ix_activities_project_id'), table_name='activities')
        op.drop_column('activities', 'project_id')
