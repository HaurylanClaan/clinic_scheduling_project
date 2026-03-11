"""Integração básica com o StorageManager para o Scheduler."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from clinic.models import Doctor
from clinic.services import Scheduler
from clinic.storage import StorageManager


def _new_scheduler(temp_root: Path) -> Scheduler:
    storage = StorageManager(temp_root)
    storage.select_database("clinic")
    return Scheduler(storage)


def test_patient_can_schedule_an_available_slot() -> None:
    temp_root = Path(tempfile.mkdtemp())
    scheduler = _new_scheduler(temp_root)
    base = datetime(2026, 3, 10, 8, 0)
    doctor = Doctor(
        name="Dr. Paulo",
        specialty="Cardiologia",
        availability=[base + timedelta(minutes=30 * i) for i in range(4)],
    )
    scheduler.add_doctor(doctor)
    scheduler.register_patient(
        name="Ana Souza", email="ana@example.com", phone="+55 11 99999-0000"
    )

    slot_to_book = doctor.availability[1]
    appointment = scheduler.schedule_appointment(
        patient_name="Ana Souza",
        doctor_name=doctor.name,
        slot=slot_to_book,
        reason="Retorno de exames",
    )

    assert appointment.patient_name == "Ana Souza"
    assert appointment.doctor_name == doctor.name
    assert slot_to_book not in scheduler.available_slots(doctor.name)


def test_doctor_blocks_slots_and_sees_appointments() -> None:
    temp_root = Path(tempfile.mkdtemp())
    scheduler = _new_scheduler(temp_root)
    base = datetime(2026, 3, 11, 9, 0)
    doctor = Doctor(
        name="Dra. Camila",
        specialty="Dermatologia",
        availability=[base + timedelta(minutes=30 * i) for i in range(5)],
    )
    scheduler.add_doctor(doctor)
    scheduler.register_patient(
        name="Carlos Meireles", email="carlos@example.com", phone="+55 11 99999-0010"
    )

    slot_to_block = doctor.availability[0]
    scheduler.block_slot(doctor.name, slot_to_block)
    assert slot_to_block not in scheduler.available_slots(doctor.name)

    slot_to_book = doctor.availability[1]
    appointment = scheduler.schedule_appointment(
        patient_name="Carlos Meireles",
        doctor_name=doctor.name,
        slot=slot_to_book,
        reason="Avaliação preventiva",
    )

    appointments = scheduler.doctor_appointments(doctor.name)
    assert len(appointments) == 1
    assert appointments[0] is appointment


def test_reception_overview_and_check_in_workflow() -> None:
    temp_root = Path(tempfile.mkdtemp())
    scheduler = _new_scheduler(temp_root)
    base = datetime(2026, 3, 12, 10, 0)
    doctor = Doctor(
        name="Dr. Rafael",
        specialty="Ortopedia",
        availability=[base + timedelta(minutes=30 * i) for i in range(3)],
    )
    scheduler.add_doctor(doctor)

    slot = doctor.availability[0]
    appointment = scheduler.schedule_by_phone(
        patient_name="Lucia Campos",
        doctor_name=doctor.name,
        slot=slot,
        reason="Consulta por telefone",
        phone="+55 11 98888-0100",
    )

    overview = scheduler.reception_overview()
    assert len(overview) == 1
    assert doctor.name in overview[0]

    checked_in = scheduler.check_in("Lucia Campos", doctor.name, slot)
    assert checked_in.checked_in
    assert scheduler.appointments_for_patient("Lucia Campos")[0] is appointment
