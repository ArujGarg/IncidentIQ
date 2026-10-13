import time
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.loki import query_loki
from backend.models import Incident
from backend.prometheus import query_prometheus

PAYMENT_SERVICE = {
    "name": "payment_service",
    "failure_metric": "payment_failures_total",
    "failure_threshold": 3,
    "severity": "critical",
}

DB_SERVICE = {
    "name": "payment_service",
    "error_message": "database connection timeout",
    "failure_threshold": 3,
    "severity": "critical",
}

HIGH_LATENCY_SERVICE = {
    "name": "payment_service",
    "threshold": 1.0,
    "severity": "warning",
}

INVENTORY_DEPENDENCY = {
    "name": "inventory_service",
    "failure_metric": "inventory_dependency_failures_total",
    "failure_threshold": 3,
    "severity": "critical",
}


@dataclass
class Detection:
    fired: bool
    value: float | None = None


def detect_payment_incident() -> Detection:
    query = f"sum(increase({PAYMENT_SERVICE['failure_metric']}[1m]))"

    result = query_prometheus(query)

    results = result["data"]["result"]

    if not results:
        return Detection(fired=False)

    failures = float(results[0]["value"][1])

    return Detection(
        fired=failures >= PAYMENT_SERVICE["failure_threshold"],
        value=failures,
    )


def has_open_incident(db: Session, service: str) -> bool:
    incident = (
        db.query(Incident)
        .filter(
            Incident.affected_service == service,
            Incident.status == "open",
        )
        .first()
    )

    return incident is not None


def detect_database_incident() -> Detection:
    query = (
        f'{{service_name="{DB_SERVICE["name"]}"}} |= "{DB_SERVICE["error_message"]}"'
    )

    end = time.time_ns()
    start = end - 60 * 1_000_000_000

    result = query_loki(
        query,
        start=start,
        end=end,
    )

    streams = result["data"]["result"]

    timeout_count = sum(len(stream["values"]) for stream in streams)

    print("DB timeouts detected:", timeout_count)

    return Detection(
        fired=timeout_count >= DB_SERVICE["failure_threshold"],
        value=float(timeout_count),
    )


def create_incident_if_needed(
    db: Session,
    service: str,
    severity: str,
    trigger: str,
    detection: Detection,
) -> Incident | None:
    if not detection.fired:
        return None

    if has_open_incident(db, service):
        return None

    incident = Incident(
        severity=severity,
        status="open",
        affected_service=service,
        started_at=datetime.now(UTC),
        trigger=trigger,
        observed_value=detection.value,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


def create_payment_incident_if_needed(db: Session) -> Incident | None:
    return create_incident_if_needed(
        db=db,
        service=PAYMENT_SERVICE["name"],
        severity=PAYMENT_SERVICE["severity"],
        trigger="payment_failures",
        detection=detect_payment_incident(),
    )


def create_database_incident_if_needed(db: Session) -> Incident | None:
    return create_incident_if_needed(
        db=db,
        service=DB_SERVICE["name"],
        severity=DB_SERVICE["severity"],
        trigger="db_timeouts",
        detection=detect_database_incident(),
    )


def detect_high_latency() -> Detection:
    query = (
        "sum(rate(payment_request_duration_seconds_sum[1m])) "
        "/ "
        "sum(rate(payment_request_duration_seconds_count[1m]))"
    )

    result = query_prometheus(query)
    results = result["data"]["result"]

    if not results:
        return Detection(fired=False)

    average_latency = float(results[0]["value"][1])

    print("Average latency:", average_latency)

    return Detection(
        fired=average_latency >= HIGH_LATENCY_SERVICE["threshold"],
        value=average_latency,
    )


def create_high_latency_incident_if_needed(db: Session) -> Incident | None:
    return create_incident_if_needed(
        db=db,
        service=HIGH_LATENCY_SERVICE["name"],
        severity=HIGH_LATENCY_SERVICE["severity"],
        trigger="high_latency",
        detection=detect_high_latency(),
    )


def detect_inventory_dependency_incident() -> Detection:
    query = f"sum(increase({INVENTORY_DEPENDENCY['failure_metric']}[1m]))"

    result = query_prometheus(query)
    results = result["data"]["result"]

    if not results:
        return Detection(fired=False)

    failures = float(results[0]["value"][1])

    print("Inventory dependency failures:", failures)

    return Detection(
        fired=failures >= INVENTORY_DEPENDENCY["failure_threshold"],
        value=failures,
    )


def create_inventory_dependency_incident_if_needed(
    db: Session,
) -> Incident | None:
    return create_incident_if_needed(
        db=db,
        service=INVENTORY_DEPENDENCY["name"],
        severity=INVENTORY_DEPENDENCY["severity"],
        trigger="inventory_dependency_failures",
        detection=detect_inventory_dependency_incident(),
    )
