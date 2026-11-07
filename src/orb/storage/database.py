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
    """Manages SQLite persistence for ORB goals and workflow history."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DATA_DIRECTORY / "orb.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_db(self) -> None:
        """Create the initial schema; all statements are safe to run repeatedly."""
        try:
            with self._get_connection() as connection:
                connection.execute("PRAGMA journal_mode=WAL;")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS goals (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        goal TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id INTEGER,
                        sequence INTEGER,
                        name TEXT,
                        action_type TEXT,
                        status TEXT,
                        FOREIGN KEY(execution_id) REFERENCES executions(id)
                    )
                    """
                )
            logger.info("SQLite database initialized successfully at %s", self.db_path)
        except Exception:
            logger.exception("Failed to initialize SQLite database: %s", self.db_path)
            raise

    def save_goal(
        self,
        *,
        goal_id: str,
        title: str,
        description: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        """Insert a goal or update its mutable fields."""
        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT INTO goals (id, title, description, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (goal_id, title, description, status, created_at, updated_at),
            )

    def fetch_goals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the most recently updated goals."""
        with self._get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM goals ORDER BY updated_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
            return [dict(row) for row in rows]

    def fetch_goal(self, goal_id: str) -> Dict[str, Any] | None:
        """Return one goal by its identifier."""
        with self._get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM goals WHERE id = ?",
                (goal_id,),
            ).fetchone()
            return dict(row) if row else None

    def update_goal_status(self, goal_id: str, status: str, updated_at: str) -> bool:
        """Update a goal status and report whether a row was changed."""
        with self._get_connection() as connection:
            cursor = connection.execute(
                "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?",
                (status, updated_at, goal_id),
            )
            return cursor.rowcount > 0

    def delete_goal(self, goal_id: str) -> bool:
        """Delete one goal and report whether it existed."""
        with self._get_connection() as connection:
            cursor = connection.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
            return cursor.rowcount > 0

    def save_execution(
        self,
        goal: str,
        status: str,
        steps: List[Dict[str, Any]],
    ) -> int:
        """Save a planned or executed workflow record and its steps."""
        try:
            with self._get_connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO executions (goal, status) VALUES (?, ?)",
                    (goal, status),
                )
                execution_id = cursor.lastrowid
                for step in steps:
                    connection.execute(
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
            logger.info("Saved workflow record ID %d to database.", execution_id)
            return execution_id or -1
        except Exception:
            logger.exception("Failed to save workflow record.")
            return -1

    def fetch_recent_executions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch recent workflow records, including plans not yet executed."""
        with self._get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM executions ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
            return [dict(row) for row in rows]

    def fetch_recent_execution_steps(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch recent workflow steps with their parent record information."""
        with self._get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    workflow_steps.id,
                    workflow_steps.execution_id,
                    workflow_steps.sequence,
                    workflow_steps.name,
                    workflow_steps.action_type,
                    workflow_steps.status,
                    executions.goal,
                    executions.status AS execution_status,
                    executions.created_at
                FROM workflow_steps
                INNER JOIN executions
                    ON executions.id = workflow_steps.execution_id
                ORDER BY executions.id DESC, workflow_steps.sequence ASC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
            return [dict(row) for row in rows]
