"""Dependency health checks.

Each check returns True or False. Errors are logged by type only, never with the
exception message, because driver messages can contain connection strings.
"""

import logging
from collections.abc import Callable

import httpx
import redis
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text

from app.config import Settings

logger = logging.getLogger(__name__)


def check_postgres(settings: Settings) -> bool:
    engine = create_engine(
        settings.database_url.get_secret_value(),
        connect_args={"connect_timeout": int(settings.health_timeout_s)},
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    finally:
        engine.dispose()


def check_neo4j(settings: Settings) -> bool:
    auth = (settings.neo4j_user, settings.neo4j_password.get_secret_value())
    with GraphDatabase.driver(
        settings.neo4j_uri, auth=auth, connection_timeout=settings.health_timeout_s
    ) as driver:
        driver.verify_connectivity()
    return True


def check_qdrant(settings: Settings) -> bool:
    response = httpx.get(f"{settings.qdrant_url}/readyz", timeout=settings.health_timeout_s)
    return response.status_code == 200


def check_redis(settings: Settings) -> bool:
    client = redis.Redis.from_url(
        settings.redis_url,
        socket_timeout=settings.health_timeout_s,
        socket_connect_timeout=settings.health_timeout_s,
    )
    try:
        return bool(client.ping())
    finally:
        client.close()


CHECKS: dict[str, Callable[[Settings], bool]] = {
    "postgres": check_postgres,
    "neo4j": check_neo4j,
    "qdrant": check_qdrant,
    "redis": check_redis,
}


def run_checks(settings: Settings, checks: dict[str, Callable[[Settings], bool]] = CHECKS):
    """Run every check and return {"status": "ok"|"degraded", "services": {name: "ok"|...}}."""
    services: dict[str, str] = {}
    for name, check in checks.items():
        try:
            ok = check(settings)
        except Exception as exc:  # any failure means "unavailable"
            logger.warning("health check %s failed: %s", name, type(exc).__name__)
            ok = False
        services[name] = "ok" if ok else "unavailable"
    status = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    return {"status": status, "services": services}
