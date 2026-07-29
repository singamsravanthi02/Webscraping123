import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.domain.users.models import User, UserRole
from app.main import app


client = TestClient(app)


def _auth_headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def _create_user(db_session, role: UserRole = UserRole.STUDENT) -> User:
    user = User(
        full_name="Security Test User",
        email=f"security-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("Password123!x"),
        role=role,
        is_active=True,
        is_verified=True,
        terms_accepted=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_resume_upload_rejects_unsupported_file_type(db_session):
    user = _create_user(db_session)

    response = client.post(
        "/api/v1/users/upload/resume",
        headers=_auth_headers(user.id),
        files={"file": ("resume.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid file type"


def test_knowledge_upload_rejects_unsupported_file_type(db_session):
    user = _create_user(db_session, role=UserRole.ADMIN)

    response = client.post(
        "/api/v1/knowledge/upload",
        headers=_auth_headers(user.id),
        data={"title": "Malicious payload"},
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
