from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ApplicationStatus, Product
from app.models import Application


class ApplicationRepository:
    """Acceso a la tabla de solicitudes.

    Aísla SQLAlchemy del resto de la aplicación.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, application: Application) -> Application:
        self._session.add(application)
        self._session.commit()
        self._session.refresh(application)
        return application

    def get(self, application_id: int) -> Application | None:
        return self._session.get(Application, application_id)

    def find(
        self,
        status: ApplicationStatus | None = None,
        product: Product | None = None,
    ) -> list[Application]:
        """Lista las solicitudes aplicando los filtros informados."""
        statement = select(Application)

        if status is not None:
            statement = statement.where(Application.status == status)
        if product is not None:
            statement = statement.where(Application.product == product)

        return list(self._session.scalars(statement.order_by(Application.id)))

    def commit(self) -> None:
        """Confirma los cambios pendientes de la sesión."""
        self._session.commit()
