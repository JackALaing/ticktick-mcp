#!/usr/bin/env python3
"""TickTick MCP Server - Consolidated Tool Architecture.

Phase 4: 43 tools consolidated to 6 tools using action-based routing.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

from ticktick_sdk.client import TickTickClient
from ticktick_sdk.tools.inputs import (
    ResponseFormat,
    TasksInput,
    ProjectsInput,
    FoldersInput,
    TagsInput,
    HabitsInput,
    ColumnsInput,
    UserInput,
    FocusInput,
)
from ticktick_sdk.models import Habit, HabitSection
from ticktick_sdk.tools.formatting import (
    format_task_markdown,
    format_task_json,
    format_tasks_markdown,
    format_tasks_json,
    format_project_markdown,
    format_project_json,
    format_projects_markdown,
    format_projects_json,
    format_tag_markdown,
    format_tag_json,
    format_tags_markdown,
    format_tags_json,
    format_folders_markdown,
    format_folders_json,
    format_column_markdown,
    format_column_json,
    format_columns_markdown,
    format_columns_json,
    format_user_markdown,
    format_user_status_markdown,
    format_statistics_markdown,
    success_message,
    error_message,
)
from ticktick_sdk.tools.help import get_help

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CHARACTER_LIMIT = 25000


def truncate_response(result: str, items_count: int, truncated_count: int | None = None) -> str:
    """Truncate response if it exceeds CHARACTER_LIMIT."""
    if len(result) <= CHARACTER_LIMIT:
        return result
    truncate_at = CHARACTER_LIMIT - 500
    truncate_point = result.rfind("\n\n", 0, truncate_at)
    if truncate_point == -1:
        truncate_point = result.rfind("\n", 0, truncate_at)
    if truncate_point == -1:
        truncate_point = truncate_at
    truncated = result[:truncate_point]
    message = f"\n\n---\n⚠️ **Response truncated** (exceeded {CHARACTER_LIMIT:,} characters)"
    return truncated + message


@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage TickTick client lifecycle."""
    logger.info("Initializing TickTick MCP Server...")
    try:
        client = TickTickClient.from_settings()
        await client.connect()
        logger.info("TickTick client connected")
        yield {"client": client}
    except Exception as e:
        logger.error("Failed to initialize client: %s", e)
        raise
    finally:
        if "client" in locals():
            await client.disconnect()
            logger.info("TickTick client disconnected")


mcp = FastMCP("ticktick_sdk", lifespan=lifespan)


def get_client(ctx: Context) -> TickTickClient:
    """Get client from context."""
    return ctx.request_context.lifespan_context["client"]


def handle_error(e: Exception, operation: str) -> str:
    """Handle exceptions with actionable messages."""
    logger.exception("Error in %s: %s", operation, e)
    error_type = type(e).__name__
    error_str = str(e)
    if "Authentication" in error_type:
        return error_message("Authentication failed", "Check TICKTICK_* environment variables.")
    elif "NotFound" in error_type:
        return error_message(f"Not found: {error_str}", "Verify the ID exists.")
    elif "Validation" in error_type:
        return error_message(f"Invalid input: {error_str}", "Check parameters.")
    else:
        return error_message(f"Error: {error_str}", f"Type: {error_type}")


# =============================================================================
# Habit Formatting Helpers
# =============================================================================


def format_habit_markdown(habit: Habit) -> str:
    """Format habit for markdown."""
    lines = [f"## {habit.name}", f"- **ID**: `{habit.id}`", f"- **Type**: {habit.habit_type}"]
    if habit.goal:
        lines.append(f"- **Goal**: {habit.goal} {habit.unit or ''}")
    lines.append(f"- **Streak**: {habit.current_streak} days")
    lines.append(f"- **Total**: {habit.total_checkins}")
    if habit.color:
        lines.append(f"- **Color**: {habit.color}")
    if habit.status:
        lines.append(f"- **Status**: {habit.status}")
    return "\n".join(lines)


def format_habit_json(habit: Habit) -> dict[str, Any]:
    """Format habit for JSON."""
    return {
        "id": habit.id,
        "name": habit.name,
        "habit_type": habit.habit_type,
        "goal": habit.goal,
        "step": habit.step,
        "unit": habit.unit,
        "color": habit.color,
        "current_streak": habit.current_streak,
        "total_checkins": habit.total_checkins,
        "status": habit.status,
    }


def format_habits_markdown(habits: list[Habit]) -> str:
    """Format multiple habits for markdown."""
    if not habits:
        return "No habits found."
    lines = [f"# {len(habits)} Habits", ""]
    for habit in habits:
        lines.append(format_habit_markdown(habit))
        lines.append("")
    return "\n".join(lines)


