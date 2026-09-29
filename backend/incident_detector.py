import time
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


def detect_payment_incident() -> bool:
    query = f"increase({PAYMENT_SERVICE['failure_metric']}[1m])"

    result = query_prometheus(query)

    results = result["data"]["result"]

    if not results:
        return False

    failures = float(results[0]["value"][1])

    return failures >= PAYMENT_SERVICE["failure_threshold"]


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


def create_payment_incident_if_needed(db: Session) -> Incident | None:
    service = PAYMENT_SERVICE["name"]

    if not detect_payment_incident():
        return None

    if has_open_incident(db, service):
        return None

    incident = Incident(
        severity=PAYMENT_SERVICE["severity"],
        status="open",
        affected_service=service,
        started_at=datetime.now(UTC),
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


def detect_database_incident() -> bool:
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

    return timeout_count >= DB_SERVICE["failure_threshold"]


def create_incident_if_needed(
    db: Session,
    service: str,
    severity: str,
    detected: bool,
) -> Incident | None:
    if not detected:
        return None

    if has_open_incident(db, service):
        return None

    incident = Incident(
        severity=severity,
        status="open",
        affected_service=service,
        started_at=datetime.now(UTC),
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


def create_database_incident_if_needed(db: Session) -> Incident | None:
    service = DB_SERVICE["name"]

    return create_incident_if_needed(
        db=db,
        service=service,
        severity=DB_SERVICE["severity"],
        detected=detect_database_incident(),
    )


def detect_high_latency() -> bool:
    query = (
        "rate(payment_request_duration_seconds_sum[1m]) "
        "/ "
        "rate(payment_request_duration_seconds_count[1m])"
    )

    result = query_prometheus(query)
    results = result["data"]["result"]

    if not results:
        return False

    average_latency = float(results[0]["value"][1])

    print("Average latency:", average_latency)

    return average_latency >= HIGH_LATENCY_SERVICE["threshold"]


def create_high_latency_incident_if_needed(db: Session) -> Incident | None:
    service = HIGH_LATENCY_SERVICE["name"]

    return create_incident_if_needed(
        db=db,
        service=service,
        severity=HIGH_LATENCY_SERVICE["severity"],
        detected=detect_high_latency(),
    )
