from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.enums import ApplicationStatus, Product

# Cotas superiores: evitan que un valor desmedido llegue a la base de datos y
# rompa el rango de INTEGER (int64), y acotan el dominio a valores plausibles.
MAX_AMOUNT = 1_000_000_000_000  # un billón de COP
MAX_MONTHLY_INCOME = 1_000_000_000_000
MAX_EMPLOYMENT_MONTHS = 960  # 80 años de vida laboral
MAX_EXTERNAL_SCORE = 1000


class HealthResponse(BaseModel):
    status: str


class ApplicationCreate(BaseModel):
    """Entrada de `POST /applications`.

    Concentra la validación de formato, de modo que las políticas operen sobre
    datos ya validados. Los campos numéricos son estrictos para que un booleano
    no termine interpretado como un monto.
    """

    amount: int = Field(
        gt=0, le=MAX_AMOUNT, strict=True, description="Monto solicitado en COP"
    )
    monthly_income: int = Field(
        gt=0,
        le=MAX_MONTHLY_INCOME,
        strict=True,
        description="Ingresos mensuales en COP",
    )
    employment_months: int = Field(
        ge=0,
        le=MAX_EMPLOYMENT_MONTHS,
        strict=True,
        description="Antigüedad laboral en meses",
    )
    external_score: int = Field(
        ge=0, le=MAX_EXTERNAL_SCORE, strict=True, description="Score externo (0-1000)"
    )
    product: Product


class ApplicationRead(BaseModel):
    """Representación de una solicitud en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    monthly_income: int
    employment_months: int
    external_score: int
    product: Product
    status: ApplicationStatus
    rejection_reasons: list[str]
    policy_name: str
    evaluated_at: datetime

    @field_serializer("evaluated_at")
    def serialize_evaluated_at(self, value: datetime) -> str:
        """Devuelve la marca de tiempo siempre en UTC explícito.

        Las fechas se persisten en UTC, pero SQLite no almacena la zona horaria
        y las devuelve sin ella; sin este marcador el consumidor las leería como
        hora local.
        """
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