def format_habits_json(habits: list[Habit]) -> list[dict[str, Any]]:
    """Format multiple habits for JSON."""
    return [format_habit_json(h) for h in habits]


def format_section_markdown(section: HabitSection) -> str:
    """Format habit section for markdown."""
    return f"- **{section.name}**: `{section.id}`"


def format_sections_json(sections: list[HabitSection]) -> list[dict[str, Any]]:
    """Format habit sections for JSON."""
    return [{"id": s.id, "name": s.name} for s in sections]


# =============================================================================
# CONSOLIDATED TOOL: Tasks
# =============================================================================


@mcp.tool(name="ticktick_tasks")
async def ticktick_tasks(params: TasksInput, ctx: Context) -> str:
    """Task operations: create, get, list, update, complete, delete, move, pin, search, set_parents, unparent."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "create":
            task_specs = params.tasks or []
            created = await client.create_tasks(task_specs)
            if params.response_format == ResponseFormat.MARKDOWN:
                if len(created) == 1:
                    return f"# Task Created\n\n{format_task_markdown(created[0])}"
                return f"# {len(created)} Tasks Created\n\n{format_tasks_markdown(created, 'Created')}"
            return json.dumps({"success": True, "count": len(created), "tasks": [format_task_json(t) for t in created]}, indent=2)

        elif action == "get":
            task = await client.get_task(params.task_id, params.project_id)
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_task_markdown(task)
            return json.dumps(format_task_json(task), indent=2)

        elif action == "list":
            status = params.status or "active"
            limit = params.limit or 50
            days = params.days or 7

            if status == "active":
                tasks = await client.get_all_tasks()
                if params.project_id:
                    tasks = [t for t in tasks if t.project_id == params.project_id]
                if params.column_id:
                    tasks = [t for t in tasks if t.column_id == params.column_id]
                if params.tag:
                    tag_lower = params.tag.lower()
                    tasks = [t for t in tasks if any(tag.lower() == tag_lower for tag in t.tags)]
                if params.priority:
                    pmap = {"none": 0, "low": 1, "medium": 3, "high": 5}
                    tasks = [t for t in tasks if t.priority == pmap.get(params.priority, 0)]
                if params.due_today:
                    today = date.today()
                    tasks = [t for t in tasks if t.due_date and t.due_date.date() == today]
                if params.overdue:
                    today = date.today()
                    tasks = [t for t in tasks if t.due_date and t.due_date.date() < today and not t.is_completed]
            elif status == "completed":
                tasks = await client.get_completed_tasks(days=days, limit=limit)
            elif status == "abandoned":
                tasks = await client.get_abandoned_tasks(days=days, limit=limit)
            elif status == "deleted":
                tasks = await client.get_deleted_tasks(limit=limit)
            else:
                tasks = await client.get_all_tasks()

            total = len(tasks)
            tasks = tasks[:limit]
            if params.response_format == ResponseFormat.MARKDOWN:
                result = format_tasks_markdown(tasks, f"{status.capitalize()} Tasks")
            else:
                result = json.dumps(format_tasks_json(tasks), indent=2)
            return truncate_response(result, total, len(tasks))

        elif action == "update":
            update_specs = params.tasks or []
            await client.update_tasks(update_specs)
            count = len(update_specs)
            return success_message(f"{count} task(s) updated.")

        elif action == "complete":
            task_ids = [(t["task_id"], t["project_id"]) for t in (params.tasks or [])]
            await client.complete_tasks(task_ids)
            return success_message(f"{len(task_ids)} task(s) completed.")

        elif action == "delete":
            task_ids = [(t["task_id"], t["project_id"]) for t in (params.tasks or [])]
            await client.delete_tasks(task_ids)
            return success_message(f"{len(task_ids)} task(s) deleted.")

        elif action == "move":
            await client.move_tasks(params.moves or [])
            return success_message(f"{len(params.moves or [])} task(s) moved.")

        elif action == "pin":
            for t in (params.tasks or []):
                pin = t.get("pin", True)
                if pin:
                    await client.pin_task(t["task_id"], t["project_id"])
                else:
                    await client.unpin_task(t["task_id"], t["project_id"])
            return success_message(f"{len(params.tasks or [])} task(s) pin status updated.")

        elif action == "search":
            tasks = await client.search_tasks(params.query)
            # Apply limit client-side since search_tasks doesn't support it
            limit = params.limit or 20
            tasks = tasks[:limit]
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_tasks_markdown(tasks, f"Search: {params.query}")
            return json.dumps(format_tasks_json(tasks), indent=2)

        elif action == "set_parents":
            assignments = [{"task_id": t["task_id"], "project_id": t["project_id"], "parent_id": t["parent_id"]} for t in (params.tasks or [])]
            await client.set_task_parents(assignments)
            return success_message(f"{len(assignments)} task(s) made subtasks.")

        elif action == "unparent":
            specs = [{"task_id": t["task_id"], "project_id": t["project_id"]} for t in (params.tasks or [])]
            await client.unparent_tasks(specs)
            return success_message(f"{len(specs)} task(s) unparented.")

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"tasks.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: Projects
# =============================================================================


@mcp.tool(name="ticktick_projects")
async def ticktick_projects(params: ProjectsInput, ctx: Context) -> str:
    """Project operations: list, get, create, update, delete."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "list":
            projects = await client.get_all_projects()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_projects_markdown(projects)
            return json.dumps(format_projects_json(projects), indent=2)

        elif action == "get":
            project = await client.get_project(params.project_id)
            tasks = []
            if params.include_tasks:
                all_tasks = await client.get_all_tasks()
                tasks = [t for t in all_tasks if t.project_id == params.project_id]
            if params.response_format == ResponseFormat.MARKDOWN:
                result = format_project_markdown(project)
                if tasks:
                    result += f"\n\n{format_tasks_markdown(tasks, 'Tasks')}"
                return result
            data = format_project_json(project)
            if tasks:
                data["tasks"] = [format_task_json(t) for t in tasks]
            return json.dumps(data, indent=2)

        elif action == "create":
            project = await client.create_project(
                name=params.name,
                color=params.color,
                kind=params.kind or "TASK",
                view_mode=params.view_mode or "list",
                folder_id=params.folder_id,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Project Created\n\n{format_project_markdown(project)}"
            return json.dumps({"success": True, "project": format_project_json(project)}, indent=2)

        elif action == "update":
            folder = params.folder_id
            if folder == "NONE":
                folder = None
            project = await client.update_project(
                project_id=params.project_id,
                name=params.name,
                color=params.color,
                folder_id=folder,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Project Updated\n\n{format_project_markdown(project)}"
            return json.dumps({"success": True, "project": format_project_json(project)}, indent=2)

        elif action == "delete":
            await client.delete_project(params.project_id)
            return success_message(f"Project `{params.project_id}` deleted.")

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"projects.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: Folders
# =============================================================================


@mcp.tool(name="ticktick_folders")
async def ticktick_folders(params: FoldersInput, ctx: Context) -> str:
    """Folder operations: list, create, rename, delete."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "list":
            folders = await client.get_all_folders()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_folders_markdown(folders)
            return json.dumps(format_folders_json(folders), indent=2)

        elif action == "create":
            folder = await client.create_folder(params.name)
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Folder Created\n\n- **Name**: {folder.name}\n- **ID**: `{folder.id}`"
            return json.dumps({"success": True, "folder": {"id": folder.id, "name": folder.name}}, indent=2)

        elif action == "rename":
            folder = await client.rename_folder(params.folder_id, params.name)
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Folder Renamed\n\n- **Name**: {folder.name}\n- **ID**: `{folder.id}`"
            return json.dumps({"success": True, "folder": {"id": folder.id, "name": folder.name}}, indent=2)

        elif action == "delete":
            await client.delete_folder(params.folder_id)
            return success_message(f"Folder `{params.folder_id}` deleted.")

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"folders.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: Tags
# =============================================================================


@mcp.tool(name="ticktick_tags")
async def ticktick_tags(params: TagsInput, ctx: Context) -> str:
    """Tag operations: list, create, update, delete, merge."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "list":
            tags = await client.get_all_tags()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_tags_markdown(tags)
            return json.dumps(format_tags_json(tags), indent=2)

        elif action == "create":
            tag = await client.create_tag(
                name=params.name,
                color=params.color,
                parent=params.parent,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Tag Created\n\n{format_tag_markdown(tag)}"
            return json.dumps({"success": True, "tag": format_tag_json(tag)}, indent=2)

        elif action == "update":
            if params.label:
                await client.rename_tag(params.name, params.label)
                name = params.label
            else:
                name = params.name
            tag = await client.update_tag(
                name=name,
                color=params.color,
                parent=params.parent,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Tag Updated\n\n{format_tag_markdown(tag)}"
            return json.dumps({"success": True, "tag": format_tag_json(tag)}, indent=2)

        elif action == "delete":
            await client.delete_tag(params.name)
            return success_message(f"Tag `{params.name}` deleted.")

        elif action == "merge":
            await client.merge_tags(params.source, params.target)
            return success_message(f"Tag `{params.source}` merged into `{params.target}`.")

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"tags.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: Habits
# =============================================================================


@mcp.tool(name="ticktick_habits")
async def ticktick_habits(params: HabitsInput, ctx: Context) -> str:
    """Habit operations: list, get, sections, create, update, delete, checkin, checkins."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "list":
            habits = await client.get_all_habits()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_habits_markdown(habits)
            return json.dumps(format_habits_json(habits), indent=2)

        elif action == "get":
            habit = await client.get_habit(params.habit_id)
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_habit_markdown(habit)
            return json.dumps(format_habit_json(habit), indent=2)

        elif action == "sections":
            sections = await client.get_habit_sections()
            if params.response_format == ResponseFormat.MARKDOWN:
                lines = ["# Habit Sections", ""]
                for s in sections:
                    lines.append(format_section_markdown(s))
                return "\n".join(lines)
            return json.dumps(format_sections_json(sections), indent=2)

        elif action == "create":
            habit = await client.create_habit(
                name=params.name,
                habit_type=params.habit_type or "Boolean",
                goal=params.goal or 1.0,
                step=params.step or 1.0,
                unit=params.unit or "Count",
                color=params.color or "#97E38B",
                section_id=params.section_id,
                repeat_rule=params.repeat_rule or "RRULE:FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA",
                reminders=params.reminders,
                target_days=params.target_days or 0,
                encouragement=params.encouragement or "",
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Habit Created\n\n{format_habit_markdown(habit)}"
            return json.dumps({"success": True, "habit": format_habit_json(habit)}, indent=2)

        elif action == "update":
            if params.archived is not None:
                if params.archived:
                    habit = await client.archive_habit(params.habit_id)
                    action_str = "archived"
                else:
                    habit = await client.unarchive_habit(params.habit_id)
                    action_str = "unarchived"
                if not any([params.name, params.goal, params.step, params.unit, params.color,
                           params.section_id, params.repeat_rule, params.reminders,
                           params.target_days, params.encouragement]):
                    if params.response_format == ResponseFormat.MARKDOWN:
                        return f"# Habit {action_str.capitalize()}\n\n**{habit.name}** has been {action_str}."
                    return json.dumps({"success": True, "action": action_str, "habit": format_habit_json(habit)}, indent=2)

            habit = await client.update_habit(
                habit_id=params.habit_id,
                name=params.name,
                goal=params.goal,
                step=params.step,
                unit=params.unit,
                color=params.color,
                section_id=params.section_id,
                repeat_rule=params.repeat_rule,
                reminders=params.reminders,
                target_days=params.target_days,
                encouragement=params.encouragement,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Habit Updated\n\n{format_habit_markdown(habit)}"
            return json.dumps({"success": True, "habit": format_habit_json(habit)}, indent=2)

        elif action == "delete":
            await client.delete_habit(params.habit_id)
            return success_message(f"Habit `{params.habit_id}` deleted.")

        elif action == "checkin":
            checkin_data = params.checkins or []
            results = await client.checkin_habits(checkin_data)
            if params.response_format == ResponseFormat.MARKDOWN:
                lines = [f"# {len(results)} Check-in(s) Recorded", ""]
                for habit_id, habit in results.items():
                    lines.append(f"## {habit.name}")
                    lines.append(f"- **Total**: {habit.total_checkins}")
                    lines.append(f"- **Streak**: {habit.current_streak}")
                    lines.append("")
                return "\n".join(lines)
            return json.dumps({"success": True, "count": len(results), "habits": {hid: format_habit_json(h) for hid, h in results.items()}}, indent=2)

        elif action == "checkins":
            data = await client.get_habit_checkins(
                habit_ids=params.habit_ids,
                after_stamp=params.after_stamp or 0,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                lines = ["# Habit Check-in History", ""]
                for habit_id, checkins in data.items():
                    lines.append(f"## Habit `{habit_id}`")
                    if not checkins:
                        lines.append("No check-ins found.")
                    else:
                        for c in checkins:
                            lines.append(f"- {c.checkin_stamp}: {c.value}")
                    lines.append("")
                return "\n".join(lines)
            result = {}
            for habit_id, checkins in data.items():
                result[habit_id] = [{"checkin_stamp": c.checkin_stamp, "value": c.value, "goal": c.goal, "status": c.status} for c in checkins]
            return json.dumps(result, indent=2)

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"habits.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: Columns (Kanban)
# =============================================================================


@mcp.tool(name="ticktick_columns")
async def ticktick_columns(params: ColumnsInput, ctx: Context) -> str:
    """Kanban column operations: list, create, update, delete."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "list":
            columns = await client.get_columns(params.project_id)
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_columns_markdown(columns)
            return json.dumps(format_columns_json(columns), indent=2)

        elif action == "create":
            column = await client.create_column(
                project_id=params.project_id,
                name=params.name,
                sort_order=params.sort_order,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Column Created\n\n{format_column_markdown(column)}"
            return json.dumps({"success": True, "column": format_column_json(column)}, indent=2)

        elif action == "update":
            column = await client.update_column(
                column_id=params.column_id,
                project_id=params.project_id,
                name=params.name,
                sort_order=params.sort_order,
            )
            if params.response_format == ResponseFormat.MARKDOWN:
                return f"# Column Updated\n\n{format_column_markdown(column)}"
            return json.dumps({"success": True, "column": format_column_json(column)}, indent=2)

        elif action == "delete":
            await client.delete_column(params.column_id, params.project_id)
            return success_message(f"Column `{params.column_id}` deleted.")

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"columns.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: User
# =============================================================================


@mcp.tool(name="ticktick_user")
async def ticktick_user(params: UserInput, ctx: Context) -> str:
    """User operations: profile, status, statistics, preferences."""
    try:
        client = get_client(ctx)
        action = params.action

        if action == "profile":
            user = await client.get_profile()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_user_markdown(user)
            return json.dumps({"id": user.id, "username": user.username, "name": user.name, "email": user.email, "timezone": user.time_zone}, indent=2)

        elif action == "status":
            status = await client.get_status()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_user_status_markdown(status)
            return json.dumps({"inbox_id": status.inbox_id, "pro": status.is_pro, "subscription": status.subscription_type}, indent=2)

        elif action == "statistics":
            stats = await client.get_statistics()
            if params.response_format == ResponseFormat.MARKDOWN:
                return format_statistics_markdown(stats)
            return json.dumps(stats.__dict__ if hasattr(stats, "__dict__") else str(stats), indent=2)

        elif action == "preferences":
            prefs = await client.get_preferences()
            return json.dumps(prefs, indent=2)

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"user.{params.action}")


# =============================================================================
# CONSOLIDATED TOOL: Focus
# =============================================================================


@mcp.tool(name="ticktick_focus")
async def ticktick_focus(params: FocusInput, ctx: Context) -> str:
    """Focus/pomodoro operations: heatmap, by_tag."""
    try:
        client = get_client(ctx)
        action = params.action
        days = params.days or 30

        if params.start_date and params.end_date:
            start = datetime.fromisoformat(params.start_date)
            end = datetime.fromisoformat(params.end_date)
        else:
            end = datetime.now()
            start = end - timedelta(days=days)

        if action == "heatmap":
            data = await client.get_focus_heatmap(start_date=start, end_date=end)
            if params.response_format == ResponseFormat.MARKDOWN:
                lines = ["# Focus Heatmap", f"Period: {start.date()} to {end.date()}", ""]
                if hasattr(data, "items"):
                    for date_str, minutes in data.items():
                        lines.append(f"- {date_str}: {minutes} min")
                return "\n".join(lines) if lines else "No focus data found."
            return json.dumps(data, indent=2, default=str)

        elif action == "by_tag":
            data = await client.get_focus_by_tag(start_date=start, end_date=end)
            if params.response_format == ResponseFormat.MARKDOWN:
                lines = ["# Focus by Tag", f"Period: {start.date()} to {end.date()}", ""]
                if hasattr(data, "items"):
                    for tag, minutes in data.items():
                        lines.append(f"- {tag}: {minutes} min")
                return "\n".join(lines) if lines else "No focus data found."
            return json.dumps(data, indent=2, default=str)

        return error_message(f"Unknown action: {action}", "")

    except Exception as e:
        return handle_error(e, f"focus.{params.action}")


# =============================================================================
# Help Tool
# =============================================================================


@mcp.tool(name="ticktick_help")
async def ticktick_help(tool: str | None = None) -> str:
    """Get documentation for TickTick tools."""
    return get_help(tool)


# =============================================================================
# Server Entry Point
# =============================================================================

# For testing
async def _test_schema():
    """Test that schema generates correctly."""
    tools = mcp._tool_manager._tools
    print(f"Registered {len(tools)} tools")
    for name in sorted(tools.keys()):
        print(f"  - {name}")


def main():
    """Main entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
