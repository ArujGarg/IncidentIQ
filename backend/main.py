import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from backend.database import SessionLocal, get_db
from backend.incident_detector import (
    create_database_incident_if_needed,
    create_high_latency_incident_if_needed,
    create_payment_incident_if_needed,
)
from backend.models import Incident
from backend.schemas import IncidentCreate, IncidentResponse


def run_detector_check():
    db = SessionLocal()
    try:
        payment_incident = create_payment_incident_if_needed(db)
        database_incident = create_database_incident_if_needed(db)
        latency_incident = create_high_latency_incident_if_needed(db)

        print("Payment detector:", payment_incident)
        print("Database detector:", database_incident)
        print("Latency detector:", latency_incident)
    finally:
        db.close()


async def detector_loop():
    while True:
        try:
            await asyncio.to_thread(run_detector_check)
        except Exception as exc:
            print(f"Detector error: {exc}")

        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(detector_loop())

    yield

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="IncidentIQ",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/incidents", response_model=IncidentResponse)
def create_incident(
    incident: IncidentCreate,
    db: Session = Depends(get_db),
):
    new_incident = Incident(
        severity=incident.severity,
        status=incident.status,
        affected_service=incident.affected_service,
        started_at=datetime.now(UTC),
    )

    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    return new_incident


@app.get("/incidents", response_model=list[IncidentResponse])
def get_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).all()


@app.get("/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


from backend.prometheus import query_prometheus


@app.get("/test-prometheus")
def test_prometheus():
    return query_prometheus("increase(payment_failures_total[1m])")
