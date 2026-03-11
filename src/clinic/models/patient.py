"""Dados básicos de um paciente."""

from dataclasses import dataclass


@dataclass
class Patient:
    name: str
    email: str
    phone: str
