"""
=============================================================================
VeriField Nexus — SQLAlchemy Declarative Base
=============================================================================
Base class for all ORM models. All models inherit from this base
to share metadata and enable Alembic migrations.
=============================================================================
"""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# Naming convention for constraints — ensures consistent migration names
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Declarative base class for all VeriField Nexus models.
    
    All SQLAlchemy models should inherit from this class:
        class User(Base):
            __tablename__ = "users"
            ...
    """
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
