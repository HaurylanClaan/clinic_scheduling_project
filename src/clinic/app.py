"""Ponto de entrada minimalista para o serviço de agendamento."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from .models import Doctor
from .services.scheduler import Scheduler
from .storage import StorageManager


def run_scheduler() -> None:
    """Simula o ciclo de cadastros, marcações e conferências da recepção."""
    storage = StorageManager(Path("data"))
    print("Bases existentes:", storage.list_databases())

    # Criar ou selecionar um banco; o usuário pode criar vários e escolher qual usar
    storage.create_database("clinic_default")
    storage.select_database("clinic_default")

    scheduler = Scheduler(storage)

    doctor = Doctor(
        name="Dr. Paulo",
        specialty="Clínica geral",
        availability=_hourly_slots(start=datetime.now(), count=6),
    )
    scheduler.add_doctor(doctor)

    scheduler.register_patient(
        name="Ana Souza",
        email="ana@example.com",
        phone="+55 11 99999-0004",
    )

    print(f"Horários disponíveis para {doctor.name}:")
    for slot in scheduler.available_slots(doctor.name):
        print(f" - {slot.isoformat()}")

    slots = scheduler.available_slots(doctor.name)
    if not slots:
        print("Nenhum horário disponível no momento.")
        return

    appointment_slot = slots[0]
    appointment = scheduler.schedule_appointment(
        patient_name="Ana Souza",
        doctor_name=doctor.name,
        slot=appointment_slot,
        reason="Consulta de rotina",
    )
    print("Consulta confirmada:", appointment)

    blocked_slot = doctor.availability[1] if len(doctor.availability) > 1 else None
    if blocked_slot:
        scheduler.block_slot(doctor.name, blocked_slot)
        print(f"Horário bloqueado por {doctor.name}: {blocked_slot.isoformat()}")

    print(f"Horários disponíveis atualizados para {doctor.name}:")
    for slot in scheduler.available_slots(doctor.name):
        print(f" - {slot.isoformat()}")

    print(f"Agenda do(a) {doctor.name}:")
    for appt in scheduler.doctor_appointments(doctor.name):
        print(f" - {appt}")

    phone_slots = scheduler.available_slots(doctor.name)
    if phone_slots:
        phone_appointment = scheduler.schedule_by_phone(
            patient_name="Carlos Meireles",
            doctor_name=doctor.name,
            slot=phone_slots[0],
            reason="Consulta marcada por telefone",
            phone="+55 11 98888-0022",
        )
        print("Consulta marcada por telefone:", phone_appointment)

    scheduler.check_in("Ana Souza", doctor.name, appointment_slot)
    print("Paciente Ana Souza fez check-in.")

    print("Visão geral da recepção:")
    for summary in scheduler.reception_overview():
        print(f" - {summary}")

    print("Histórico de consultas de Ana Souza:")
    for appt in scheduler.appointments_for_patient("Ana Souza"):
        print(f" - {appt}")


def _hourly_slots(start: datetime, count: int) -> List[datetime]:
    base = start.replace(minute=0, second=0, microsecond=0)
    return [base + timedelta(minutes=30 * i) for i in range(count)]
