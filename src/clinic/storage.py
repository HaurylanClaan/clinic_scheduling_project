"""Gerencia os arquivos SQLite usados como 'mini bancos' da clínica."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    name TEXT PRIMARY KEY,
    email TEXT,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS doctors (
    name TEXT PRIMARY KEY,
    specialty TEXT
);

CREATE TABLE IF NOT EXISTS doctor_availability (
    doctor_name TEXT,
    slot TEXT,
    PRIMARY KEY (doctor_name, slot),
    FOREIGN KEY (doctor_name) REFERENCES doctors(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS doctor_blocked_slots (
    doctor_name TEXT,
    slot TEXT,
    PRIMARY KEY (doctor_name, slot),
    FOREIGN KEY (doctor_name) REFERENCES doctors(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    doctor_name TEXT,
    scheduled_at TEXT,
    reason TEXT,
    checked_in INTEGER,
    checked_in_at TEXT,
    FOREIGN KEY (patient_name) REFERENCES patients(name),
    FOREIGN KEY (doctor_name) REFERENCES doctors(name)
);
"""


@dataclass
class StorageManager:
    """Controla múltiplos bancos SQLite no disco."""

    root: Path
    _database: Optional[str] = None

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def database_file(self, name: str) -> Path:
        return self.root / f"{name}.db"

    def list_databases(self) -> List[str]:
        return sorted(path.stem for path in self.root.glob("*.db"))

    def create_database(self, name: str, *, overwrite: bool = False) -> Path:
        path = self.database_file(name)
        if path.exists():
            if not overwrite:
                return path
            path.unlink()
        with sqlite3.connect(path) as conn:
            conn.executescript(_SCHEMA)
        return path

    def delete_database(self, name: str) -> None:
        path = self.database_file(name)
        if path.exists():
            path.unlink()

    def select_database(self, name: str, *, create_if_missing: bool = True) -> Path:
        path = self.database_file(name)
        if not path.exists():
            if create_if_missing:
                self.create_database(name)
            else:
                raise FileNotFoundError(f"Banco {name} não existe")
        self._database = name
        self._ensure_schema()
        return path

    def recreate_database(self, name: str) -> Path:
        """Limpa e cria novamente o mesmo banco."""
        self.create_database(name, overwrite=True)
        self._database = name
        self._ensure_schema()
        return self.database_file(name)

    def _ensure_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(_SCHEMA)

    def connection(self) -> sqlite3.Connection:
        if not self._database:
            raise RuntimeError("Nenhum banco selecionado")
        conn = sqlite3.connect(self.database_file(self._database))
        conn.row_factory = sqlite3.Row
        return conn

    @property
    def current_database(self) -> Optional[str]:
        return self._database

    @property
    def current_path(self) -> Optional[Path]:
        if not self._database:
            return None
        return self.database_file(self._database)

    def __repr__(self) -> str:
        return f"StorageManager(root={self.root}, current={self._database})"

    def clear_selection(self) -> None:
        self._database = None
