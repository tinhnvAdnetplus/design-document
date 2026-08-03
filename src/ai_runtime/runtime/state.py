"""Pure feature projection used for status and restart recovery."""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Mapping
from typing import Any


class FeaturePhase(enum.StrEnum):
    NEW = "NEW"
    REQUESTED = "REQUESTED"
    PLAN_READY = "PLAN_READY"
    PLAN_APPROVED = "PLAN_APPROVED"
    IMPLEMENTING = "IMPLEMENTING"
    IMPLEMENTATION_READY = "IMPLEMENTATION_READY"
    REVIEWING = "REVIEWING"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    MERGING = "MERGING"
    COMPLETED = "COMPLETED"


@dataclasses.dataclass(frozen=True, slots=True)
class FeatureState:
    feature_id: str
    phase: FeaturePhase = FeaturePhase.NEW
    sequence: int = 0
    correlation_id: str | None = None
    last_event_id: str | None = None
    request: Mapping[str, Any] | None = None
    plan: Mapping[str, Any] | None = None
    workspace: Mapping[str, Any] | None = None
    implementation: Mapping[str, Any] | None = None
    review: Mapping[str, Any] | None = None
    approval: Mapping[str, Any] | None = None
    merge: Mapping[str, Any] | None = None


def project_feature(state: FeatureState, event: Mapping[str, Any]) -> FeatureState:
    """Project one event without invoking an adapter or touching Git."""
    aggregate = event["aggregate"]
    if aggregate["feature_id"] != state.feature_id:
        return state
    event_type = event["type"]
    payload = event["payload"]
    values: dict[str, Any] = {
        "sequence": aggregate["sequence"],
        "correlation_id": event["correlation_id"],
        "last_event_id": event["event_id"],
    }
    if event_type == "feature.requested":
        values.update(phase=FeaturePhase.REQUESTED, request=payload)
    elif event_type == "plan.ready":
        values.update(phase=FeaturePhase.PLAN_READY, plan=payload)
    elif event_type == "plan.approved":
        values.update(phase=FeaturePhase.PLAN_APPROVED)
    elif event_type == "lease.granted":
        values.update(phase=FeaturePhase.IMPLEMENTING, workspace=payload)
    elif event_type == "implementation.ready":
        values.update(phase=FeaturePhase.IMPLEMENTATION_READY, implementation=payload)
    elif event_type == "review.requested":
        values.update(phase=FeaturePhase.REVIEWING)
    elif event_type == "changes.requested":
        values.update(phase=FeaturePhase.CHANGES_REQUESTED, review=payload)
    elif event_type == "implementation.progress" and payload.get("stage") == "review.recommendation":
        values.update(phase=FeaturePhase.AWAITING_HUMAN_APPROVAL, review=payload)
    elif event_type == "merge.approved":
        values.update(phase=FeaturePhase.APPROVED, approval=payload)
    elif event_type == "merge.started":
        values.update(phase=FeaturePhase.MERGING)
    elif event_type == "merge.completed":
        values.update(phase=FeaturePhase.COMPLETED, merge=payload)
    return dataclasses.replace(state, **values)
