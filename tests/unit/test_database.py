"""Unit tests for ORB SQLite persistence."""

from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orb.storage.database import ORBDatabase


class DatabaseTests(unittest.TestCase):

    def test_uses_default_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            expected_directory = Path(directory) / "data"

            with patch(
                "orb.storage.database.DATA_DIRECTORY",
                expected_directory
            ):
                db = ORBDatabase()

            self.assertEqual(
                db.db_path,
                expected_directory / "orb.db"
            )
            self.assertTrue(db.db_path.exists())

    def test_accepts_custom_database_path(self):
        with tempfile.TemporaryDirectory() as directory:
            custom_path = Path(directory) / "custom" / "test.db"

            db = ORBDatabase(custom_path)

            self.assertEqual(db.db_path, custom_path)
            self.assertTrue(custom_path.exists())

    def test_creates_missing_parent_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "nested" / "folder" / "orb.db"

            ORBDatabase(db_path)

            self.assertTrue(db_path.parent.exists())
            self.assertTrue(db_path.exists())

    def test_saves_execution_and_workflow_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            db = ORBDatabase(Path(directory) / "orb.db")

            steps = [
                {
                    "sequence": 1,
                    "name": "Analyze goal",
                    "action_type": "ANALYSIS",
                    "status": "COMPLETED",
                },
                {
                    "sequence": 2,
                    "name": "Execute task",
                    "action_type": "EXECUTION",
                    "status": "PENDING",
                },
            ]

            execution_id = db.save_execution(
                goal="Build ORB",
                status="IN_PROGRESS",
                steps=steps,
            )

            self.assertGreater(execution_id, 0)

            with closing(sqlite3.connect(db.db_path)) as conn:
                execution = conn.execute(
                    "SELECT goal, status FROM executions WHERE id = ?",
                    (execution_id,),
                ).fetchone()

                saved_steps = conn.execute(
                    """
                    SELECT sequence, name, action_type, status
                    FROM workflow_steps
                    WHERE execution_id = ?
                    ORDER BY sequence
                    """,
                    (execution_id,),
                ).fetchall()

            self.assertEqual(
                execution,
                ("Build ORB", "IN_PROGRESS")
            )
            self.assertEqual(len(saved_steps), 2)
            self.assertEqual(saved_steps[0][1], "Analyze goal")
            self.assertEqual(saved_steps[1][1], "Execute task")

    def test_fetches_recent_executions(self):
        with tempfile.TemporaryDirectory() as directory:
            db = ORBDatabase(Path(directory) / "orb.db")

            db.save_execution("Goal One", "COMPLETED", [])
            db.save_execution("Goal Two", "COMPLETED", [])
            db.save_execution("Goal Three", "FAILED", [])

            results = db.fetch_recent_executions(limit=2)

            self.assertEqual(len(results), 2)
            self.assertEqual(
                [item["goal"] for item in results],
                ["Goal Three", "Goal Two"]
            )


if __name__ == "__main__":
    unittest.main()