from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.models import Deployment


def record_deployment(
    db: Session,
    service: str,
    previous_version: str,
    version: str,
    configuration_change: str,
) -> Deployment:
    deployment = Deployment(
        service=service,
        previous_version=previous_version,
        version=version,
        configuration_change=configuration_change,
        deployed_at=datetime.now(UTC),
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    return deployment


def get_deployments(
    db: Session,
    service: str | None = None,
) -> list[Deployment]:
    query = db.query(Deployment)

    if service is not None:
        query = query.filter(Deployment.service == service)

    return query.order_by(Deployment.deployed_at.desc()).all()
