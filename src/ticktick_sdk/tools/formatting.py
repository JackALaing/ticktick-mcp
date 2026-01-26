"""
Response Formatting Utilities for TickTick SDK Tools.

This module provides consistent formatting for tool responses
in both Markdown and JSON formats.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from ticktick_sdk.models import Column, Task, Project, ProjectGroup, Tag
from ticktick_sdk.tools.inputs import ResponseFormat

# Maximum response size in characters
CHARACTER_LIMIT = 25000


def format_datetime(dt: datetime | None) -> str:
    """Format a datetime for human-readable display."""
    if dt is None:
        return "Not set"
    return dt.strftime("%Y-%m-%d %H:%M %Z").strip()


def format_date(dt: datetime | None) -> str:
    """Format a date for human-readable display."""
    if dt is None:
        return "Not set"
    return dt.strftime("%Y-%m-%d")


def priority_label(priority: int) -> str:
    """Convert priority int to label."""
    labels = {0: "None", 1: "Low", 3: "Medium", 5: "High"}
    return labels.get(priority, "None")


def status_label(status: int) -> str:
    """Convert status int to label."""
    labels = {-1: "Abandoned", 0: "Active", 1: "Completed", 2: "Completed"}
    return labels.get(status, "Unknown")


# =============================================================================
# Task Formatting
# =============================================================================


def format_task_markdown(task: Task) -> str:
    """Format a single task as Markdown."""
    lines = []
    title = task.title or "(No title)"

    lines.append(f"## {title}")
    lines.append("")
    lines.append(f"- **ID**: `{task.id}`")
    lines.append(f"- **Project**: `{task.project_id}`")
    lines.append(f"- **Status**: {status_label(task.status)}")
    lines.append(f"- **Priority**: {priority_label(task.priority)}")

    if task.kind and task.kind != "TEXT":
        lines.append(f"- **Type**: {task.kind}")

    if task.start_date:
        lines.append(f"- **Start**: {format_datetime(task.start_date)}")

    if task.due_date:
        lines.append(f"- **Due**: {format_datetime(task.due_date)}")

    if task.tags:
        tags_str = ", ".join(f"`{t}`" for t in task.tags)
        lines.append(f"- **Tags**: {tags_str}")

    if task.content:
        lines.append("")
        lines.append("### Notes")
        lines.append(task.content)

    if task.items:
        lines.append("")
        lines.append("### Checklist")
        for item in task.items:
            checkbox = "[x]" if item.is_completed else "[ ]"
            lines.append(f"- {checkbox} {item.title or '(No title)'}")

    return "\n".join(lines)


def format_task_json(task: Task, include_content: bool = True) -> dict[str, Any]:
    """Format a single task as JSON. Includes all user-facing fields."""
    result: dict[str, Any] = {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
    }
    if include_content and task.content:
        result["content"] = task.content
    if task.kind and task.kind != "TEXT":
        result["kind"] = task.kind
    if task.start_date:
        result["start_date"] = task.start_date.isoformat()
    if task.due_date:
        result["due_date"] = task.due_date.isoformat()
    if task.tags:
        result["tags"] = task.tags
    if task.parent_id:
        result["parent_id"] = task.parent_id
    if include_content and task.items:
        result["items"] = [
            {"id": item.id, "title": item.title, "completed": item.is_completed}
            for item in task.items
        ]
    return result


def format_tasks_markdown(tasks: list[Task], title: str = "Tasks") -> str:
    """Format multiple tasks as Markdown list."""
    if not tasks:
        return f"# {title}\n\nNo tasks found."

    lines = [f"# {title}", "", f"Found {len(tasks)} task(s):", ""]

    for task in tasks:
        task_title = task.title or "(No title)"
        parts = [f"**{task_title}** (`{task.id}`)"]

        if task.priority and task.priority > 0:
            parts.append(priority_label(task.priority))
        if task.due_date:
            parts.append(f"Due: {format_date(task.due_date)}")
        if task.tags:
            parts.append(f"Tags: {', '.join(task.tags)}")

        lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)


def format_tasks_json(tasks: list[Task]) -> dict[str, Any]:
    """Format multiple tasks as JSON. Excludes content for list views."""
    return {
        "count": len(tasks),
        "tasks": [format_task_json(t, include_content=False) for t in tasks],
    }


# =============================================================================
# Project Formatting
# =============================================================================


def format_project_markdown(project: Project) -> str:
    """Format a single project as Markdown."""
    lines = []

    lines.append(f"## {project.name}")
    lines.append("")
    lines.append(f"- **ID**: `{project.id}`")

    if project.kind and project.kind != "TASK":
        lines.append(f"- **Kind**: {project.kind}")
    if project.view_mode and project.view_mode != "list":
        lines.append(f"- **View Mode**: {project.view_mode}")
    if project.color:
        lines.append(f"- **Color**: {project.color}")
    if project.group_id:
        lines.append(f"- **Folder**: `{project.group_id}`")
    if project.closed:
        lines.append("- **Status**: Archived")

    return "\n".join(lines)


def format_project_json(project: Project) -> dict[str, Any]:
    """Format a single project as JSON."""
    result: dict[str, Any] = {"id": project.id, "name": project.name}
    if project.kind and project.kind != "TASK":
        result["kind"] = project.kind
    if project.view_mode and project.view_mode != "list":
        result["view_mode"] = project.view_mode
    if project.color:
        result["color"] = project.color
    if project.group_id:
        result["folder_id"] = project.group_id
    return result


def format_projects_markdown(projects: list[Project], title: str = "Projects") -> str:
    """Format multiple projects as Markdown."""
    if not projects:
        return f"# {title}\n\nNo projects found."

    lines = [f"# {title}", "", f"Found {len(projects)} project(s):", ""]

    for project in projects:
        parts = [f"**{project.name}** (`{project.id}`)"]
        if project.view_mode and project.view_mode != "list":
            parts.append(project.view_mode)
        if project.color:
            parts.append(project.color)
        lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)


def format_projects_json(projects: list[Project]) -> dict[str, Any]:
    """Format multiple projects as JSON."""
    return {
        "count": len(projects),
        "projects": [format_project_json(p) for p in projects],
    }


# =============================================================================
# Tag Formatting
# =============================================================================


def format_tag_markdown(tag: Tag) -> str:
    """Format a single tag as Markdown."""
    lines = []
    lines.append(f"## {tag.label}")
    lines.append("")
    lines.append(f"- **Name**: `{tag.name}`")
    if tag.color:
        lines.append(f"- **Color**: {tag.color}")
    if tag.parent:
        lines.append(f"- **Parent**: `{tag.parent}`")
    return "\n".join(lines)


def format_tag_json(tag: Tag) -> dict[str, Any]:
    """Format a single tag as JSON."""
    result: dict[str, Any] = {"name": tag.name, "label": tag.label}
    if tag.color:
        result["color"] = tag.color
    if tag.parent:
        result["parent"] = tag.parent
    return result


def format_tags_markdown(tags: list[Tag], title: str = "Tags") -> str:
    """Format multiple tags as Markdown."""
    if not tags:
        return f"# {title}\n\nNo tags found."

    lines = [f"# {title}", "", f"Found {len(tags)} tag(s):", ""]

    for tag in tags:
        parts = [f"**{tag.label}** (`{tag.name}`)"]
        if tag.color:
            parts.append(tag.color)
        if tag.parent:
            parts.append(f"in {tag.parent}")
        lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)


def format_tags_json(tags: list[Tag]) -> dict[str, Any]:
    """Format multiple tags as JSON."""
    return {
        "count": len(tags),
        "tags": [format_tag_json(t) for t in tags],
    }


# =============================================================================
# Folder Formatting
# =============================================================================


def format_folder_markdown(folder: ProjectGroup) -> str:
    """Format a single folder as Markdown."""
    return f"- **{folder.name}** (`{folder.id}`)"


def format_folder_json(folder: ProjectGroup) -> dict[str, Any]:
    """Format a single folder as JSON."""
    return {"id": folder.id, "name": folder.name}


def format_folders_markdown(folders: list[ProjectGroup], title: str = "Folders") -> str:
    """Format multiple folders as Markdown."""
    if not folders:
        return f"# {title}\n\nNo folders found."

    lines = [f"# {title}", "", f"Found {len(folders)} folder(s):", ""]
    for folder in folders:
        lines.append(format_folder_markdown(folder))
    return "\n".join(lines)


def format_folders_json(folders: list[ProjectGroup]) -> dict[str, Any]:
    """Format multiple folders as JSON."""
    return {
        "count": len(folders),
        "folders": [format_folder_json(f) for f in folders],
    }


# =============================================================================
# Column Formatting (Kanban)
# =============================================================================


def format_column_markdown(column: Column) -> str:
    """Format a single column as Markdown."""
    return f"- **{column.name}** (`{column.id}`)"


def format_column_json(column: Column) -> dict[str, Any]:
    """Format a single column as JSON."""
    return {
        "id": column.id,
        "project_id": column.project_id,
        "name": column.name,
    }


def format_columns_markdown(columns: list[Column], title: str = "Kanban Columns") -> str:
    """Format multiple columns as Markdown."""
    if not columns:
        return f"# {title}\n\nNo columns found."

    lines = [f"# {title}", "", f"Found {len(columns)} column(s):", ""]
    sorted_columns = sorted(columns, key=lambda c: c.sort_order or 0)
    for column in sorted_columns:
        lines.append(format_column_markdown(column))
    return "\n".join(lines)


def format_columns_json(columns: list[Column]) -> dict[str, Any]:
    """Format multiple columns as JSON."""
    return {
        "count": len(columns),
        "columns": [format_column_json(c) for c in columns],
    }


# =============================================================================
# Response Helpers
# =============================================================================


def format_response(
    data: Any,
    response_format: ResponseFormat,
    markdown_formatter: Callable[[Any], str],
    json_formatter: Callable[[Any], dict[str, Any]],
) -> str:
    """Format a response based on the requested format."""
    if response_format == ResponseFormat.MARKDOWN:
        result = markdown_formatter(data)
    else:
        result = json.dumps(json_formatter(data), indent=2, default=str)

    if len(result) > CHARACTER_LIMIT:
        if response_format == ResponseFormat.MARKDOWN:
            return (
                f"{result[:CHARACTER_LIMIT]}\n\n"
                f"---\n"
                f"*Response truncated. Use filters to narrow results.*"
            )
        else:
            return json.dumps({
                "truncated": True,
                "message": "Response truncated due to size. Use filters to narrow results.",
                "partial_data": result[:CHARACTER_LIMIT],
            })

    return result


def success_message(message: str) -> str:
    """Format a success message."""
    return f"**Success**: {message}"


def error_message(error: str, suggestion: str | None = None) -> str:
    """Format an error message with optional suggestion."""
    msg = f"**Error**: {error}"
    if suggestion:
        msg += f"\n\n*Suggestion*: {suggestion}"
    return msg


# =============================================================================
# Batch Operation Formatting
# =============================================================================


def format_batch_create_tasks_markdown(tasks: list[Task]) -> str:
    """Format batch task creation results as Markdown."""
    if not tasks:
        return "# Tasks Created\n\nNo tasks were created."

    lines = [f"# {len(tasks)} Task(s) Created", ""]
    for task in tasks:
        task_title = task.title or "(No title)"
        due_str = f" | Due: {format_date(task.due_date)}" if task.due_date else ""
        lines.append(f"- **{task_title}** (`{task.id}`){due_str}")
    return "\n".join(lines)


def format_batch_create_tasks_json(tasks: list[Task]) -> dict[str, Any]:
    """Format batch task creation results as JSON."""
    return {
        "success": True,
        "count": len(tasks),
        "tasks": [format_task_json(t) for t in tasks],
    }


def format_batch_update_tasks_markdown(results: dict[str, Any], update_count: int) -> str:
    """Format batch task update results as Markdown."""
    lines = [f"# {update_count} Task(s) Updated", ""]

    if results.get("id2error"):
        lines.append("## Errors")
        for task_id, error in results["id2error"].items():
            lines.append(f"- `{task_id}`: {error}")
        lines.append("")

    if results.get("id2etag"):
        lines.append("## Updated Tasks")
        for task_id in results["id2etag"]:
            lines.append(f"- `{task_id}` updated successfully")

    return "\n".join(lines)


def format_batch_update_tasks_json(results: dict[str, Any], update_count: int) -> dict[str, Any]:
    """Format batch task update results as JSON."""
    return {
        "success": not results.get("id2error"),
        "count": update_count,
        "updated_ids": list(results.get("id2etag", {}).keys()),
        "errors": results.get("id2error", {}),
    }


def format_batch_delete_tasks_markdown(count: int, task_ids: list[str]) -> str:
    """Format batch task deletion results as Markdown."""
    lines = [f"# {count} Task(s) Deleted", ""]
    lines.append("Tasks moved to trash:")
    for task_id in task_ids:
        lines.append(f"- `{task_id}`")
    return "\n".join(lines)


def format_batch_delete_tasks_json(count: int, task_ids: list[str]) -> dict[str, Any]:
    """Format batch task deletion results as JSON."""
    return {"success": True, "count": count, "deleted_ids": task_ids}


def format_batch_complete_tasks_markdown(count: int, task_ids: list[str]) -> str:
    """Format batch task completion results as Markdown."""
    lines = [f"# {count} Task(s) Completed", ""]
    for task_id in task_ids:
        lines.append(f"- `{task_id}` marked as completed")
    return "\n".join(lines)


def format_batch_complete_tasks_json(count: int, task_ids: list[str]) -> dict[str, Any]:
    """Format batch task completion results as JSON."""
    return {"success": True, "count": count, "completed_ids": task_ids}


def format_batch_move_tasks_markdown(moves: list[dict[str, str]]) -> str:
    """Format batch task move results as Markdown."""
    if not moves:
        return "# Tasks Moved\n\nNo tasks were moved."

    lines = [f"# {len(moves)} Task(s) Moved", ""]
    for move in moves:
        lines.append(
            f"- `{move['task_id']}`: `{move['from_project_id']}` -> `{move['to_project_id']}`"
        )
    return "\n".join(lines)


def format_batch_move_tasks_json(moves: list[dict[str, str]]) -> dict[str, Any]:
    """Format batch task move results as JSON."""
    return {"success": True, "count": len(moves), "moves": moves}


def format_batch_set_parents_markdown(results: list[dict[str, Any]]) -> str:
    """Format batch set parent results as Markdown."""
    if not results:
        return "# Subtasks Created\n\nNo parent assignments made."

    lines = [f"# {len(results)} Subtask Assignment(s)", ""]
    for result in results:
        lines.append(f"- `{result['task_id']}` -> parent `{result['parent_id']}`")
    return "\n".join(lines)


def format_batch_set_parents_json(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Format batch set parent results as JSON."""
    return {"success": True, "count": len(results), "assignments": results}


