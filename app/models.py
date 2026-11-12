from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import ApplicationStatus, Product


class Application(Base):
    """Solicitud de crédito con el resultado de su evaluación."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Datos de la solicitud
    amount: Mapped[int]
    monthly_income: Mapped[int]
    employment_months: Mapped[int]
    external_score: Mapped[int]
    product: Mapped[Product] = mapped_column(SAEnum(Product))

    # Resultado de la evaluación
    status: Mapped[ApplicationStatus] = mapped_column(SAEnum(ApplicationStatus))
    rejection_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Trazabilidad: permite saber con qué criterio se evaluó cada solicitud
    # si los umbrales cambian
    policy_name: Mapped[str]
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
