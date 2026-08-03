"""Helpers for producing integrity-bound runtime event envelopes."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Mapping
from typing import Any

from .store.event_store import PROTOCOL_VERSION, content_sha256


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def new_event(
    *,
    event_type: str,
    feature_id: str,
    sequence: int,
    producer: Mapping[str, str],
    payload: Mapping[str, Any],
    correlation_id: str,
    causation_id: str | None,
    policy_revision: str,
    idempotency_key: str,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build a canonical v1 event and calculate its content digest."""
    event: dict[str, Any] = {
        "event_id": event_id or f"evt-{uuid.uuid4().hex}",
        "protocol": PROTOCOL_VERSION,
        "type": event_type,
        "occurred_at": utc_now(),
        "producer": dict(producer),
        "aggregate": {
            "feature_id": feature_id,
            "stream": f"feature/{feature_id}",
            "sequence": sequence,
        },
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "idempotency_key": idempotency_key,
        "policy_revision": policy_revision,
        "payload": dict(payload),
        "attachments": [],
    }
    event["integrity"] = {
        "content_sha256": content_sha256(event),
        "signature_ref": None,
    }
    return event
