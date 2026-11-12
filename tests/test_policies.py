"""Tests unitarios de las políticas, sin API ni base de datos."""

import pytest

from app.enums import Product
from app.schemas import ApplicationCreate
from app.strategies import get_policy
from app.strategies.policies import (
    AggressivePolicy,
    ConservativePolicy,
    StandardPolicy,
)


def build_request(**overrides) -> ApplicationCreate:
    """Solicitud base aprobada por cualquier política.

    Cada test sobrescribe solo el campo bajo prueba.
    """
    defaults = {
        "amount": 1_200_000,  # cuota = 100.000
        "monthly_income": 3_000_000,
        "employment_months": 24,
        "external_score": 750,
        "product": Product.PHONE,
    }
    return ApplicationCreate(**{**defaults, **overrides})


class TestRegistry:
    @pytest.mark.parametrize(
        ("product", "expected"),
        [
            (Product.PHONE, ConservativePolicy),
            (Product.TWIST, StandardPolicy),
            (Product.CARD, AggressivePolicy),
        ],
    )
    def test_cada_producto_resuelve_su_politica(self, product, expected):
        assert isinstance(get_policy(product), expected)


class TestConservativePolicy:
    policy = ConservativePolicy()

    def test_aprueba_cuando_cumple_las_tres_condiciones(self):
        assert self.policy.evaluate(build_request()) == []

    def test_rechaza_por_score_bajo(self):
        reasons = self.policy.evaluate(build_request(external_score=699))
        assert len(reasons) == 1
        assert "score crediticio" in reasons[0]

    def test_rechaza_por_antiguedad_insuficiente(self):
        reasons = self.policy.evaluate(build_request(employment_months=11))
        assert len(reasons) == 1
        assert "antigüedad laboral" in reasons[0]

    def test_rechaza_por_cuota_sobre_el_25_por_ciento(self):
        # Cuota = 9.000.000 / 12 = 750.000 > 25% de 2.000.000 (500.000)
        reasons = self.policy.evaluate(
            build_request(amount=9_000_000, monthly_income=2_000_000)
        )
        assert len(reasons) == 1
        assert "cuota mensual" in reasons[0]

    def test_acumula_todas_las_razones_de_rechazo(self):
        reasons = self.policy.evaluate(
            build_request(
                external_score=500, employment_months=2, amount=9_000_000,
                monthly_income=2_000_000,
            )
        )
        assert len(reasons) == 3

    def test_los_limites_exactos_aprueban(self):
        request = build_request(
            external_score=700,
            employment_months=12,
            amount=6_000_000,  # cuota = 500.000
            monthly_income=2_000_000,  # 25% = 500.000
        )
        assert self.policy.evaluate(request) == []


class TestStandardPolicy:
    policy = StandardPolicy()

    def test_aprueba_con_score_y_cuota_dentro_del_limite(self):
        request = build_request(product=Product.TWIST, external_score=600)
        assert self.policy.evaluate(request) == []

    def test_rechaza_por_score_bajo(self):
        request = build_request(product=Product.TWIST, external_score=599)
        reasons = self.policy.evaluate(request)
        assert len(reasons) == 1
        assert "score crediticio" in reasons[0]

    def test_rechaza_por_cuota_sobre_el_35_por_ciento(self):
        # Cuota = 12.000.000 / 12 = 1.000.000 > 35% de 2.000.000 (700.000)
        request = build_request(
            product=Product.TWIST, amount=12_000_000, monthly_income=2_000_000
        )
        reasons = self.policy.evaluate(request)
        assert len(reasons) == 1
        assert "cuota mensual" in reasons[0]

    def test_aprueba_el_limite_exacto_que_float_rechazaria(self):
        """Caso de frontera que falla si la cuota se calcula con float.

        Con float, el límite da 458753.74999999994 en lugar de 458753.75 y la
        solicitud se rechazaría pese a estar justo en el tope del 35%.
        """
        request = build_request(
            product=Product.TWIST,
            external_score=600,
            monthly_income=1_310_725,
            amount=5_505_045,
        )
        assert self.policy.evaluate(request) == []

    def test_no_exige_antiguedad_laboral(self):
        request = build_request(
            product=Product.TWIST, external_score=600, employment_months=0
        )
        assert self.policy.evaluate(request) == []


class TestAggressivePolicy:
    policy = AggressivePolicy()

    def test_aprueba_por_score_suficiente(self):
        request = build_request(product=Product.CARD, external_score=550)
        assert self.policy.evaluate(request) == []

    def test_aprueba_por_la_ruta_alternativa(self):
        request = build_request(
            product=Product.CARD, external_score=500, monthly_income=3_000_000
        )
        assert self.policy.evaluate(request) == []

    def test_rechaza_cuando_no_cumple_ninguna_ruta(self):
        request = build_request(
            product=Product.CARD, external_score=520, monthly_income=2_999_999
        )
        reasons = self.policy.evaluate(request)
        assert len(reasons) == 1
        assert "condición alternativa" in reasons[0]

    def test_rechaza_con_score_bajo_aunque_el_ingreso_sea_alto(self):
        request = build_request(
            product=Product.CARD, external_score=499, monthly_income=50_000_000
        )
        assert self.policy.evaluate(request) != []

    def test_no_evalua_la_cuota(self):
        request = build_request(
            product=Product.CARD, external_score=800, amount=100_000_000,
            monthly_income=1_000_000,
        )
        assert self.policy.evaluate(request) == []
