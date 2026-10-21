"""GraphLens API entry point."""

from fastapi import FastAPI, Response, status

from app.config import get_settings
from app.health import run_checks

app = FastAPI(title="GraphLens API", version="0.0.1")


@app.get("/api/v1/health")
def health(response: Response) -> dict:
    """Report whether each backing service is reachable. Returns 503 if any is down."""
    result = run_checks(get_settings())
    if result["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
