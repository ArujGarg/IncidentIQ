from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentCreate(BaseModel):
    severity: str
    status: str
    affected_service: str


class IncidentResponse(BaseModel):
    id: int
    severity: str
    status: str
    affected_service: str
    started_at: datetime
    ended_at: datetime | None
    trigger: str | None
    observed_value: float | None

    model_config = ConfigDict(from_attributes=True)


class DeploymentResponse(BaseModel):
    id: int
    service: str
    previous_version: str
    version: str
    configuration_change: str
    deployed_at: datetime

    model_config = ConfigDict(from_attributes=True)
