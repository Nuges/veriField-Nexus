"""
=============================================================================
VeriField Nexus — SQLAlchemy Declarative Base
=============================================================================
Base class for all ORM models. All models inherit from this base
to share metadata and enable Alembic migrations.
=============================================================================
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

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

# Import all models here to ensure they are registered with SQLAlchemy's Base.metadata
from app.domains.organizations.models import *
from app.domains.reporting.models import *
from app.domains.ledger.models import *
from app.domains.evidence.models import *
from app.domains.compliance_engine.models import *
from app.domains.projects.models import *
from app.domains.marketplace.models import *
from app.domains.jurisdictions.models import *
from app.domains.workspaces.models import *
from app.domains.ai_trust_engine.models import *
from app.domains.verification.models import *
from app.domains.activities.models import *
from app.domains.programmes.models import *
from app.domains.finance.models import *
from app.domains.registry_integrations.models import *
from app.domains.assets.models import *
from app.domains.authentication.models import *
from app.domains.notifications.models import *
from app.domains.methodologies.models.base_registry import *
from app.domains.hardware.models import *
from app.domains.digital_twins.models import *
