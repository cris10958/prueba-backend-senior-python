from fastapi import APIRouter, Depends, status as http_status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import ApplicationStatus, Product
from app.models import Application
from app.repositories.application_repository import ApplicationRepository
from app.schemas import ApplicationCreate, ApplicationRead
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/applications", tags=["applications"])


def get_service(db: Session = Depends(get_db)) -> EvaluationService:
    """Construye la cadena sesión -> repositorio -> servicio."""
    return EvaluationService(ApplicationRepository(db))


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Evalúa y persiste una solicitud de crédito",
)
def create_application(
    data: ApplicationCreate,
    service: EvaluationService = Depends(get_service),
) -> Application:
    return service.create(data)


@router.get(
    "",
    response_model=list[ApplicationRead],
    summary="Lista solicitudes con filtros opcionales",
)
def list_applications(
    status: ApplicationStatus | None = None,
    product: Product | None = None,
    service: EvaluationService = Depends(get_service),
) -> list[Application]:
    return service.find(status=status, product=product)


@router.get(
    "/{application_id}",
    response_model=ApplicationRead,
    summary="Consulta una solicitud por su id",
)
def get_application(
    application_id: int,
    service: EvaluationService = Depends(get_service),
) -> Application:
    return service.get(application_id)


@router.post(
    "/{application_id}/reevaluate",
    response_model=ApplicationRead,
    summary="Reevalúa una solicitud con la política vigente",
)
def reevaluate_application(
    application_id: int,
    service: EvaluationService = Depends(get_service),
) -> Application:
    return service.reevaluate(application_id)