def format_batch_unparent_tasks_markdown(results: list[dict[str, Any]]) -> str:
    """Format batch unparent results as Markdown."""
    if not results:
        return "# Tasks Unparented\n\nNo tasks were unparented."

    lines = [f"# {len(results)} Task(s) Made Top-Level", ""]
    for result in results:
        lines.append(f"- `{result['task_id']}` removed from parent")
    return "\n".join(lines)


def format_batch_unparent_tasks_json(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Format batch unparent results as JSON."""
    return {"success": True, "count": len(results), "unparented": results}


def format_batch_pin_tasks_markdown(tasks: list[Task]) -> str:
    """Format batch pin/unpin results as Markdown."""
    if not tasks:
        return "# Task Pin Status\n\nNo pin operations performed."

    pinned = [t for t in tasks if t.is_pinned]
    unpinned = [t for t in tasks if not t.is_pinned]

    lines = [f"# {len(tasks)} Task Pin Operation(s)", ""]

    if pinned:
        lines.append(f"## Pinned ({len(pinned)})")
        for task in pinned:
            lines.append(f"- **{task.title or '(No title)'}** (`{task.id}`)")
        lines.append("")

    if unpinned:
        lines.append(f"## Unpinned ({len(unpinned)})")
        for task in unpinned:
            lines.append(f"- **{task.title or '(No title)'}** (`{task.id}`)")

    return "\n".join(lines)


def format_batch_pin_tasks_json(tasks: list[Task]) -> dict[str, Any]:
    """Format batch pin/unpin results as JSON."""
    return {
        "success": True,
        "count": len(tasks),
        "tasks": [{"id": t.id, "title": t.title, "is_pinned": t.is_pinned} for t in tasks],
    }
