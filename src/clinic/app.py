"""Ponto de entrada minimalista para o serviço de agendamento."""

from .services.scheduler import Scheduler


def run_scheduler():
    """Simula o ciclo de agendamentos."""
    scheduler = Scheduler()
    scheduler.add_test_appointment()
    scheduler.list_appointments()  # Apenas demonstração

