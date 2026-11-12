from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Protocol

TERM_MONTHS = 12


class CreditRequest(Protocol):
    """Datos mínimos que una política necesita para decidir.

    Es un Protocol para que tanto el schema de entrada como el modelo ORM lo
    satisfagan, y la misma política sirva para evaluar y reevaluar.
    """

    amount: int
    monthly_income: int
    employment_months: int
    external_score: int


def monthly_installment(amount: int) -> Decimal:
    """Cuota mensual a plazo fijo.

    Usa Decimal para que la comparación contra el porcentaje de ingreso sea
    exacta en los casos de frontera. Con float, un ingreso de 1.310.725 y un
    monto de 5.505.045 dan un límite de 458753.74999999994 en lugar de
    458753.75, y la solicitud se rechaza pese a estar justo en el tope.
    """
    return Decimal(amount) / Decimal(TERM_MONTHS)


class EvaluationPolicy(ABC):
    """Criterio de evaluación de una solicitud de crédito."""

    name: str

    @abstractmethod
    def evaluate(self, request: CreditRequest) -> list[str]:
        """Devuelve las razones de rechazo. Lista vacía significa aprobado."""
