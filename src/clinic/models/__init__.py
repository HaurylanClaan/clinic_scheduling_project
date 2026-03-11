"""Modelos que descrevem pacientes, médicos e compromissos."""

from .appointment import Appointment
from .doctor import Doctor
from .patient import Patient

__all__ = ["Appointment", "Doctor", "Patient"]
