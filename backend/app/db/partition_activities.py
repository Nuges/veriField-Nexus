import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("verifield.database.partitioning")


async def setup_activities_partitioning(session: AsyncSession):
    """
    Sets up monthly partitioning for activities table.
    Renames old activities table if not partitioned, creates the partitioned parent,
    pre-creates partitions based on date range of historical records,
    and migrates old records.
    """
    try:
        # Check if activities table is already partitioned
        chk_stmt = text("""
            SELECT relkind FROM pg_class 
            WHERE relname = 'activities'
        """)
        res = await session.execute(chk_stmt)
        row = res.scalar()
        if row == "p":  # 'p' means partitioned table
            logger.info("Table 'activities' is already partitioned.")
            await create_future_partitions(session)
            return

        logger.info("Setting up activities monthly partitioning...")

        # Rename existing table to activities_old
        await session.execute(
            text("ALTER TABLE IF EXISTS activities RENAME TO activities_old")
        )

        # Query minimum date to determine when to start partition boundaries
        min_date = datetime.now(timezone.utc)
        chk_old = text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'activities_old')"
        )
        old_exists_res = await session.execute(chk_old)
        has_old = bool(old_exists_res.scalar())

        if has_old:
            try:
                min_res = await session.execute(
                    text("SELECT min(created_at) FROM activities_old")
                )
                min_val = min_res.scalar()
                if min_val:
                    min_date = min_val
                    logger.info(f"Detected historical data starting at: {min_date}")
            except Exception as e:
                logger.warning(
                    f"Could not read min(created_at) from activities_old: {e}"
                )

        # Create partitioned activities table matching model attributes
        await session.execute(text("""
            CREATE TABLE activities (
                id UUID NOT NULL,
                organization_id UUID NOT NULL,
                user_id UUID NOT NULL,
                property_id UUID,
                asset_id UUID,
                activity_type VARCHAR(50) NOT NULL,
                activity_data JSONB DEFAULT '{}'::jsonb,
                description TEXT,
                image_url VARCHAR(500),
                image_hash VARCHAR(64),
                latitude FLOAT,
                longitude FLOAT,
                gps_accuracy FLOAT,
                environment_type VARCHAR(10),
                radius_used_m FLOAT,
                duplicate_flag BOOLEAN DEFAULT false,
                override_reason TEXT,
                captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
                submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                trust_score FLOAT,
                trust_flags JSONB DEFAULT '{}'::jsonb,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                client_id VARCHAR(36),
                is_locked BOOLEAN DEFAULT false,
                evidence_payload JSONB DEFAULT '{}'::jsonb,
                PRIMARY KEY (id, organization_id, created_at)
            ) PARTITION BY RANGE (created_at)
        """))

        # Pre-create partitions starting from min_date to current month + 12 months
        await create_future_partitions(session, min_date=min_date)

        # Migrate old records from activities_old to the new partitioned activities table
        if has_old:
            logger.info("Migrating existing activities data to partitioned table...")

            # Query column names of activities_old to dynamically select existing columns
            cols_res = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'activities_old'
            """))
            existing_cols = {row[0] for row in cols_res.all()}

            # List of all destination columns expected in partitioned activities
            dest_columns = [
                "id",
                "organization_id",
                "user_id",
                "property_id",
                "asset_id",
                "activity_type",
                "activity_data",
                "description",
                "image_url",
                "image_hash",
                "latitude",
                "longitude",
                "gps_accuracy",
                "environment_type",
                "radius_used_m",
                "duplicate_flag",
                "override_reason",
                "captured_at",
                "submitted_at",
                "trust_score",
                "trust_flags",
                "status",
                "client_id",
                "created_at",
                "validation_status",
                "validation_hash",
                "is_locked",
                "evidence_payload",
            ]

            # Fallback SQL expressions for columns that might be missing in activities_old
            defaults = {
                "organization_id": "'00000000-0000-0000-0000-000000000000'::uuid",
                "asset_id": "NULL::uuid",
                "environment_type": "NULL::varchar",
                "radius_used_m": "NULL::float",
                "duplicate_flag": "false",
                "validation_status": "'pending'::varchar",
                "validation_hash": "NULL::varchar",
                "trust_score": "NULL::float",
                "trust_flags": "'{}'::jsonb",
                "client_id": "NULL::varchar",
                "evidence_payload": "'{}'::jsonb",
                "description": "NULL::text",
                "image_url": "NULL::varchar",
                "image_hash": "NULL::varchar",
                "latitude": "NULL::float",
                "longitude": "NULL::float",
                "gps_accuracy": "NULL::float",
                "submitted_at": "now()",
                "created_at": "now()",
                "status": "'pending'::varchar",
            }

            select_expressions = []
            for col in dest_columns:
                if col in existing_cols:
                    if col == "organization_id":
                        select_expressions.append(
                            "COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'::uuid)"
                        )
                    elif col == "created_at":
                        select_expressions.append("COALESCE(created_at, now())")
                    else:
                        select_expressions.append(col)
                else:
                    select_expressions.append(f"{defaults.get(col, 'NULL')} AS {col}")

            cols_str = ", ".join(dest_columns)
            select_str = ", ".join(select_expressions)

            migration_query = f"""
                INSERT INTO activities ({cols_str})
                SELECT {select_str}
                FROM activities_old
            """

            await session.execute(text(migration_query))
            logger.info("Migration completed successfully. Dropping activities_old.")
            await session.execute(text("DROP TABLE IF EXISTS activities_old CASCADE"))

        await session.commit()
    except Exception as e:
        logger.error(f"Error setting up partitioning: {e}")
        await session.rollback()


async def create_future_partitions(
    session: AsyncSession, min_date: Optional[datetime] = None
):
    """
    Creates partition tables dynamically from min_date up to 12 months in the future.
    """
    if not min_date:
        min_date = datetime.now(timezone.utc)

    start_date = min_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_limit = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=365)

    current_date = start_date
    while current_date <= end_limit:
        m_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1)

        partition_name = f"activities_y{m_start.year}m{m_start.month:02d}"

        start_str = m_start.strftime("%Y-%m-%d %H:%M:%S%z")
        end_str = m_end.strftime("%Y-%m-%d %H:%M:%S%z")

        stmt = text(f"""
            CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF activities
            FOR VALUES FROM ('{start_str}') TO ('{end_str}')
        """)
        await session.execute(stmt)
        logger.info(f"Ensured partition {partition_name} is active.")

        current_date = m_end
