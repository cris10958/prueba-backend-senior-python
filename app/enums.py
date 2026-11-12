from enum import Enum


class Product(str, Enum):
    """Tipos de producto disponibles para una solicitud de crédito."""

    PHONE = "PHONE"
    TWIST = "TWIST"
    CARD = "CARD"


class ApplicationStatus(str, Enum):
    """Resultado de la evaluación de una solicitud."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
