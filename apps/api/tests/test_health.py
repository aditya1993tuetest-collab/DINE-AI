from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from restaurant_recommender.config import Settings
from restaurant_recommender.main import create_app


def test_liveness_does_not_require_dependencies() -> None:
    client = TestClient(create_app(Settings(app_env="test")))

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "restaurant-recommendation-api",
        "version": "0.5.0",
    }


def test_phase_five_readiness_reports_unavailable_dependency() -> None:
    client = TestClient(
        create_app(
            Settings(app_env="test"),
            engine=create_engine(
                "sqlite+pysqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            ),
        )
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["phase"] == 5
    assert response.json()["activeDataset"] is False
    assert response.json()["redis"] == "not_required"
    assert response.json()["llm"] == "degraded"


def test_cors_allows_only_configured_web_origin() -> None:
    settings = Settings(
        app_env="test",
        web_origin="https://web.example,https://preview.example",
    )
    client = TestClient(create_app(settings))

    response = client.options(
        "/health/live",
        headers={
            "Origin": "https://web.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://web.example"


def test_security_headers_and_request_body_limit() -> None:
    settings = Settings(app_env="test", max_request_body_bytes=1024)
    client = TestClient(create_app(settings))
    health = client.get("/health/live")
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"

    response = client.post(
        "/api/v1/recommendations",
        content=b"x" * 1025,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
