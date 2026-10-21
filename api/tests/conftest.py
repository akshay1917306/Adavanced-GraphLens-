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
