"""Orquestra ações de agendamento com regras básicas."""

from datetime import datetime
from typing import List

from ..models.appointment import Appointment


class Scheduler:
    def __init__(self) -> None:
        self._appointments: List[Appointment] = []

    def add_appointment(self, appointment: Appointment) -> None:
        """Registra um novo agendamento."""
        self._appointments.append(appointment)

    def list_appointments(self) -> None:
        """Imprime os agendamentos existentes."""
        for appt in self._appointments:
            print(appt)

    def add_test_appointment(self) -> None:
        """Adiciona um exemplo rápido para ilustrar o modelo."""
        example = Appointment(
            patient_name="João Silva",
            doctor_name="Dra. Camila",
            scheduled_at=datetime.now(),
            reason="Consulta de acompanhamento",
        )
        self.add_appointment(example)
