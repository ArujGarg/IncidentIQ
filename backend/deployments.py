from datetime import UTC, datetime
from uuid import uuid4

deployments = []


def record_deployment(
    service: str,
    previous_version: str,
    version: str,
    configuration_change: str,
):
    deployment = {
        "deployment_id": str(uuid4()),
        "service": service,
        "previous_version": previous_version,
        "version": version,
        "configuration_change": configuration_change,
        "timestamp": datetime.now(UTC),
    }

    deployments.append(deployment)

    return deployment


def get_deployments(
    service: str | None = None,
):
    if service is None:
        return deployments

    return [
        deployment for deployment in deployments if deployment["service"] == service
    ]
