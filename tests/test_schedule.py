"""Casos básicos para o scheduler."""

from datetime import datetime

from clinic.services import Scheduler
from clinic.models import Appointment


def test_scheduler_accepts_appointments() -> None:
    scheduler = Scheduler()
    appointment = Appointment(
        patient_name="Ana",
        doctor_name="Dr. Paulo",
        scheduled_at=datetime(2026, 3, 10, 10, 0),
        reason="Retorno",
    )
    scheduler.add_appointment(appointment)
    assert len(scheduler._appointments) == 1
