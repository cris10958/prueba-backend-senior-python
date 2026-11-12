"""Resolución de la política aplicable a cada producto."""

from app.enums import Product
from app.strategies.base import EvaluationPolicy
from app.strategies.policies import (
    AggressivePolicy,
    ConservativePolicy,
    StandardPolicy,
)

# Las políticas no guardan estado: una instancia por producto es suficiente.
_POLICIES: dict[Product, EvaluationPolicy] = {
    Product.PHONE: ConservativePolicy(),
    Product.TWIST: StandardPolicy(),
    Product.CARD: AggressivePolicy(),
}


def get_policy(product: Product) -> EvaluationPolicy:
    """Devuelve la política registrada para el producto."""
    return _POLICIES[product]
