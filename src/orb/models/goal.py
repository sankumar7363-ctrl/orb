"""
ORB Platform
Goal Model
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import uuid4


class GoalStatus(StrEnum):
    """Possible lifecycle states for an ORB goal."""

    CREATED = "created"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    """Represent a user goal inside ORB."""

    title: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    status: GoalStatus = GoalStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_status(self, status: GoalStatus) -> None:
        """Update the goal status."""

        self.status = status
        self.updated_at = datetime.now()