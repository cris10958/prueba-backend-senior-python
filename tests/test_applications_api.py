"""Tests de punta a punta de la API."""

from app.strategies.policies import ConservativePolicy

APPROVED_PHONE = {
    "amount": 1_200_000,
    "monthly_income": 3_000_000,
    "employment_months": 24,
    "external_score": 750,
    "product": "PHONE",
}

REJECTED_PHONE = {**APPROVED_PHONE, "external_score": 600}


class TestCreateApplication:
    def test_aprueba_y_persiste(self, client):
        response = client.post("/applications", json=APPROVED_PHONE)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "APPROVED"
        assert body["rejection_reasons"] == []
        assert body["policy_name"] == "CONSERVATIVE"
        assert body["id"] > 0

    def test_rechaza_e_incluye_las_razones(self, client):
        response = client.post("/applications", json=REJECTED_PHONE)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "REJECTED"
        assert len(body["rejection_reasons"]) == 1
        assert "score crediticio" in body["rejection_reasons"][0]

    def test_rechaza_entradas_invalidas(self, client):
        response = client.post(
            "/applications", json={**APPROVED_PHONE, "external_score": 1001}
        )
        assert response.status_code == 422

    def test_rechaza_un_producto_desconocido(self, client):
        response = client.post(
            "/applications", json={**APPROVED_PHONE, "product": "LAPTOP"}
        )
        assert response.status_code == 422

    def test_rechaza_montos_fuera_del_rango_almacenable(self, client):
        """Sin cota superior, el monto rompería el INTEGER de la base y daría un 500."""
        response = client.post(
            "/applications", json={**APPROVED_PHONE, "amount": 9_223_372_036_854_775_808}
        )
        assert response.status_code == 422

    def test_rechaza_un_booleano_como_monto(self, client):
        """En modo laxo, Pydantic convertiría True en un monto de 1."""
        response = client.post("/applications", json={**APPROVED_PHONE, "amount": True})
        assert response.status_code == 422

    def test_rechaza_por_cuota_sobre_el_ingreso(self, client):
        response = client.post(
            "/applications",
            json={
                **APPROVED_PHONE,
                "amount": 9_000_000,
                "monthly_income": 2_000_000,
            },
        )

        body = response.json()
        assert body["status"] == "REJECTED"
        assert any("cuota mensual" in reason for reason in body["rejection_reasons"])


class TestGetApplication:
    def test_devuelve_la_solicitud_creada(self, client):
        created = client.post("/applications", json=APPROVED_PHONE).json()

        response = client.get(f"/applications/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created

    def test_404_cuando_no_existe(self, client):
        response = client.get("/applications/9999")
        assert response.status_code == 404

    def test_la_marca_de_tiempo_se_expone_en_utc(self, client):
        """Sin zona horaria explícita, el consumidor la leería como hora local."""
        created = client.post("/applications", json=APPROVED_PHONE).json()

        assert created["evaluated_at"].endswith("+00:00")


class TestListApplications:
    def _seed(self, client):
        client.post("/applications", json=APPROVED_PHONE)
        client.post("/applications", json=REJECTED_PHONE)
        client.post(
            "/applications",
            json={**APPROVED_PHONE, "product": "TWIST", "external_score": 650},
        )

    def test_sin_filtros_devuelve_todo(self, client):
        self._seed(client)
        assert len(client.get("/applications").json()) == 3

    def test_filtra_por_estado(self, client):
        self._seed(client)
        body = client.get("/applications?status=APPROVED").json()
        assert len(body) == 2
        assert all(item["status"] == "APPROVED" for item in body)

    def test_filtra_por_producto(self, client):
        self._seed(client)
        body = client.get("/applications?product=TWIST").json()
        assert len(body) == 1
        assert body[0]["product"] == "TWIST"

    def test_combina_los_dos_filtros(self, client):
        self._seed(client)
        body = client.get("/applications?status=APPROVED&product=TWIST").json()
        assert len(body) == 1
        assert body[0]["product"] == "TWIST"
        assert body[0]["status"] == "APPROVED"

    def test_sin_coincidencias_devuelve_lista_vacia(self, client):
        self._seed(client)
        assert client.get("/applications?product=CARD").json() == []


class TestReevaluate:
    def test_aplica_el_umbral_vigente_y_cambia_la_decision(self, client, monkeypatch):
        """Una solicitud rechazada pasa a aprobada si bajan el umbral."""
        created = client.post("/applications", json=REJECTED_PHONE).json()
        assert created["status"] == "REJECTED"

        monkeypatch.setattr(ConservativePolicy, "MIN_SCORE", 500)
        body = client.post(f"/applications/{created['id']}/reevaluate").json()

        assert body["id"] == created["id"]
        assert body["status"] == "APPROVED"
        assert body["rejection_reasons"] == []

    def test_actualiza_la_marca_de_tiempo(self, client):
        created = client.post("/applications", json=APPROVED_PHONE).json()

        body = client.post(f"/applications/{created['id']}/reevaluate").json()

        assert body["evaluated_at"] > created["evaluated_at"]

    def test_404_cuando_no_existe(self, client):
        response = client.post("/applications/9999/reevaluate")
        assert response.status_code == 404
