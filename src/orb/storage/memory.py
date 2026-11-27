"""Persistent notes explicitly saved by the user."""

import sqlite3
from contextlib import closing
from pathlib import Path

from orb.core.constants import MEMORY_DIRECTORY


class MemoryStore:
    def __init__(self, path: Path = MEMORY_DIRECTORY / "notes.db"):
        self.path = path

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def notes(self) -> list[tuple[int, str]]:
        if not self.path.exists():
            return []
        with closing(self._connect()) as db:
            return db.execute("SELECT id, text FROM notes ORDER BY id DESC").fetchall()

    def save(self, text: str) -> None:
        text = text.strip()
        if not text or len(text) > 4000:
            raise ValueError("Enter a note between 1 and 4,000 characters.")
        with closing(self._connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
            db.execute("INSERT INTO notes (text) VALUES (?)", (text,))

    def delete(self, note_id: int) -> None:
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
