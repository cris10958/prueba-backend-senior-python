from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registra el modelo en Base.metadata)
from app.database import Base, engine
from app.exceptions import ApplicationNotFoundError
from app.routers import applications
from app.schemas import HealthResponse

# Simple setup: create tables on startup. In production, use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Credit Evaluation Service")

app.include_router(applications.router)


@app.exception_handler(ApplicationNotFoundError)
def handle_application_not_found(
    request: Request, exc: ApplicationNotFoundError
) -> JSONResponse:
    """Traduce la excepción de dominio a un 404, en un único lugar."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}
