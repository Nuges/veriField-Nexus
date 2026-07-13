from uuid import UUID

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.domains.authentication.models import User
from app.main import app


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def admin_token_headers(db_session: AsyncSession):
    # This is a dummy token for tests. In a real app, it would generate a JWT token.
    # The application's get_current_user dependency must be mocked/overridden in app.main or we return a valid auth payload.
    # Actually, for standard FastAPI Dependency injection testing, we can override the dependency on the app:
    from app.core.security import get_current_user

    async def override_get_current_user():
        user = User(
            id=UUID("00000000-0000-5000-a000-000000000000"),
            email="superadmin@verifield.io",
            full_name="Super Admin",
            role="SUPER_ADMIN",
            status="active",
        )
        await db_session.merge(user)
        await db_session.commit()
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield {"Authorization": "Bearer TEST_TOKEN"}

    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis():
    from app.core.redis import close_redis

    yield
    await close_redis()
