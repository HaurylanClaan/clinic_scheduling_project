"""Representa um agendamento clínico básico."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Appointment:
    patient_name: str
    doctor_name: str
    scheduled_at: datetime
    reason: str
    checked_in: bool = False
    checked_in_at: Optional[datetime] = None

    def __str__(self) -> str:
        status = "chegou" if self.checked_in else "pendente"
        return (
            f"{self.scheduled_at.isoformat()} | {self.doctor_name} atende {self.patient_name} "
            f"para {self.reason} [{status}]"
        )
