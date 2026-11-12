"""Excepciones de dominio, independientes del transporte HTTP."""


class ApplicationNotFoundError(Exception):
    """La solicitud solicitada no existe."""

    def __init__(self, application_id: int) -> None:
        self.application_id = application_id
        super().__init__(f"Application {application_id} not found")
