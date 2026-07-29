import uuid

from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.domain.users.models import User
from app.main import app


client = TestClient(app)


class BrokenRedis:
    async def incr(self, key):  # noqa: ARG002
        raise TimeoutError("redis unavailable")

    async def expire(self, key, seconds):  # noqa: ARG002
        raise TimeoutError("redis unavailable")


def test_auth_register_fails_open_when_redis_is_down(db_session, monkeypatch):
    monkeypatch.setattr("app.core.rate_limit._redis_client", BrokenRedis(), raising=False)

    email = f"ratelimit-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Rate Limit User",
            "email": email,
            "role": "student",
            "password": "Password123!x",
            "confirm_password": "Password123!x",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 201


def test_auth_login_fails_open_when_redis_is_down(db_session, monkeypatch):
    monkeypatch.setattr("app.core.rate_limit._redis_client", BrokenRedis(), raising=False)

    email = f"ratelimit-login-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        full_name="Rate Limit Login User",
        email=email,
        password_hash=get_password_hash("Password123!x"),
        is_active=True,
        is_verified=True,
        terms_accepted=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "Password123!x",
            "remember_me": False,
        },
    )

    assert response.status_code == 200

