from decimal import Decimal

from app.strategies.base import CreditRequest, EvaluationPolicy, monthly_installment


def _format_cop(value: Decimal | int) -> str:
    """Formatea un valor en pesos con separador de miles colombiano."""
    return f"${value:,.2f}".replace(",", "|").replace(".", ",").replace("|", ".")


def _score_below_minimum(request: CreditRequest, minimum: int) -> str | None:
    """Razón de rechazo por score insuficiente, o None si lo cumple."""
    if request.external_score >= minimum:
        return None
    return (
        f"El score crediticio ({request.external_score}) es inferior al mínimo "
        f"requerido ({minimum})."
    )


def _installment_over_ratio(request: CreditRequest, ratio: Decimal) -> str | None:
    """Razón de rechazo por cuota excesiva, o None si está dentro del límite."""
    installment = monthly_installment(request.amount)
    maximum = Decimal(request.monthly_income) * ratio
    if installment <= maximum:
        return None
    return (
        f"La cuota mensual ({_format_cop(installment)}) supera el {ratio:.0%} de los "
        f"ingresos mensuales ({_format_cop(maximum)})."
    )


def _employment_below_minimum(request: CreditRequest, minimum: int) -> str | None:
    """Razón de rechazo por antigüedad insuficiente, o None si la cumple."""
    if request.employment_months >= minimum:
        return None
    return (
        f"La antigüedad laboral ({request.employment_months} meses) es inferior al "
        f"mínimo requerido ({minimum} meses)."
    )


class ConservativePolicy(EvaluationPolicy):
    """Política conservadora (PHONE): score, antigüedad y cuota sobre ingreso.

    Evalúa todas las condiciones aunque alguna ya haya fallado, para reportar
    los motivos de rechazo completos.
    """

    name = "CONSERVATIVE"

    MIN_SCORE = 700
    MIN_EMPLOYMENT_MONTHS = 12
    MAX_INSTALLMENT_RATIO = Decimal("0.25")

    def evaluate(self, request: CreditRequest) -> list[str]:
        checks = (
            _score_below_minimum(request, self.MIN_SCORE),
            _employment_below_minimum(request, self.MIN_EMPLOYMENT_MONTHS),
            _installment_over_ratio(request, self.MAX_INSTALLMENT_RATIO),
        )
        return [reason for reason in checks if reason is not None]


class StandardPolicy(EvaluationPolicy):
    """Política estándar (TWIST): score y cuota sobre ingreso."""

    name = "STANDARD"

    MIN_SCORE = 600
    MAX_INSTALLMENT_RATIO = Decimal("0.35")

    def evaluate(self, request: CreditRequest) -> list[str]:
        checks = (
            _score_below_minimum(request, self.MIN_SCORE),
            _installment_over_ratio(request, self.MAX_INSTALLMENT_RATIO),
        )
        return [reason for reason in checks if reason is not None]


class AggressivePolicy(EvaluationPolicy):
    """Política agresiva (CARD): score alto, o score medio con ingreso alto.

    Las condiciones son alternativas, por lo que basta con satisfacer una.
    """

    name = "AGGRESSIVE"

    MIN_SCORE = 550
    ALTERNATIVE_MIN_SCORE = 500
    ALTERNATIVE_MIN_INCOME = 3_000_000

    def evaluate(self, request: CreditRequest) -> list[str]:
        if request.external_score >= self.MIN_SCORE:
            return []

        meets_alternative = (
            request.external_score >= self.ALTERNATIVE_MIN_SCORE
            and request.monthly_income >= self.ALTERNATIVE_MIN_INCOME
        )
        if meets_alternative:
            return []

        return [
            f"El score crediticio ({request.external_score}) es inferior a "
            f"{self.MIN_SCORE} y no cumple la condición alternativa: score desde "
            f"{self.ALTERNATIVE_MIN_SCORE} con ingresos mensuales desde "
            f"{_format_cop(self.ALTERNATIVE_MIN_INCOME)}."
        ]
