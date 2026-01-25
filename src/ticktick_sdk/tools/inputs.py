"""Consolidated Pydantic Input Models for TickTick SDK Tools.

Phase 4: Action-based routing consolidates 43 tools → 6 tools.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, List, Literal, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class ResponseFormat(str, Enum):
    """Output format."""
    MARKDOWN = "markdown"
    JSON = "json"


class ResponseDetail(str, Enum):
    """Detail level. Lower = fewer tokens."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


# =============================================================================
# Consolidated Tasks Input
# =============================================================================


class TasksInput(BaseModel):
    """All task operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["create", "get", "list", "update", "complete", "delete", "move", "pin", "search", "set_parents", "unparent"]

    # Response options
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    # For create: list of task specs
    tasks: Optional[List[dict]] = Field(default=None)

    # For get
    task_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{24}$")

    # For list filtering
    status: Optional[Literal["active", "completed", "abandoned", "deleted"]] = Field(default=None)
    project_id: Optional[str] = Field(default=None, pattern=r"^(inbox\d+|[a-f0-9]{24})$")
    column_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{24}$")
    tag: Optional[str] = Field(default=None)
    priority: Optional[str] = Field(default=None, pattern=r"^(none|low|medium|high)$")
    due_today: Optional[bool] = Field(default=None)
    overdue: Optional[bool] = Field(default=None)
    from_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: Optional[int] = Field(default=None, ge=1, le=90)
    limit: Optional[int] = Field(default=None, ge=1, le=500)

    # For search
    query: Optional[str] = Field(default=None, min_length=1, max_length=200)

    # For move: list of {task_id, from_project_id, to_project_id}
    moves: Optional[List[dict]] = Field(default=None)

    @model_validator(mode="after")
    def validate_action_params(self) -> "TasksInput":
        a = self.action
        if a == "create" and not self.tasks:
            raise ValueError("create requires tasks")
        if a == "get" and not self.task_id:
            raise ValueError("get requires task_id")
        if a in ("update", "complete", "delete", "pin", "set_parents", "unparent") and not self.tasks:
            raise ValueError(f"{a} requires tasks")
        if a == "move" and not self.moves:
            raise ValueError("move requires moves")
        if a == "search" and not self.query:
            raise ValueError("search requires query")
        return self


# =============================================================================
# Consolidated Projects Input
# =============================================================================


class ProjectsInput(BaseModel):
    """All project operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["list", "get", "create", "update", "delete"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    # For get/update/delete
    project_id: Optional[str] = Field(default=None, pattern=r"^(inbox\d+|[a-f0-9]{24})$")

    # For get
    include_tasks: Optional[bool] = Field(default=None)

    # For create/update
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    kind: Optional[str] = Field(default=None, pattern=r"^(TASK|NOTE)$")
    view_mode: Optional[str] = Field(default=None, pattern=r"^(list|kanban|timeline)$")
    folder_id: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_action_params(self) -> "ProjectsInput":
        a = self.action
        if a == "create" and not self.name:
            raise ValueError("create requires name")
        if a in ("get", "update", "delete") and not self.project_id:
            raise ValueError(f"{a} requires project_id")
        return self


# =============================================================================
# Consolidated Folders Input
# =============================================================================


class FoldersInput(BaseModel):
    """All folder operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["list", "create", "rename", "delete"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    # For rename/delete
    folder_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{24}$")

    # For create/rename
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_action_params(self) -> "FoldersInput":
        a = self.action
        if a == "create" and not self.name:
            raise ValueError("create requires name")
        if a in ("rename", "delete") and not self.folder_id:
            raise ValueError(f"{a} requires folder_id")
        if a == "rename" and not self.name:
            raise ValueError("rename requires name")
        return self


# =============================================================================
# Consolidated Tags Input
# =============================================================================


class TagsInput(BaseModel):
    """All tag operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["list", "create", "update", "delete", "merge"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    # For create/update/delete
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)

    # For create/update
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    parent: Optional[str] = Field(default=None)

    # For update (rename)
    label: Optional[str] = Field(default=None, min_length=1, max_length=50)

    # For merge
    source: Optional[str] = Field(default=None, min_length=1, max_length=50)
    target: Optional[str] = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_action_params(self) -> "TagsInput":
        a = self.action
        if a in ("create", "update", "delete") and not self.name:
            raise ValueError(f"{a} requires name")
        if a == "merge" and (not self.source or not self.target):
            raise ValueError("merge requires source and target")
        return self


# =============================================================================
# Consolidated Habits Input
# =============================================================================


class HabitsInput(BaseModel):
    """All habit operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["list", "get", "sections", "create", "update", "delete", "checkin", "checkins"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    # For get/update/delete
    habit_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{24}$")

    # For list
    include_archived: Optional[bool] = Field(default=None)

    # For create/update
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    habit_type: Optional[str] = Field(default=None, pattern=r"^(Boolean|Real)$")
    goal: Optional[float] = Field(default=None, ge=0.1, le=10000)
    step: Optional[float] = Field(default=None, ge=0.1, le=1000)
    unit: Optional[str] = Field(default=None, max_length=20)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    section_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{24}$")
    repeat_rule: Optional[str] = Field(default=None)
    reminders: Optional[List[str]] = Field(default=None, max_length=5)
    target_days: Optional[int] = Field(default=None, ge=0, le=1000)
    encouragement: Optional[str] = Field(default=None, max_length=200)
    archived: Optional[bool] = Field(default=None)

    # For checkin: list of {habit_id, value, checkin_date}
    checkins: Optional[List[dict]] = Field(default=None)

    # For checkins (history)
    habit_ids: Optional[List[str]] = Field(default=None)
    after_stamp: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_action_params(self) -> "HabitsInput":
        a = self.action
        if a in ("get", "update", "delete") and not self.habit_id:
            raise ValueError(f"{a} requires habit_id")
        if a == "create" and not self.name:
            raise ValueError("create requires name")
        if a == "checkin" and not self.checkins:
            raise ValueError("checkin requires checkins")
        if a == "checkins" and not self.habit_ids:
            raise ValueError("checkins requires habit_ids")
        return self


# =============================================================================
# Columns Input (kept separate, can be filtered)
# =============================================================================


class ColumnsInput(BaseModel):
    """Kanban column operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["list", "create", "update", "delete"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    project_id: Optional[str] = Field(default=None, pattern=r"^(inbox\d+|[a-f0-9]{24})$")
    column_id: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{24}$")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    sort_order: Optional[int] = Field(default=None)

    @model_validator(mode="after")
    def validate_action_params(self) -> "ColumnsInput":
        a = self.action
        if a == "list" and not self.project_id:
            raise ValueError("list requires project_id")
        if a == "create" and (not self.project_id or not self.name):
            raise ValueError("create requires project_id and name")
        if a in ("update", "delete") and (not self.column_id or not self.project_id):
            raise ValueError(f"{a} requires column_id and project_id")
        return self


# =============================================================================
# User Input (kept separate, can be filtered)
# =============================================================================


class UserInput(BaseModel):
    """User/account operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["profile", "status", "statistics", "preferences"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# =============================================================================
# Focus Input (kept separate, can be filtered)
# =============================================================================


class FocusInput(BaseModel):
    """Focus/pomodoro operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: Literal["heatmap", "by_tag"]

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    start_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: Optional[int] = Field(default=None, ge=1, le=365)
