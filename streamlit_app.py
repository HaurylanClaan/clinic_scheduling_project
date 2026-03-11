"""Interface Streamlit para pacientes, médicos e recepção."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

from clinic.models import Doctor
from clinic.services import Scheduler
from clinic.storage import StorageManager


def _stringify_slot(slot: datetime) -> str:
    return slot.strftime("%Y-%m-%d %H:%M")


def _ensure_database(storage: StorageManager) -> str:
    dbs = storage.list_databases()
    if not dbs:
        storage.create_database("clinic_default")
        dbs = storage.list_databases()
    return dbs[0]


def main() -> None:
    st.set_page_config(page_title="Agenda Clínica", layout="wide")

    storage = StorageManager(Path("data"))
    default_db = _ensure_database(storage)

    with st.sidebar:
        st.header("Base de dados")
        dbs = storage.list_databases()
        if "selected_db" not in st.session_state or st.session_state["selected_db"] not in dbs:
            st.session_state["selected_db"] = default_db
        new_db = st.text_input("Criar novo banco", key="new_db")
        if st.button("Criar banco", key="create_db") and new_db:
            storage.create_database(new_db)
            st.success(f"Banco {new_db} criado")
            st.experimental_rerun()

        selected = st.selectbox(
            "Banco ativo",
            dbs,
            index=dbs.index(st.session_state["selected_db"]),
            key="db_select",
        )
        st.session_state["selected_db"] = selected
        if st.button("Recriar banco atual", key="recreate_db"):
            storage.recreate_database(selected)
            st.success(f"Banco {selected} recriado")
            st.experimental_rerun()
        if st.button("Excluir banco atual", key="delete_db"):
            storage.delete_database(selected)
            storage.clear_selection()
            st.warning(f"Banco {selected} removido")
            st.experimental_rerun()

    storage.select_database(selected)
    scheduler = Scheduler(storage)

    st.title("Clinica de Consultas")
    tabs = st.tabs(["Pacientes", "Médicos", "Visão geral"])

    _render_patient_tab(tabs[0], scheduler)
    _render_doctor_tab(tabs[1], scheduler)
    _render_overview_tab(tabs[2], scheduler)


def _render_patient_tab(tab: st.delta_generator.DeltaGenerator, scheduler: Scheduler) -> None:
    with tab:
        st.subheader("Seção do paciente")
        with st.form("patient_form"):
            name = st.text_input("Nome completo", key="patient_name")
            email = st.text_input("E-mail")
            phone = st.text_input("Telefone")
            submitted = st.form_submit_button("Cadastrar paciente")
        if submitted and name and email and phone:
            scheduler.register_patient(name=name, email=email, phone=phone)
            st.success(f"Paciente {name} registrado")
            st.session_state["last_patient"] = name

        doctor_options = scheduler.list_doctors()
        if not doctor_options:
            st.info("Cadastre um médico na aba Médicos para liberar agendamentos.")
            return

        doctor = st.selectbox("Escolha um médico", doctor_options, format_func=lambda doc: doc.name)
        slots = scheduler.available_slots(doctor.name)
        if not slots:
            st.warning("Nenhum horário disponível no momento para este médico.")
            return
        slot_choice = st.selectbox("Escolha um horário", slots, format_func=_stringify_slot)
        reason = st.text_input("Motivo da consulta")
        if st.button("Agendar consulta") and slot_choice and st.session_state.get("last_patient"):
            scheduler.schedule_appointment(
                patient_name=st.session_state["last_patient"],
                doctor_name=doctor.name,
                slot=slot_choice,
                reason=reason or "Consulta agendada pelo paciente",
            )
            st.success("Consulta agendada com sucesso")

        patient_name = st.session_state.get("last_patient")
        if patient_name:
            st.markdown(f"**Consultas de {patient_name}:**")
            appointments = scheduler.appointments_for_patient(patient_name)
            for appointment in appointments:
                st.write(str(appointment))


def _render_doctor_tab(tab: st.delta_generator.DeltaGenerator, scheduler: Scheduler) -> None:
    with tab:
        st.subheader("Seção dos médicos")
        with st.form("doctor_form"):
            name = st.text_input("Nome do médico", key="doctor_name")
            specialty = st.text_input("Especialidade")
            start_date = st.date_input("Data inicial", value=datetime.now().date())
            start_time = st.time_input("Hora inicial", value=datetime.now().time())
            slots = st.number_input("Quantidade de janelas (30 min)", min_value=1, max_value=12, value=4)
            submitted = st.form_submit_button("Cadastrar médico")
        if submitted and name and specialty:
            start_dt = datetime.combine(start_date, start_time)
            availability = [start_dt + timedelta(minutes=30 * i) for i in range(slots)]
            scheduler.add_doctor(Doctor(name=name, specialty=specialty, availability=availability))
            st.success(f"Médico {name} adicionado com {slots} horários disponíveis")

        doctors = scheduler.list_doctors()
        if not doctors:
            st.info("Adicione médicos para começar.")
            return

        doctor = st.selectbox("Gerenciar agenda de", doctors, format_func=lambda doc: doc.name)
        available_slots = scheduler.available_slots(doctor.name)
        if available_slots:
            action_slot = st.selectbox(
                "Bloquear horário", available_slots, format_func=_stringify_slot, key="block_slot"
            )
            if st.button("Bloquear horário selecionado"):
                scheduler.block_slot(doctor.name, action_slot)
                st.success(f"Horário {_stringify_slot(action_slot)} bloqueado")
        else:
            st.info("Nenhum horário livre para bloquear no momento.")

        st.markdown("**Consultas marcadas:**")
        for appointment in scheduler.doctor_appointments(doctor.name):
            st.write(str(appointment))

        st.markdown("**Horários bloqueados:**")
        for slot in doctor.blocked_slots:
            st.write(_stringify_slot(slot))


def _render_overview_tab(tab: st.delta_generator.DeltaGenerator, scheduler: Scheduler) -> None:
    with tab:
        st.subheader("Visão geral da recepção")
        appointments = scheduler.all_appointments()
        total = len(appointments)
        blocked = sum(len(doc.blocked_slots) for doc in scheduler.list_doctors())
        available_doctors = len(scheduler.list_doctors())
        waiting = sum(1 for appt in appointments if not appt.checked_in)

        cols = tab.columns(4)
        cols[0].metric("Consultas totais", total)
        cols[1].metric("Horários bloqueados", blocked)
        cols[2].metric("Médicos disponíveis", available_doctors)
        cols[3].metric("Pessoas esperando", waiting)

        tab.markdown("**Agenda completa:**")
        for appointment in appointments:
            tab.write(str(appointment))

        if appointments:
            option_map = {
                f"{_stringify_slot(appt.scheduled_at)} - {appt.patient_name}": appt for appt in appointments
            }
            selection = tab.selectbox("Check-in (selecione a consulta)", list(option_map.keys()))
            if tab.button("Registrar chegada"):
                picked = option_map[selection]
                scheduler.check_in(picked.patient_name, picked.doctor_name, picked.scheduled_at)
                tab.success("Check-in registrado")


if __name__ == "__main__":
    main()
