import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.domain.users.models import User
from app.core.security import get_password_hash

client = TestClient(app)

def test_login_brute_force_lockout(db_session):
    # Setup test user
    email = f"lockout-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        full_name="Lockout User",
        email=email,
        password_hash=get_password_hash("password123"),
        is_verified=True,
        is_active=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    db_session.commit()
    
    # 1. 4 failed attempts
    for _ in range(4):
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
        assert response.status_code == 401
        
    db_session.refresh(user)
    assert user.failed_login_attempts == 4
    assert not user.is_locked
    
    # 2. 5th failed attempt locks the account
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    assert response.status_code == 401
    
    db_session.refresh(user)
    assert user.is_locked
    
    # 3. Next attempt (even if correct) is forbidden
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 403
    assert "locked" in response.json()["detail"].lower()
