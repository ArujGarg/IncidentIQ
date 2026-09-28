from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.models import Incident
from backend.prometheus import query_prometheus

PAYMENT_SERVICE = {
    "name": "payment_service",
    "failure_metric": "payment_failures_total",
    "failure_threshold": 3,
    "severity": "critical",
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
