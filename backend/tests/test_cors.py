from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_local_lan_origin_is_allowed_for_auth_requests():
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://192.168.32.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://192.168.32.1:3000"


def test_private_network_preflight_is_allowed_for_local_origin():
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://192.168.32.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Private-Network": "true",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-private-network"] == "true"
    assert response.headers["access-control-allow-origin"] == "http://192.168.32.1:3000"
