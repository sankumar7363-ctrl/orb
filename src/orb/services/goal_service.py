"""
ORB Platform
Goal Service

Goals are persisted through the ORB SQLite data-access layer.
"""

from __future__ import annotations

from datetime import datetime

from orb.models.goal import Goal, GoalStatus
from orb.storage.database import ORBDatabase


class GoalService:
    """Create, retrieve, update, and delete persistent ORB goals."""

    def __init__(self, database: ORBDatabase | None = None) -> None:
        self._database = database or ORBDatabase()

    def create_goal(self, title: str, description: str = "") -> Goal:
        """Validate and persist a new goal."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Goal title cannot be empty.")

        goal = Goal(title=clean_title, description=description.strip())
        self._database.save_goal(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            status=goal.status.value,
            created_at=goal.created_at.isoformat(),
            updated_at=goal.updated_at.isoformat(),
        )
        return goal

    def get_goals(self) -> list[Goal]:
        """Return persisted goals, newest updates first."""
        return [self._to_goal(row) for row in self._database.fetch_goals()]

    def get_goal(self, goal_id: str) -> Goal | None:
        """Find a persisted goal by ID."""
        row = self._database.fetch_goal(goal_id)
        return self._to_goal(row) if row else None

    def update_status(self, goal_id: str, status: GoalStatus) -> bool:
        """Update a goal lifecycle state."""
        return self._database.update_goal_status(
            goal_id,
            status.value,
            datetime.now().isoformat(),
        )

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal by ID."""
        return self._database.delete_goal(goal_id)

    @staticmethod
    def _to_goal(row: dict) -> Goal:
        """Convert a database row into the typed goal model."""
        try:
            status = GoalStatus(row["status"])
        except ValueError:
            status = GoalStatus.CREATED

        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])

        return Goal(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=status,
            created_at=created_at,
            updated_at=updated_at,
        )
