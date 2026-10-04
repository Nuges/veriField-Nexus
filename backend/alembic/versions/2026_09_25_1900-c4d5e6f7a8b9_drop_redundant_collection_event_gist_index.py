"""Drop redundant GiST index on sample_collection_events.actual_geom

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a8
Create Date: 2026-09-25 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b2c3d4e5f6a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        indexes = [i["name"] for i in insp.get_indexes("sample_collection_events")]
        # Keep canonical idx_sample_collection_events_actual_geom and safely drop redundant idx_sample_collection_events_geom
        if "idx_sample_collection_events_geom" in indexes:
            op.execute(sa.text("DROP INDEX IF EXISTS idx_sample_collection_events_geom;"))


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_sample_collection_events_geom
            ON sample_collection_events USING gist (actual_geom);
        """))
