"""Errors the pipeline raises on purpose. Messages never contain secrets or full paths."""


class IngestError(Exception):
    """A single document could not be ingested. The batch continues with the next one."""
