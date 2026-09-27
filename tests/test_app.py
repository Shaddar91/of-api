import pytest

from app import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_hello(client):
    response = client.get("/api/v1/hello")
    assert response.status_code == 200
    assert response.get_json() == {"message": "hello"}
