"""Interface Streamlit para pacientes, médicos e recepção."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from clinic.models import Doctor
from clinic.services import Scheduler
from clinic.storage import StorageManager

CARD_STYLE = """
<style>
.metric-card {
    background: #fff;
    border-radius: 20px;
    padding: 1.2rem;
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
    border: 1px solid rgba(15, 23, 42, 0.08);
}
.metric-icon {
    font-size: 1.4rem;
    margin-right: 0.5rem;
}
.metric-label {
    color: #666;
    font-size: 13px;
}
.metric-value {
    font-size: 2rem;
    font-weight: 600;
    margin-top: 0.25rem;
}
</style>
"""


def _stringify_slot(slot: datetime) -> str:
    return slot.strftime("%Y-%m-%d %H:%M")


def _ensure_database(storage: StorageManager) -> str:
    dbs = storage.list_databases()
    if not dbs:
        storage.create_database("clinic_default")
        dbs = storage.list_databases()
    return dbs[0]


def _metric_card(label: str, value: int, caption: str, icon: str) -> str:
    return f"""
    <div class="metric-card">
        <div><span class="metric-icon">{icon}</span><span class="metric-label">{label}</span></div>
        <div class="metric-value">{value}</div>
        <div style="color:#999; font-size: 12px;">{caption}</div>
    </div>
    """


def _render_reception_panel(scheduler: Scheduler) -> None:
    st.markdown(CARD_STYLE, unsafe_allow_html=True)
    appointments = scheduler.all_appointments()
    today = datetime.now().date()
    consults_today = sum(1 for appt in appointments if appt.scheduled_at and appt.scheduled_at.date() == today)
    waiting = sum(1 for appt in appointments if not appt.checked_in)
    checked_in = sum(1 for appt in appointments if appt.checked_in)
    doctors = scheduler.list_doctors()

    header_col, button_col = st.columns([4, 1])
    with header_col:
        st.header("Painel da Recepção")
        st.caption(f"{datetime.now():%A, %d de %B}")
    with button_col:
        if st.button("+ Novo Agendamento"):
            st.info("Use o perfil de Paciente para cadastrar a nova consulta.")

    card_cols = st.columns(3)
    metrics = [
        ("Consultas Hoje", consults_today, "Consultas previstas para hoje", "📅"),
        ("Aguardando", waiting, "Pacientes aguardando check-in", "🧍"),
        ("Check-in Feito", checked_in, "Pacientes que já chegaram", "✅"),
    ]
    for col, metric in zip(card_cols, metrics):
        col.markdown(_metric_card(*metric), unsafe_allow_html=True)

    st.markdown("#### Agenda Semanal")
    nav_col, filter_col = st.columns([3, 1])
    with nav_col:
        st.write(" ")
        n1, n2, n3 = st.columns([1, 2, 1])
        n1.button("<")
        n2.markdown(f"**{datetime.now():%d %b %Y}**", unsafe_allow_html=True)
        n3.button(">")
    doctor_options = ["Todos os médicos"] + [doc.name for doc in doctors]
    selected_doctor = filter_col.selectbox("Todos os médicos", doctor_options)

    df = _build_week_df(appointments, doctors, None if selected_doctor == "Todos os médicos" else selected_doctor)
    st.dataframe(df, use_container_width=True, height=420)


def _build_week_df(appointments, doctors, doctor_filter: Optional[str]) -> pd.DataFrame:
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    day_names = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    day_labels = [
        f"{name} {(monday + timedelta(days=i)).day}" for i, name in enumerate(day_names)
    ]
    slots = [f"{hour:02d}:{minute:02d}" for hour in range(8, 13) for minute in (0, 30)]
    data = {label: [""] * len(slots) for label in day_labels}

    for appointment in appointments:
        slot = appointment.scheduled_at
        if not slot or slot.weekday() >= 5:
            continue
        if doctor_filter and appointment.doctor_name != doctor_filter:
            continue
        time_label = slot.strftime("%H:%M")
        if time_label not in slots:
            continue
        day_label = day_labels[slot.weekday()]
        index = slots.index(time_label)
        if not data[day_label][index]:
            data[day_label][index] = appointment.patient_name

    for doctor in doctors:
        if doctor_filter and doctor.name != doctor_filter:
            continue
        for blocked in doctor.blocked_slots:
            if not blocked or blocked.weekday() >= 5:
                continue
            time_label = blocked.strftime("%H:%M")
            if time_label not in slots:
                continue
            day_label = day_labels[blocked.weekday()]
            index = slots.index(time_label)
            if not data[day_label][index]:
                data[day_label][index] = "Bloqueado"

    df = pd.DataFrame(data, index=slots)
    df.index.name = "Horários"
    return df


def main() -> None:
    st.set_page_config(page_title="Agenda Clínica", layout="wide")

    storage = StorageManager(Path("data"))
    default_db = _ensure_database(storage)

    with st.sidebar:
        st.header("MedAgenda")
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

        st.markdown("---")
        profile = st.radio(
            "Perfil (demo)",
            ["Recepção", "Médico(a)", "Paciente"],
            index=0,
        )

    storage.select_database(selected)
    scheduler = Scheduler(storage)

    if profile == "Recepção":
        _render_reception_panel(scheduler)
    elif profile == "Médico(a)":
        _render_doctor_section(scheduler)
    else:
        _render_patient_section(scheduler)


def _render_patient_section(scheduler: Scheduler) -> None:
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


def _render_doctor_section(scheduler: Scheduler) -> None:
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


if __name__ == "__main__":
    main()
