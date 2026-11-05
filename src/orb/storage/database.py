
"""
=============================================================
ORB Platform
SQLite Persistence Layer

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List

from orb.core.constants import DATA_DIRECTORY
from orb.logging import get_logger

logger = get_logger("storage.db")


class ORBDatabase:
    """Manages SQLite database operations for ORB state persistence."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = (
            Path(db_path)
            if db_path is not None
            else DATA_DIRECTORY / "orb.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema with WAL mode."""
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        goal TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id INTEGER,
                        sequence INTEGER,
                        name TEXT,
                        action_type TEXT,
                        status TEXT,
                        FOREIGN KEY(execution_id) REFERENCES executions(id)
                    )
                """)

            logger.info(
                "SQLite database initialized successfully at %s",
                self.db_path,
            )

        except Exception:
            logger.exception(
                "Failed to initialize SQLite database: %s",
                self.db_path,
            )
            raise

    def save_execution(
        self,
        goal: str,
        status: str,
        steps: List[Dict[str, Any]],
    ) -> int:
        """Save a goal execution and its steps into the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO executions (goal, status) VALUES (?, ?)",
                    (goal, status),
                )

                execution_id = cursor.lastrowid

                for step in steps:
                    cursor.execute(
                        """
                        INSERT INTO workflow_steps
                        (execution_id, sequence, name, action_type, status)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            execution_id,
                            step.get("sequence", 1),
                            step.get("name", ""),
                            step.get("action_type", ""),
                            str(step.get("status", "PENDING")),
                        ),
                    )

            logger.info("Saved execution ID %d to database.", execution_id)
            return execution_id or -1

        except Exception:
            logger.exception("Failed to save execution to database.")
            return -1

    def fetch_recent_executions(
        self,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fetch recent executions from the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM executions ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception:
            logger.exception("Failed to fetch executions.")
            return []
