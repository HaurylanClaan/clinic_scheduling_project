"""Entidade médica com janelas de disponibilidade."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Doctor:
    name: str
    specialty: str
    availability: List[datetime]
    blocked_slots: List[datetime] = field(default_factory=list)
