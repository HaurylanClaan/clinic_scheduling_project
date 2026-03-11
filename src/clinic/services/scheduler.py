"""Orquestra ações de agendamento persistidas via SQLite."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from ..models import Appointment, Doctor, Patient
from ..storage import StorageManager


class Scheduler:
    def __init__(self, storage: StorageManager) -> None:
        if not storage.current_database:
            raise ValueError("É preciso selecionar um banco antes de instanciar o Scheduler")
        self._storage = storage
        self._appointments: List[Appointment] = []
        self._patients: Dict[str, Patient] = {}
        self._doctors: Dict[str, Doctor] = {}
        self._load_from_db()

    def _load_from_db(self) -> None:
        self._appointments.clear()
        self._patients.clear()
        self._doctors.clear()
        with self._storage.connection() as conn:
            for row in conn.execute("SELECT name, email, phone FROM patients"):
                self._patients[row["name"]] = Patient(
                    name=row["name"], email=row["email"], phone=row["phone"]
                )

            for row in conn.execute("SELECT name, specialty FROM doctors"):
                self._doctors[row["name"]] = Doctor(
                    name=row["name"], specialty=row["specialty"], availability=[]
                )

            for row in conn.execute(
                "SELECT doctor_name, slot FROM doctor_availability ORDER BY slot"
            ):
                doctor = self._doctors.get(row["doctor_name"])
                if doctor:
                    slot = self._parse_slot(row["slot"])
                    if slot:
                        doctor.availability.append(slot)

            for row in conn.execute(
                "SELECT doctor_name, slot FROM doctor_blocked_slots ORDER BY slot"
            ):
                doctor = self._doctors.get(row["doctor_name"])
                if doctor:
                    slot = self._parse_slot(row["slot"])
                    if slot:
                        doctor.blocked_slots.append(slot)

            for row in conn.execute(
                "SELECT patient_name, doctor_name, scheduled_at, reason, checked_in, checked_in_at FROM appointments"
            ):
                appointment = Appointment(
                    patient_name=row["patient_name"],
                    doctor_name=row["doctor_name"],
                    scheduled_at=self._parse_slot(row["scheduled_at"]),
                    reason=row["reason"],
                    checked_in=bool(row["checked_in"]),
                    checked_in_at=self._parse_slot(row["checked_in_at"]),
                )
                self._appointments.append(appointment)

    @staticmethod
    def _parse_slot(value: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(value) if value else None

    def register_patient(self, name: str, email: str, phone: str) -> Patient:
        """Cria ou atualiza o cadastro de um paciente."""
        patient = Patient(name=name, email=email, phone=phone)
        self._patients[patient.name] = patient
        with self._storage.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO patients (name, email, phone) VALUES (?, ?, ?)",
                (patient.name, patient.email, patient.phone),
            )
        return patient

    def add_doctor(self, doctor: Doctor) -> None:
        """Disponibiliza um médico no sistema de agendamentos."""
        self._doctors[doctor.name] = doctor
        with self._storage.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO doctors (name, specialty) VALUES (?, ?)",
                (doctor.name, doctor.specialty),
            )
            conn.execute("DELETE FROM doctor_availability WHERE doctor_name = ?", (doctor.name,))
            conn.executemany(
                "INSERT INTO doctor_availability (doctor_name, slot) VALUES (?, ?)",
                [(doctor.name, slot.isoformat()) for slot in doctor.availability],
            )
            conn.execute("DELETE FROM doctor_blocked_slots WHERE doctor_name = ?", (doctor.name,))
            conn.executemany(
                "INSERT INTO doctor_blocked_slots (doctor_name, slot) VALUES (?, ?)",
                [(doctor.name, slot.isoformat()) for slot in doctor.blocked_slots],
            )

    def list_doctors(self) -> List[Doctor]:
        """Retorna os médicos cadastrados."""
        return list(self._doctors.values())

    def available_slots(self, doctor_name: str) -> List[datetime]:
        """Lista os horários ainda livres do médico."""
        doctor = self._doctors.get(doctor_name)
        if not doctor:
            return []
        booked = self._booked_slots(doctor_name)
        blocked = set(doctor.blocked_slots)
        return [
            slot
            for slot in doctor.availability
            if slot not in booked and slot not in blocked
        ]

    def schedule_appointment(
        self, patient_name: str, doctor_name: str, slot: datetime, reason: str
    ) -> Appointment:
        """Marca uma consulta garantindo disponibilidade."""
        patient = self._patients.get(patient_name)
        if not patient:
            raise ValueError(f"Paciente {patient_name} não cadastrado")

        slots = self.available_slots(doctor_name)
        if slot not in slots:
            raise ValueError(f"Horário {slot.isoformat()} indisponível para {doctor_name}")

        appointment = Appointment(
            patient_name=patient.name,
            doctor_name=doctor_name,
            scheduled_at=slot,
            reason=reason,
        )
        self.add_appointment(appointment)
        return appointment

    def schedule_by_phone(
        self,
        patient_name: str,
        doctor_name: str,
        slot: datetime,
        reason: str,
        phone: str,
        email: Optional[str] = None,
    ) -> Appointment:
        """Agenda uma consulta via recepção telefônica."""
        contact_email = email or f"{patient_name.replace(' ', '.').lower()}@phone.agenda"
        self.register_patient(name=patient_name, email=contact_email, phone=phone)
        return self.schedule_appointment(patient_name, doctor_name, slot, reason)

    def block_slot(self, doctor_name: str, slot: datetime) -> None:
        """Permite que o médico bloqueie um horário antes de pacientes agendarem."""
        doctor = self._doctors.get(doctor_name)
        if not doctor:
            raise ValueError(f"Médico {doctor_name} não encontrado")

        if slot not in doctor.availability:
            raise ValueError(f"Horário {slot.isoformat()} fora da grade de {doctor_name}")

        if slot in self._booked_slots(doctor_name):
            raise ValueError(
                f"Não é possível bloquear um horário já reservado ({slot.isoformat()})"
            )

        if slot in doctor.blocked_slots:
            return

        doctor.blocked_slots.append(slot)
        with self._storage.connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO doctor_blocked_slots (doctor_name, slot) VALUES (?, ?)",
                (doctor_name, slot.isoformat()),
            )

    def doctor_appointments(self, doctor_name: str) -> List[Appointment]:
        """Retorna os compromissos já marcados para o médico."""
        return [appt for appt in self._appointments if appt.doctor_name == doctor_name]

    def appointments_for_patient(self, patient_name: str) -> List[Appointment]:
        """Retorna todas as consultas registradas de um paciente."""
        return [appt for appt in self._appointments if appt.patient_name == patient_name]

    def check_in(self, patient_name: str, doctor_name: str, slot: datetime) -> Appointment:
        """Registra a chegada do paciente para um horário específico."""
        appointment = self._find_appointment(patient_name, doctor_name, slot)
        if appointment.checked_in:
            return appointment
        appointment.checked_in = True
        appointment.checked_in_at = datetime.now()
        with self._storage.connection() as conn:
            conn.execute(
                "UPDATE appointments SET checked_in = 1, checked_in_at = ? WHERE patient_name = ? AND doctor_name = ? AND scheduled_at = ?",
                (
                    appointment.checked_in_at.isoformat(),
                    patient_name,
                    doctor_name,
                    slot.isoformat(),
                ),
            )
        return appointment

    def reception_overview(self) -> List[str]:
        """Fornece uma visão geral textual de todos os agendamentos."""
        return [str(appt) for appt in self._appointments]

    def add_appointment(self, appointment: Appointment) -> None:
        """Registra um novo agendamento."""
        self._appointments.append(appointment)
        with self._storage.connection() as conn:
            conn.execute(
                "INSERT INTO appointments (patient_name, doctor_name, scheduled_at, reason, checked_in, checked_in_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    appointment.patient_name,
                    appointment.doctor_name,
                    appointment.scheduled_at.isoformat(),
                    appointment.reason,
                    int(appointment.checked_in),
                    appointment.checked_in_at.isoformat() if appointment.checked_in_at else None,
                ),
            )

    def list_appointments(self) -> None:
        """Imprime os agendamentos existentes."""
        for appt in self._appointments:
            print(appt)

    def all_appointments(self) -> List[Appointment]:
        """Retorna a cópia dos agendamentos carregados em memória."""
        return list(self._appointments)

    def add_test_appointment(self) -> None:
        """Exemplo de fluxo completo com paciente e médico."""
        doctor = Doctor(
            name="Dra. Camila",
            specialty="Clínica geral",
            availability=self._make_sample_schedule(),
        )
        self.add_doctor(doctor)

        patient = self.register_patient(
            name="João Silva", email="joao@exemplo.com", phone="+55 11 99999-0001"
        )

        slots = self.available_slots(doctor.name)
        if slots:
            self.schedule_appointment(
                patient_name=patient.name,
                doctor_name=doctor.name,
                slot=slots[0],
                reason="Consulta de acompanhamento",
            )

    def _make_sample_schedule(self) -> List[datetime]:
        """Gera janelas de 30 minutos começando na hora cheia seguinte."""
        now = datetime.now()
        base = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        return [base + timedelta(minutes=30 * i) for i in range(6)]

    def _booked_slots(self, doctor_name: str) -> Set[datetime]:
        """Acumula os horários que já foram confirmados para o médico."""
        return {
            appt.scheduled_at
            for appt in self._appointments
            if appt.doctor_name == doctor_name
        }

    def _find_appointment(self, patient_name: str, doctor_name: str, slot: datetime) -> Appointment:
        """Busca um agendamento específico."""
        for appt in self._appointments:
            if (
                appt.patient_name == patient_name
                and appt.doctor_name == doctor_name
                and appt.scheduled_at == slot
            ):
                return appt
        raise ValueError(
            f"Nenhum agendamento encontrado para {patient_name} com {doctor_name} em {slot.isoformat()}"
        )
