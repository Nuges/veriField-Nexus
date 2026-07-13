import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import jwt as pyjwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.event_bus import EventBus
from app.core.security import get_password_hash, verify_password
from app.domains.authentication.models import User
from app.domains.authentication.repository import UserRepository
from app.domains.authentication.schemas import UserCreate, UserLogin


class AuthenticationService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def authenticate(self, credentials: UserLogin) -> User:
        """Verifies credentials and returns user model."""
        if credentials.email:
            user = await self.repository.get_by_email(credentials.email)
        elif credentials.phone:
            user = await self.repository.get_by_phone(credentials.phone)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone must be provided for login.",
            )

        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Please verify and try again.",
            )

        if not user.is_active or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or blocked.",
            )

        return user

    def generate_token(self, user: User) -> str:
        """Generates a local JWT access token."""
        secret = settings.jwt_secret or "verifield-dev-secret-key"
        expires_delta = timedelta(hours=24)
        expire = datetime.now(timezone.utc) + expires_delta

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "organization_id": (
                str(user.organization_id) if user.organization_id else None
            ),
            "exp": expire,
        }
        return pyjwt.encode(payload, secret, algorithm="HS256")

    async def create_user(self, data: UserCreate, actor_id: str) -> User:
        """Creates a new user and emits domain event."""
        # Check if exists
        if data.email:
            existing = await self.repository.get_by_email(data.email)
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=data.email,
            phone=data.phone,
            full_name=data.full_name,
            role=data.role,
            organization_id=data.organization_id,
            organization=data.organization,
            country=data.country,
            password_hash=get_password_hash(data.password) if data.password else None,
            requires_password_change=True if not data.password else False,
            meta_data=data.meta_data or {},
        )

        user = await self.repository.create(user)

        # Publish event
        await EventBus.publish(
            stream_name="identity_events",
            event_type="UserCreated",
            payload={"user_id": str(user.id), "email": user.email, "role": user.role},
            actor_id=actor_id,
        )

        return user

    async def update_user(
        self, user_id: uuid.UUID, updates: Dict[str, Any], actor_id: str
    ) -> User:
        """Updates user with optimistic concurrency and emits event."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        old_state = {"role": user.role, "status": user.status}

        for key, value in updates.items():
            if hasattr(user, key) and key not in [
                "id",
                "version",
                "created_at",
                "updated_at",
            ]:
                setattr(user, key, value)

        user = await self.repository.update(user)

        await EventBus.publish(
            stream_name="identity_events",
            event_type="UserUpdated",
            payload={
                "user_id": str(user.id),
                "updates": updates,
                "old_state": old_state,
            },
            actor_id=actor_id,
        )

        return user

    async def delete_user(self, user_id: uuid.UUID, actor_id: str) -> User:
        """Soft deletes a user."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user = await self.repository.soft_delete(user)

        await EventBus.publish(
            stream_name="identity_events",
            event_type="UserDeleted",
            payload={"user_id": str(user.id)},
            actor_id=actor_id,
        )

        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def list_users(
        self, organization_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> List[User]:
        return await self.repository.list_by_organization(
            organization_id, limit, offset
        )
