from datetime import datetime, timezone

from app.enums import ApplicationStatus, Product
from app.exceptions import ApplicationNotFoundError
from app.models import Application
from app.repositories.application_repository import ApplicationRepository
from app.schemas import ApplicationCreate
from app.strategies import get_policy


class EvaluationService:
    """Orquesta la evaluación de solicitudes: elige la política, la aplica y persiste.

    Independiente de HTTP y de SQLAlchemy; recibe el repositorio ya construido.
    """

    def __init__(self, repository: ApplicationRepository) -> None:
        self._repository = repository

    def create(self, data: ApplicationCreate) -> Application:
        policy = get_policy(data.product)
        reasons = policy.evaluate(data)

        application = Application(
            amount=data.amount,
            monthly_income=data.monthly_income,
            employment_months=data.employment_months,
            external_score=data.external_score,
            product=data.product,
            status=self._status_for(reasons),
            rejection_reasons=reasons,
            policy_name=policy.name,
        )
        return self._repository.add(application)

    def get(self, application_id: int) -> Application:
        application = self._repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        return application

    def find(
        self,
        status: ApplicationStatus | None = None,
        product: Product | None = None,
    ) -> list[Application]:
        return self._repository.find(status=status, product=product)

    def reevaluate(self, application_id: int) -> Application:
        """Reevalúa una solicitud existente con la política vigente."""
        application = self.get(application_id)

        policy = get_policy(application.product)
        reasons = policy.evaluate(application)

        application.status = self._status_for(reasons)
        application.rejection_reasons = reasons
        application.policy_name = policy.name
        application.evaluated_at = datetime.now(timezone.utc)

        self._repository.commit()
        return application

    @staticmethod
    def _status_for(reasons: list[str]) -> ApplicationStatus:
        """Traduce las razones reportadas por la política en una decisión."""
        return ApplicationStatus.REJECTED if reasons else ApplicationStatus.APPROVED
