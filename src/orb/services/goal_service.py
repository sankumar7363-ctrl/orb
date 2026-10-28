"""
ORB Platform
Goal Service
"""

from orb.models.goal import Goal


class GoalService:
    """Manage goals inside ORB."""

    def __init__(self) -> None:
        self._goals: list[Goal] = []

    def create_goal(
        self,
        title: str,
        description: str = "",
    ) -> Goal:
        """Create and store a new goal."""

        title = title.strip()

        if not title:
            raise ValueError("Goal title cannot be empty.")

        goal = Goal(
            title=title,
            description=description.strip(),
        )

        self._goals.append(goal)

        return goal

    def get_goals(self) -> list[Goal]:
        """Return all goals."""

        return list(self._goals)

    def get_goal(self, goal_id: str) -> Goal | None:
        """Find a goal by ID."""

        for goal in self._goals:
            if goal.id == goal_id:
                return goal

        return None

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal by ID."""

        for goal in self._goals:
            if goal.id == goal_id:
                self._goals.remove(goal)
                return True

        return False