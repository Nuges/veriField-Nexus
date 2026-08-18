"""Add unique constraint to carbon_calculations (project_id, activity_id)

Revision ID: 7f9a1b2c3d4e
Revises: 5676a3f9d027
Create Date: 2026-08-17 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f9a1b2c3d4e'
down_revision = '5676a3f9d027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_carbon_calc_project_activity',
        'carbon_calculations',
        ['project_id', 'activity_id']
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_carbon_calc_project_activity',
        'carbon_calculations',
        type_='unique'
    )
