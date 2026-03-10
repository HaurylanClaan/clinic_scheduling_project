"""Representa um agendamento clínico básico."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Appointment:
    patient_name: str
    doctor_name: str
    scheduled_at: datetime
    reason: str

    def __str__(self) -> str:
        return (
            f"{self.scheduled_at.isoformat()} | {self.doctor_name} atende {self.patient_name} "
            f"para {self.reason}"
        )
