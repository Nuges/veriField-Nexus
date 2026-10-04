"""agriculture_phase3b1_profile_identity_and_mass_provenance

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-10-03 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. sampling_points.soil_profile_id
    op.add_column('sampling_points', sa.Column('soil_profile_id', sa.String(length=100), nullable=True))
    op.create_index('ix_sampling_points_soil_profile_id', 'sampling_points', ['soil_profile_id'])

    # 2. physical_samples explicit profile lineage & physical core geometry
    op.add_column('physical_samples', sa.Column('soil_profile_id', sa.String(length=100), nullable=True))
    op.add_column('physical_samples', sa.Column('core_count', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('physical_samples', sa.Column('sample_dry_mass_g', sa.Numeric(10, 2), nullable=True))
    op.add_column('physical_samples', sa.Column('core_diameter_mm', sa.Numeric(6, 2), nullable=True))
    op.create_index('ix_physical_samples_soil_profile_id', 'physical_samples', ['soil_profile_id'])

    # 3. agriculture_soc_stock_results.soil_profile_id
    op.add_column('agriculture_soc_stock_results', sa.Column('soil_profile_id', sa.String(length=100), nullable=True))
    op.create_index('ix_agri_soc_stock_results_profile_id', 'agriculture_soc_stock_results', ['soil_profile_id'])

    # 4. agriculture_soc_layer_results mass provenance & physical fractions
    op.add_column('agriculture_soc_layer_results', sa.Column('soil_mass_provenance', sa.String(length=50), nullable=False, server_default='CORE_BULK_DENSITY_DERIVED'))
    op.add_column('agriculture_soc_layer_results', sa.Column('coarse_fragment_mass_g', sa.Numeric(10, 2), nullable=True))
    op.add_column('agriculture_soc_layer_results', sa.Column('fine_soil_mass_g', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('agriculture_soc_layer_results', 'fine_soil_mass_g')
    op.drop_column('agriculture_soc_layer_results', 'coarse_fragment_mass_g')
    op.drop_column('agriculture_soc_layer_results', 'soil_mass_provenance')

    op.drop_index('ix_agri_soc_stock_results_profile_id', table_name='agriculture_soc_stock_results')
    op.drop_column('agriculture_soc_stock_results', 'soil_profile_id')

    op.drop_index('ix_physical_samples_soil_profile_id', table_name='physical_samples')
    op.drop_column('physical_samples', 'core_diameter_mm')
    op.drop_column('physical_samples', 'sample_dry_mass_g')
    op.drop_column('physical_samples', 'core_count')
    op.drop_column('physical_samples', 'soil_profile_id')

    op.drop_index('ix_sampling_points_soil_profile_id', table_name='sampling_points')
    op.drop_column('sampling_points', 'soil_profile_id')
