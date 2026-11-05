"""
=============================================================
ORB Platform
Core Domain Models (Pydantic Schemas)

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    WAITING = "waiting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PASSED = "passed"
    FAILED_SAFE = "failed_safe"
    FAILED_CRITICAL = "failed_critical"


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    priority: int = 1
    status: str = "planning"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    parent_step_id: Optional[str] = None
    sequence: int
    name: str
    action_type: str  # e.g., File.Read, Sandbox.PythonExecute, Browser.Navigate
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    requires_approval: bool = False

    # Verifier and Safety Integration
    expected_outcome: Dict[str, Any] = Field(default_factory=dict, description="Criteria for Verifier to check (e.g. file_exists)")
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED


class Plan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    goal_id: str
    version: int = 1
    steps: List[WorkflowStep] = Field(default_factory=list)
    required_capabilities: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    risk_level: str = "low"  # low, medium, high
    status: str = "created"
