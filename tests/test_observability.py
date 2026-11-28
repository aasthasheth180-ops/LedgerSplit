
import json
import logging
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core import observability


SENSITIVE_VALUE = "synthetic-sensitive-test-value"


class TestPayload(BaseModel):
    amount: int


@pytest.fixture
def monitored_client():
    app = FastAPI()
    observability.install_observability(app)

    @app.get("/test/success")
    def success():
        return {"status": "ok"}

    @app.get("/test/failure")
    def failure():
        raise RuntimeError(SENSITIVE_VALUE)

    @app.post("/test/validate")
    def validate(payload: TestPayload):
        return payload

    with TestClient(app) as client:
        yield client


def test_liveness(monitored_client):
    response = monitored_client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_success(monitored_client, monkeypatch):
    session_factory = MagicMock()
    monkeypatch.setattr(
        observability, "SessionLocal", session_factory
    )

    response = monitored_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

    session = session_factory.return_value.__enter__.return_value
    session.execute.assert_called_once()
    assert str(session.execute.call_args.args[0]) == "SELECT 1"


def test_readiness_failure_and_recovery(
    monitored_client, monkeypatch
):
    session_factory = MagicMock()
    session = session_factory.return_value.__enter__.return_value

    session.execute.side_effect = RuntimeError(SENSITIVE_VALUE)

    monkeypatch.setattr(
        observability, "SessionLocal", session_factory
    )

    response = monitored_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert SENSITIVE_VALUE not in response.text

    live = monitored_client.get("/health/live")
    assert live.status_code == 200

    session.execute.side_effect = None

    recovered = monitored_client.get("/health/ready")

    assert recovered.status_code == 200
    assert recovered.json() == {"status": "ready"}


def test_unique_request_ids(monitored_client):
    first = monitored_client.get("/test/success")
    second = monitored_client.get("/test/success")

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]

    assert UUID(first_id).hex == first_id
    assert UUID(second_id).hex == second_id
    assert first_id != second_id


def test_security_response_header(monitored_client):
    response = monitored_client.get("/test/success")

    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_validation_error_is_sanitized(monitored_client):
    response = monitored_client.post(
        "/test/validate",
        json={"amount": SENSITIVE_VALUE},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Invalid request data"
    }
    assert SENSITIVE_VALUE not in response.text
    assert response.headers.get("X-Request-ID")


def test_internal_error_is_sanitized(monitored_client):
    response = monitored_client.get("/test/failure")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error"
    }
    assert SENSITIVE_VALUE not in response.text
    assert response.headers.get("X-Request-ID")


def test_structured_request_logging(monitored_client, caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = monitored_client.get("/test/success")

    request_id = response.headers["X-Request-ID"]

    entries = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "uvicorn.error"
        and record.getMessage().startswith("{")
    ]

    matching = [
        entry for entry in entries
        if entry.get("request_id") == request_id
        and "status" in entry
    ]

    assert len(matching) == 1

    entry = matching[0]

    assert entry["method"] == "GET"
    assert entry["status"] == 200
    assert entry["duration_ms"] >= 0


def test_sensitive_data_not_logged(monitored_client, caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = monitored_client.get(
            "/test/failure",
            params={"secret": SENSITIVE_VALUE},
            headers={
                "Authorization": f"Bearer {SENSITIVE_VALUE}"
            },
        )

    assert response.status_code == 500
    assert SENSITIVE_VALUE not in caplog.text

    entries = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "uvicorn.error"
        and record.getMessage().startswith("{")
    ]

    errors = [
        entry for entry in entries
        if entry.get("error_type") == "RuntimeError"
    ]

    assert len(errors) == 1
    assert errors[0]["request_id"] == response.headers["X-Request-ID"]


def test_request_and_error_metrics(monitored_client):
    monitored_client.get("/test/success")
    monitored_client.get("/test/success")
    monitored_client.get("/test/failure")

    response = monitored_client.get("/metrics")

    assert response.status_code == 200

    metrics = response.json()

    assert metrics["requests"] == 3
    assert metrics["errors"] == 1
    assert metrics["mean_latency_ms"] >= 0
    assert metrics["error_rate"] == pytest.approx(1 / 3)


def test_client_errors_not_counted_as_server_errors(
    monitored_client
):
    monitored_client.post(
        "/test/validate",
        json={"amount": "invalid"},
    )

    metrics = monitored_client.get("/metrics").json()

    assert metrics["requests"] == 1
    assert metrics["errors"] == 0
    assert metrics["error_rate"] == 0
