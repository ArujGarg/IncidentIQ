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

    model_config = ConfigDict(from_attributes=True)
