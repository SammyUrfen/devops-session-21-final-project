from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .models import Incident
from .schemas import IncidentCreate, IncidentOut, IncidentUpdate, StatsOut


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Containers run `alembic upgrade head` first, so this is a no-op there. It keeps tests self-contained.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


def _get_or_404(db: Session, incident_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/")
def root():
    return {"service": settings.app_name, "environment": settings.environment, "docs": "/docs"}


@app.get("/health")
def health():
    """Liveness: the process answers. No DB call, so a DB outage does not restart every pod."""
    return {"status": "UP"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: the DB answers. A failing DB takes the pod out of the Service, it does not kill it."""
    db.execute(text("SELECT 1"))
    return {"status": "READY"}


@app.get("/api/config")
def config():
    return {"environment": settings.environment, "banner": settings.banner}


@app.get("/api/incidents", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db)):
    return list(db.scalars(select(Incident).order_by(Incident.id.desc())))


@app.get("/api/incidents/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Incident.status, func.count(Incident.id)).group_by(Incident.status)).all()
    counts = dict(rows)
    sev1 = db.scalar(
        select(func.count(Incident.id)).where(Incident.severity == "SEV1", Incident.status != "RESOLVED")
    )
    return StatsOut(
        total=sum(counts.values()),
        open=counts.get("OPEN", 0),
        investigating=counts.get("INVESTIGATING", 0),
        resolved=counts.get("RESOLVED", 0),
        sev1Open=sev1 or 0,
    )


@app.get("/api/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, incident_id)


@app.post("/api/incidents", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@app.put("/api/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)):
    incident = _get_or_404(db, incident_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, key, value)
    db.commit()
    db.refresh(incident)
    return incident


@app.delete("/api/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, incident_id))
    db.commit()
