import os
import subprocess
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def migrated_db() -> str:
    """Bring the test database (DATABASE_URL) to the latest migration and return its URL."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    subprocess.run(["alembic", "upgrade", "head"], cwd=API_DIR, check=True)  # noqa: S603, S607
    return url


class AllowAll:
    """A limiter that never limits, so ordinary tests do not need Redis."""

    def hit(self, scope, key, limit, window_seconds):
        return None

    def ensure_room(self, cap_usd):
        return None

    def record_cost(self, usd):
        return None


@pytest.fixture(autouse=True)
def no_limits():
    from app import main, ratelimit

    main.app.dependency_overrides[ratelimit.get_limiter] = lambda: AllowAll()
    yield
    main.app.dependency_overrides.pop(ratelimit.get_limiter, None)
