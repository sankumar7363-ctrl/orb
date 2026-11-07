"""Unit tests for the persistent ORB goal service."""

import tempfile
import unittest
from pathlib import Path

from orb.models.goal import GoalStatus
from orb.services.goal_service import GoalService
from orb.storage.database import ORBDatabase


class GoalServiceTests(unittest.TestCase):
    def test_goals_survive_service_recreation(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "orb.db"
            first_service = GoalService(ORBDatabase(database_path))
            created = first_service.create_goal(
                "Build ORB dashboard",
                "Use the glassmorphism reference.",
            )

            second_service = GoalService(ORBDatabase(database_path))
            loaded = second_service.get_goal(created.id)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.title, "Build ORB dashboard")
            self.assertEqual(loaded.description, "Use the glassmorphism reference.")
            self.assertEqual(loaded.status, GoalStatus.CREATED)

    def test_rejects_blank_goal_title(self):
        with tempfile.TemporaryDirectory() as directory:
            service = GoalService(ORBDatabase(Path(directory) / "orb.db"))
            with self.assertRaises(ValueError):
                service.create_goal("   ")

    def test_updates_and_deletes_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            service = GoalService(ORBDatabase(Path(directory) / "orb.db"))
            goal = service.create_goal("Test goal")
            self.assertTrue(service.update_status(goal.id, GoalStatus.PLANNING))
            self.assertEqual(service.get_goal(goal.id).status, GoalStatus.PLANNING)
            self.assertTrue(service.delete_goal(goal.id))
            self.assertIsNone(service.get_goal(goal.id))


if __name__ == "__main__":
    unittest.main()
