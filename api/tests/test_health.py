"""Unit tests for the health endpoint. Real services are replaced by fake checks."""

from fastapi.testclient import TestClient

from app import health, main
from app.config import Settings


def _client_with(monkeypatch, checks):
    monkeypatch.setattr(main, "run_checks", lambda s: health.run_checks(s, checks))
    return TestClient(main.app)


def test_all_services_ok_returns_200(monkeypatch):
    checks = {name: (lambda s: True) for name in health.CHECKS}
    response = _client_with(monkeypatch, checks).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "services": {name: "ok" for name in health.CHECKS},
    }


def test_one_service_down_returns_503(monkeypatch):
    checks = {name: (lambda s: True) for name in health.CHECKS}
    checks["neo4j"] = lambda s: False
    response = _client_with(monkeypatch, checks).get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["neo4j"] == "unavailable"


def test_exception_does_not_leak_secret(monkeypatch, caplog):
    secret = "super-secret-password-123"

    def boom(settings):
        raise RuntimeError(f"could not connect with password {secret}")

    checks = {"postgres": boom}
    response = _client_with(monkeypatch, checks).get("/api/v1/health")
    assert response.status_code == 503
    assert secret not in response.text
    assert secret not in caplog.text


def test_settings_hide_passwords():
    settings = Settings(
        neo4j_password="hunter2-hidden", database_url="postgresql://u:pw-hidden@h/db"
    )
    assert "hunter2-hidden" not in repr(settings)
    assert "pw-hidden" not in repr(settings)


def test_database_url_built_from_postgres_values(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        postgres_user="u",
        postgres_password="p",
        postgres_db="d",
        postgres_port=5433,
    )
    assert settings.database_url.get_secret_value() == "postgresql+psycopg://u:p@localhost:5433/d"
