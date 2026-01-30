#!/usr/bin/env python3
"""
TickTick CLI - Token-efficient task management.

Usage:
    ticktick tasks list [--project ID] [--tag NAME] [--priority low|medium|high] [--today] [--overdue]
    ticktick tasks get ID
    ticktick tasks add "Title" [--project ID] [--due DATE] [--priority low|medium|high] [--tags a,b]
    ticktick tasks done ID
    ticktick tasks rm ID
    ticktick projects list
    ticktick auth status|clear
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

AUTH_CACHE_DIR = Path.home() / ".ticktick"
AUTH_CACHE_FILE = AUTH_CACHE_DIR / "auth_cache.json"
SESSION_TTL = 86400


def parse_natural_date(date_str: str, timezone: str = "America/New_York") -> str:
    """
    Parse natural language dates into YYYY-MM-DD format.

    Supports:
        - today, tomorrow, yesterday
        - in N days/weeks (e.g., "in 3 days", "in 2 weeks")
        - next monday/tuesday/etc.
        - YYYY-MM-DD (passthrough)

    Args:
        date_str: The date string to parse
        timezone: IANA timezone name (default: America/New_York)

    Returns:
        Date string in YYYY-MM-DD format
    """
    from datetime import datetime, timedelta
    import re
    import os

    date_str = date_str.strip().lower()

    # Get current time in user's timezone
    tz = os.environ.get("TZ", timezone)
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tz))
    except (ImportError, KeyError):
        # Fallback to UTC if zoneinfo unavailable or invalid tz
        now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str[:10]

    # Simple keywords
    if date_str == "today":
        return today.strftime("%Y-%m-%d")
    if date_str == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if date_str == "yesterday":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # "in N days/weeks"
    match = re.match(r'^in\s+(\d+)\s+(day|days|week|weeks)$', date_str)
    if match:
        n = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("week"):
            n *= 7
        return (today + timedelta(days=n)).strftime("%Y-%m-%d")

    # "next monday", "next tuesday", etc.
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    match = re.match(r'^next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', date_str)
    if match:
        target_weekday = weekdays[match.group(1)]
        current_weekday = today.weekday()
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:  # Target day is today or earlier, go to next week
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # If nothing matched, return as-is (let the API handle/reject it)
    return date_str


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def get_credentials() -> dict[str, str | None]:
    return {
        "client_id": os.environ.get("TICKTICK_CLIENT_ID"),
        "client_secret": os.environ.get("TICKTICK_CLIENT_SECRET"),
        "access_token": os.environ.get("TICKTICK_ACCESS_TOKEN"),
        "username": os.environ.get("TICKTICK_USERNAME"),
        "password": os.environ.get("TICKTICK_PASSWORD"),
    }


def load_auth_cache() -> dict[str, Any] | None:
    if not AUTH_CACHE_FILE.exists():
        return None
    try:
        with open(AUTH_CACHE_FILE) as f:
            cache = json.load(f)
        if time.time() - cache.get("cached_at", 0) > SESSION_TTL:
            return None
        return cache
    except Exception:
        return None


def save_auth_cache(cache_data: dict[str, Any]) -> None:
    AUTH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_data["cached_at"] = time.time()
    with open(AUTH_CACHE_FILE, "w") as f:
        json.dump(cache_data, f)
    AUTH_CACHE_FILE.chmod(0o600)


def clear_auth_cache() -> None:
    if AUTH_CACHE_FILE.exists():
        AUTH_CACHE_FILE.unlink()


async def get_api():
    from ticktick_sdk.api.v2 import TickTickV2Client
    from ticktick_sdk.api.v2.auth import SessionToken

    creds = get_credentials()
    cache = load_auth_cache()
    v2_session = None

    if cache and "v2_session" in cache:
        try:
            v2_session = SessionToken.from_dict(cache["v2_session"])
        except Exception:
            v2_session = None

    v2_client = TickTickV2Client()

    if v2_session:
        v2_client.set_session(v2_session)
        inbox_id = v2_session.inbox_id
    else:
        if not creds.get("username") or not creds.get("password"):
            raise ValueError("No cached session. Set TICKTICK_USERNAME and TICKTICK_PASSWORD.")
        session = await v2_client.authenticate(creds["username"], creds["password"])
        inbox_id = session.inbox_id
        save_auth_cache({"v2_session": session.to_dict()})

    return CachedAPI(v2_client, inbox_id)


class CachedAPI:
    def __init__(self, v2_client, inbox_id):
        self._v2 = v2_client
        self._inbox_id = inbox_id

    async def close(self):
        if self._v2:
            await self._v2.close()

    @property
    def inbox_id(self):
        return self._inbox_id

    async def list_projects(self):
        from ticktick_sdk.models import Project
        data = await self._v2.sync()
        return [Project.from_v2(p) for p in data.get("projectProfiles", [])]

    async def get_project(self, project_id: str):
        from ticktick_sdk.models import Project
        projects = await self.list_projects()
        for p in projects:
            if p.id == project_id:
                return p
        raise ValueError(f"Project {project_id} not found")

    async def create_project(self, name: str, **kwargs):
        response = await self._v2.create_project(name=name, **kwargs)
        project_id = next(iter(response.get("id2etag", {}).keys()), None)
        if project_id:
            return await self.get_project(project_id)
        raise ValueError("Failed to create project")

    async def update_project(self, project_id: str, name: str = None, **kwargs):
        existing = await self.get_project(project_id)
        project_name = name if name is not None else existing.name
        await self._v2.update_project(project_id=project_id, name=project_name, **kwargs)
        return await self.get_project(project_id)

    async def delete_project(self, project_id: str):
        await self.get_project(project_id)
        await self._v2.delete_project(project_id)

    async def list_tasks(
        self,
        project_id: str = None,
        column_id: str = None,
        tag: str = None,
        priority: int = None,
        due_today: bool = None,
        overdue: bool = None,
        from_date: str = None,
        to_date: str = None,
        days: int = None,
        limit: int = None,
    ):
        from datetime import datetime, timedelta
        from ticktick_sdk.models import Task
        from ticktick_sdk.constants import TaskStatus

        sync_data = await self._v2.sync()
        tasks = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Calculate date range if days is specified
        if days and not from_date:
            from_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")

        for t in sync_data.get("syncTaskBean", {}).get("update", []):
            task = Task.from_v2(t)

            # Only active tasks by default
            if task.status != TaskStatus.ACTIVE:
                continue

            if project_id and task.project_id != project_id:
                continue

            if column_id and getattr(task, 'column_id', None) != column_id:
                continue

            if tag and tag not in (task.tags or []):
                continue

            if priority is not None and task.priority != priority:
                continue

            if due_today:
                if not task.due_date:
                    continue
                task_due = task.due_date.replace(hour=0, minute=0, second=0, microsecond=0) if hasattr(task.due_date, 'replace') else None
                if not task_due or task_due.date() != today.date():
                    continue

            if overdue:
                if not task.due_date:
                    continue
                now = datetime.now(task.due_date.tzinfo) if task.due_date.tzinfo else datetime.now()
                if task.due_date >= now:
                    continue

            # Date range filtering (typically for created/modified date)
            if from_date:
                task_date = task.created_time or task.modified_time
                if task_date:
                    task_date_str = str(task_date)[:10]
                    if task_date_str < from_date:
                        continue

            if to_date:
                task_date = task.created_time or task.modified_time
                if task_date:
                    task_date_str = str(task_date)[:10]
                    if task_date_str > to_date:
                        continue

            tasks.append(task)

        if limit:
            tasks = tasks[:limit]

        return tasks

    async def get_task(self, task_id: str):
        from ticktick_sdk.models import Task
        data = await self._v2.get_task(task_id)
        return Task.from_v2(data)

    async def create_task(self, title: str, project_id: str = None, **kwargs):
        results = await self.create_tasks([title], project_id=project_id, **kwargs)
        return results[0] if results else None

    async def create_tasks(self, titles: list[str], project_id: str = None, **kwargs):
        pid = project_id or self._inbox_id
        results = []
        for title in titles:
            response = await self._v2.create_task(title=title, project_id=pid, **kwargs)
            task_id = next(iter(response.get("id2etag", {}).keys()), None)
            if task_id:
                results.append(await self.get_task(task_id))
        return results

    async def update_task(self, task_id: str, **kwargs):
        task = await self.get_task(task_id)
        update_data = {"id": task_id, "projectId": task.project_id, **kwargs}
        await self._v2.batch_tasks(update=[update_data])
        return await self.get_task(task_id)

    async def complete_task(self, task_id: str):
        await self.complete_tasks([task_id])

    async def complete_tasks(self, task_ids: list[str]):
        from datetime import datetime
        from ticktick_sdk.constants import TaskStatus
        from ticktick_sdk.models import Task
        updates = []
        for task_id in task_ids:
            task = await self.get_task(task_id)
            updates.append({
                "id": task_id,
                "projectId": task.project_id,
                "status": TaskStatus.COMPLETED,
                "completedTime": Task.format_datetime(datetime.now(), "v2"),
            })
        await self._v2.batch_tasks(update=updates)

    async def abandon_task(self, task_id: str):
        await self.abandon_tasks([task_id])

    async def abandon_tasks(self, task_ids: list[str]):
        from datetime import datetime
        from ticktick_sdk.constants import TaskStatus
        from ticktick_sdk.models import Task
        updates = []
        for task_id in task_ids:
            task = await self.get_task(task_id)
            updates.append({
                "id": task_id,
                "projectId": task.project_id,
                "status": TaskStatus.ABANDONED,
                "completedTime": Task.format_datetime(datetime.now(), "v2"),
            })
        await self._v2.batch_tasks(update=updates)

    async def delete_task(self, task_id: str):
        await self.delete_tasks([task_id])

    async def delete_tasks(self, task_ids: list[str]):
        for task_id in task_ids:
            task = await self.get_task(task_id)
            await self._v2.delete_task(task.project_id, task_id)

    async def move_task(self, task_id: str, to_project_id: str):
        await self.move_tasks([task_id], to_project_id)

    async def move_tasks(self, task_ids: list[str], to_project_id: str):
        for task_id in task_ids:
            task = await self.get_task(task_id)
            await self._v2.move_task(task_id, task.project_id, to_project_id)

    async def pin_task(self, task_id: str, pin: bool = True):
        result = await self.pin_tasks([task_id], pin)
        return result[0] if result else None

    async def pin_tasks(self, task_ids: list[str], pin: bool = True):
        from datetime import datetime, timezone
        results = []
        for task_id in task_ids:
            task = await self.get_task(task_id)
            if pin:
                now = datetime.now(timezone.utc)
                pinned_time = now.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
                await self._v2.update_task(task_id=task_id, project_id=task.project_id, pinned_time=pinned_time)
            else:
                await self._v2.update_task(task_id=task_id, project_id=task.project_id, pinned_time="")
            results.append(await self.get_task(task_id))
        return results

    async def search_tasks(self, query: str):
        tasks = await self.list_tasks()
        q = query.lower()
        return [t for t in tasks if q in (t.title or "").lower() or q in (t.content or "").lower()]

    async def set_task_parent(self, task_id: str, parent_id: str):
        await self.set_task_parents([(task_id, parent_id)])

    async def set_task_parents(self, task_parent_pairs: list[tuple[str, str]]):
        for task_id, parent_id in task_parent_pairs:
            task = await self.get_task(task_id)
            await self._v2.set_task_parent(task_id, task.project_id, parent_id)

    async def unset_task_parent(self, task_id: str):
        await self.unset_task_parents([task_id])

    async def unset_task_parents(self, task_ids: list[str]):
        for task_id in task_ids:
            task = await self.get_task(task_id)
            parent_id = task.parent_id
            if not parent_id:
                raise ValueError(f"Task {task_id} has no parent")
            await self._v2.unset_task_parent(task_id, task.project_id, parent_id)

    async def list_tags(self):
        from ticktick_sdk.models import Tag
        data = await self._v2.sync()
        return [Tag.from_v2(t) for t in data.get("tags", [])]

    async def create_tag(self, name: str, color: str = None, parent: str = None):
        await self._v2.create_tag(name=name, color=color, parent=parent)
        tags = await self.list_tags()
        for t in tags:
            if t.name == name:
                return t
        from ticktick_sdk.models import Tag
        return Tag(name=name)

    async def delete_tag(self, name: str):
        await self._v2.delete_tag(name)

    async def update_tag(self, name: str, new_name: str = None, color: str = None, parent: str = None):
        kwargs = {}
        if new_name:
            kwargs["label"] = new_name
        if color:
            kwargs["color"] = color
        if parent is not None:  # Allow empty string to remove parent
            kwargs["parent"] = parent
        await self._v2.update_tag(name=name, **kwargs)
        tags = await self.list_tags()
        target_name = new_name or name
        for t in tags:
            if t.name == target_name:
                return t
        from ticktick_sdk.models import Tag
        return Tag(name=target_name)

    async def merge_tags(self, source: str, target: str):
        await self._v2.merge_tags(source, target)

    async def list_folders(self):
        from ticktick_sdk.models import ProjectGroup
        data = await self._v2.sync()
        return [ProjectGroup.from_v2(f) for f in data.get("projectGroups", [])]

    async def create_folder(self, name: str):
        from ticktick_sdk.models import ProjectGroup
        response = await self._v2.create_folder(name=name)
        folder_id = next(iter(response.get("id2etag", {}).keys()), None)
        if folder_id:
            folders = await self.list_folders()
            for f in folders:
                if f.id == folder_id:
                    return f
        return ProjectGroup(id=folder_id or "", name=name)

    async def delete_folder(self, folder_id: str):
        await self._v2.delete_folder(folder_id)

    async def rename_folder(self, folder_id: str, name: str):
        await self._v2.rename_folder(folder_id, name)
        folders = await self.list_folders()
        for f in folders:
            if f.id == folder_id:
                return f
        from ticktick_sdk.models import ProjectGroup
        return ProjectGroup(id=folder_id, name=name)

    async def list_columns(self, project_id: str):
        from ticktick_sdk.models import Column
        data = await self._v2.get_columns(project_id)
        return [Column.from_v2(c) for c in data]

    async def create_column(self, project_id: str, name: str, sort_order: int = None):
        from ticktick_sdk.models import Column
        kwargs = {"project_id": project_id, "name": name}
        if sort_order is not None:
            kwargs["sort_order"] = sort_order
        response = await self._v2.create_column(**kwargs)
        column_id = next(iter(response.get("id2etag", {}).keys()), None)
        if column_id:
            columns = await self.list_columns(project_id)
            for c in columns:
                if c.id == column_id:
                    return c
        return Column(id=column_id or "", name=name, project_id=project_id, sort_order=sort_order or 0)

    async def update_column(self, column_id: str, project_id: str, name: str = None, sort_order: int = None):
        kwargs = {"column_id": column_id, "project_id": project_id}
        if name:
            kwargs["name"] = name
        if sort_order is not None:
            kwargs["sort_order"] = sort_order
        await self._v2.update_column(**kwargs)
        columns = await self.list_columns(project_id)
        for c in columns:
            if c.id == column_id:
                return c
        from ticktick_sdk.models import Column
        return Column(id=column_id, name=name or "", project_id=project_id, sort_order=sort_order or 0)

    async def delete_column(self, column_id: str, project_id: str):
        await self._v2.delete_column(column_id, project_id)


# Output formatters - minimal fields only
def fmt_task_list(task) -> dict:
    d = task.model_dump()
    r = {"id": d["id"], "title": d["title"]}
    if d.get("project_id"):
        r["project_id"] = d["project_id"]
    if d.get("priority"):
        r["priority"] = d["priority"]
    if d.get("due_date"):
        r["due"] = str(d["due_date"])[:10]
    if d.get("tags"):
        r["tags"] = d["tags"]
    return r


def fmt_task_detail(task) -> dict:
    d = task.model_dump()
    r = {"id": d["id"], "title": d["title"], "project_id": d["project_id"]}
    if d.get("priority"):
        r["priority"] = d["priority"]
    if d.get("content"):
        r["content"] = d["content"]
    if d.get("due_date"):
        r["due"] = str(d["due_date"])
    if d.get("start_date"):
        r["start"] = str(d["start_date"])
    if d.get("tags"):
        r["tags"] = d["tags"]
    return r


def fmt_project(project) -> dict:
    d = project.model_dump()
    r = {"id": d["id"], "name": d["name"]}
    if d.get("view_mode"):
        r["view"] = d["view_mode"]
    return r


def fmt_tag(tag) -> dict:
    d = tag.model_dump()
    r = {"name": d["name"]}
    if d.get("color"):
        r["color"] = d["color"]
    if d.get("parent"):
        r["parent"] = d["parent"]
    return r


def fmt_folder(folder) -> dict:
    d = folder.model_dump()
    return {"id": d["id"], "name": d["name"]}


def fmt_column(col) -> dict:
    d = col.model_dump()
    r = {"id": d["id"], "name": d["name"]}
    if d.get("sort_order") is not None:
        r["sort"] = d["sort_order"]
    return r


def output(data):
    print(json.dumps(data, default=str))


def error(msg: str):
    print(json.dumps({"error": msg}))
    sys.exit(1)


# Command handlers
async def cmd_tasks_list(args):
    api = await get_api()
    try:
        priority_map = {"low": 1, "medium": 3, "high": 5}
        priority = priority_map.get(args.priority) if args.priority else None
        tasks = await api.list_tasks(
            project_id=args.project,
            column_id=args.column,
            tag=args.tag,
            priority=priority,
            due_today=args.today,
            overdue=args.overdue,
            from_date=args.from_date,
            to_date=args.to_date,
            days=args.days,
            limit=args.limit,
        )
        output([fmt_task_list(t) for t in tasks])
    finally:
        await api.close()


async def cmd_tasks_get(args):
    api = await get_api()
    try:
        task = await api.get_task(args.id)
        output(fmt_task_detail(task))
    finally:
        await api.close()


async def cmd_tasks_add(args):
    api = await get_api()
    try:
        priority_map = {"low": 1, "medium": 3, "high": 5}
        priority = priority_map.get(args.priority) if args.priority else None
        tags = args.tags.split(",") if args.tags else None
        due = parse_natural_date(args.due) if args.due else None
        tasks = await api.create_tasks(
            titles=args.titles,
            project_id=args.project,
            content=args.content,
            priority=priority,
            due_date=due,
            tags=tags,
        )
        if len(tasks) == 1:
            output(fmt_task_detail(tasks[0]))
        else:
            output([fmt_task_list(t) for t in tasks])
    finally:
        await api.close()


async def cmd_tasks_edit(args):
    api = await get_api()
    try:
        priority_map = {"low": 1, "medium": 3, "high": 5}
        kwargs = {}
        if args.title:
            kwargs["title"] = args.title
        if args.content:
            kwargs["content"] = args.content
        if args.priority:
            kwargs["priority"] = priority_map.get(args.priority)
        if args.due:
            kwargs["dueDate"] = parse_natural_date(args.due)
        if args.tags:
            kwargs["tags"] = args.tags.split(",")
        task = await api.update_task(args.id, **kwargs)
        output(fmt_task_detail(task))
    finally:
        await api.close()


async def cmd_tasks_done(args):
    api = await get_api()
    try:
        await api.complete_tasks(args.ids)
        output({"ok": True, "ids": args.ids})
    finally:
        await api.close()


async def cmd_tasks_abandon(args):
    api = await get_api()
    try:
        await api.abandon_tasks(args.ids)
        output({"ok": True, "ids": args.ids})
    finally:
        await api.close()


async def cmd_tasks_rm(args):
    api = await get_api()
    try:
        await api.delete_tasks(args.ids)
        output({"ok": True, "ids": args.ids})
    finally:
        await api.close()


async def cmd_tasks_move(args):
    api = await get_api()
    try:
        await api.move_tasks(args.ids, args.to)
        output({"ok": True, "ids": args.ids, "to": args.to})
    finally:
        await api.close()


async def cmd_tasks_pin(args):
    api = await get_api()
    try:
        tasks = await api.pin_tasks(args.ids, not args.unpin)
        output({"ok": True, "ids": args.ids, "pinned": not args.unpin})
    finally:
        await api.close()


async def cmd_tasks_search(args):
    api = await get_api()
    try:
        tasks = await api.search_tasks(args.query)
        output([fmt_task_list(t) for t in tasks])
    finally:
        await api.close()


async def cmd_tasks_parent(args):
    api = await get_api()
    try:
        await api.set_task_parents([(tid, args.parent) for tid in args.ids])
        output({"ok": True, "ids": args.ids, "parent": args.parent})
    finally:
        await api.close()


async def cmd_tasks_unparent(args):
    api = await get_api()
    try:
        await api.unset_task_parents(args.ids)
        output({"ok": True, "ids": args.ids})
    finally:
        await api.close()


async def cmd_projects_list(args):
    api = await get_api()
    try:
        projects = await api.list_projects()
        output([fmt_project(p) for p in projects])
    finally:
        await api.close()


async def cmd_projects_get(args):
    api = await get_api()
    try:
        project = await api.get_project(args.id)
        output(fmt_project(project))
    finally:
        await api.close()


async def cmd_projects_add(args):
    api = await get_api()
    try:
        project = await api.create_project(name=args.name, view_mode=args.view)
        output(fmt_project(project))
    finally:
        await api.close()


async def cmd_projects_rm(args):
    api = await get_api()
    try:
        await api.delete_project(args.id)
        output({"ok": True, "id": args.id})
    finally:
        await api.close()


async def cmd_projects_edit(args):
    api = await get_api()
    try:
        kwargs = {}
        if args.name:
            kwargs["name"] = args.name
        if args.view:
            kwargs["view_mode"] = args.view
        project = await api.update_project(args.id, **kwargs)
        output(fmt_project(project))
    finally:
        await api.close()


async def cmd_tags_list(args):
    api = await get_api()
    try:
        tags = await api.list_tags()
        output([fmt_tag(t) for t in tags])
    finally:
        await api.close()


async def cmd_tags_add(args):
    api = await get_api()
    try:
        tag = await api.create_tag(args.name, args.color, args.parent)
        output(fmt_tag(tag))
    finally:
        await api.close()


async def cmd_tags_rm(args):
    api = await get_api()
    try:
        await api.delete_tag(args.name)
        output({"ok": True, "name": args.name})
    finally:
        await api.close()


async def cmd_tags_edit(args):
    api = await get_api()
    try:
        tag = await api.update_tag(args.name, new_name=args.rename, color=args.color, parent=args.parent)
        output(fmt_tag(tag))
    finally:
        await api.close()


async def cmd_tags_merge(args):
    api = await get_api()
    try:
        await api.merge_tags(args.source, args.target)
        output({"ok": True, "source": args.source, "target": args.target})
    finally:
        await api.close()


async def cmd_folders_list(args):
    api = await get_api()
    try:
        folders = await api.list_folders()
        output([fmt_folder(f) for f in folders])
    finally:
        await api.close()


async def cmd_folders_add(args):
    api = await get_api()
    try:
        folder = await api.create_folder(args.name)
        output(fmt_folder(folder))
    finally:
        await api.close()


async def cmd_folders_rm(args):
    api = await get_api()
    try:
        await api.delete_folder(args.id)
        output({"ok": True, "id": args.id})
    finally:
        await api.close()


async def cmd_folders_rename(args):
    api = await get_api()
    try:
        folder = await api.rename_folder(args.id, args.name)
        output(fmt_folder(folder))
    finally:
        await api.close()


async def cmd_columns_list(args):
    api = await get_api()
    try:
        columns = await api.list_columns(args.project)
        output([fmt_column(c) for c in columns])
    finally:
        await api.close()


async def cmd_columns_add(args):
    api = await get_api()
    try:
        column = await api.create_column(args.project, args.name, args.sort)
        output(fmt_column(column))
    finally:
        await api.close()


async def cmd_columns_edit(args):
    api = await get_api()
    try:
        column = await api.update_column(args.id, args.project, name=args.name, sort_order=args.sort)
        output(fmt_column(column))
    finally:
        await api.close()


async def cmd_columns_rm(args):
    api = await get_api()
    try:
        await api.delete_column(args.id, args.project)
        output({"ok": True, "id": args.id})
    finally:
        await api.close()


def cmd_auth_status(args):
    cache = load_auth_cache()
    if cache:
        age = int(time.time() - cache.get("cached_at", 0))
        output({"ok": True, "age_seconds": age})
    else:
        output({"ok": False})


def cmd_auth_clear(args):
    clear_auth_cache()
    output({"ok": True})


def cmd_auth_login(args):
    """Run OAuth2 flow in manual/headless mode."""
    from ticktick_sdk.auth_cli import main as auth_main
    # Always use manual mode for headless/AI-friendly operation
    exit_code = auth_main(manual=True)
    sys.exit(exit_code)


def build_parser():
    parser = argparse.ArgumentParser(prog="ticktick", description="TickTick CLI")
    subs = parser.add_subparsers(dest="command", required=True)

    # tasks
    tasks = subs.add_parser("tasks", help="Task operations")
    tasks_subs = tasks.add_subparsers(dest="action", required=True)

    # tasks list
    tl = tasks_subs.add_parser("list", help="List tasks")
    tl.add_argument("--project", "-p", help="Filter by project ID")
    tl.add_argument("--column", help="Filter by column ID (kanban)")
    tl.add_argument("--tag", "-t", help="Filter by tag")
    tl.add_argument("--priority", choices=["low", "medium", "high"], help="Filter by priority")
    tl.add_argument("--today", action="store_true", help="Due today only")
    tl.add_argument("--overdue", action="store_true", help="Overdue only")
    tl.add_argument("--from-date", help="From date (YYYY-MM-DD)")
    tl.add_argument("--to-date", help="To date (YYYY-MM-DD)")
    tl.add_argument("--days", type=int, help="Lookback days")
    tl.add_argument("--limit", "-n", type=int, help="Max results")
    tl.set_defaults(func=cmd_tasks_list)

    # tasks get
    tg = tasks_subs.add_parser("get", help="Get task details")
    tg.add_argument("id", help="Task ID")
    tg.set_defaults(func=cmd_tasks_get)

    # tasks add
    ta = tasks_subs.add_parser("add", help="Create task(s)")
    ta.add_argument("titles", nargs="+", help="Task title(s)")
    ta.add_argument("--project", "-p", help="Project ID")
    ta.add_argument("--content", "-c", help="Description (for single task)")
    ta.add_argument("--due", "-d", help="Due date (YYYY-MM-DD, today, tomorrow, 'in N days', 'next monday')")
    ta.add_argument("--priority", choices=["low", "medium", "high"])
    ta.add_argument("--tags", help="Comma-separated tags")
    ta.set_defaults(func=cmd_tasks_add)

    # tasks edit
    te = tasks_subs.add_parser("edit", help="Update task")
    te.add_argument("id", help="Task ID")
    te.add_argument("--title", help="New title")
    te.add_argument("--content", "-c", help="New description")
    te.add_argument("--due", "-d", help="New due date (YYYY-MM-DD, today, tomorrow, 'in N days', 'next monday')")
    te.add_argument("--priority", choices=["low", "medium", "high"])
    te.add_argument("--tags", help="New tags (comma-separated)")
    te.set_defaults(func=cmd_tasks_edit)

    # tasks done
    td = tasks_subs.add_parser("done", help="Complete task(s)")
    td.add_argument("ids", nargs="+", help="Task ID(s)")
    td.set_defaults(func=cmd_tasks_done)

    # tasks abandon
    tab = tasks_subs.add_parser("abandon", help="Abandon task(s) (mark as won't do)")
    tab.add_argument("ids", nargs="+", help="Task ID(s)")
    tab.set_defaults(func=cmd_tasks_abandon)

    # tasks rm
    tr = tasks_subs.add_parser("rm", help="Delete task(s)")
    tr.add_argument("ids", nargs="+", help="Task ID(s)")
    tr.set_defaults(func=cmd_tasks_rm)

    # tasks move
    tm = tasks_subs.add_parser("move", help="Move task(s) to project")
    tm.add_argument("ids", nargs="+", help="Task ID(s)")
    tm.add_argument("--to", required=True, help="Target project ID")
    tm.set_defaults(func=cmd_tasks_move)

    # tasks pin
    tp = tasks_subs.add_parser("pin", help="Pin/unpin task(s)")
    tp.add_argument("ids", nargs="+", help="Task ID(s)")
    tp.add_argument("--unpin", action="store_true", help="Unpin instead of pin")
    tp.set_defaults(func=cmd_tasks_pin)

    # tasks search
    ts = tasks_subs.add_parser("search", help="Search tasks")
    ts.add_argument("query", help="Search query")
    ts.set_defaults(func=cmd_tasks_search)

    # tasks parent
    tpa = tasks_subs.add_parser("parent", help="Set task(s) parent")
    tpa.add_argument("ids", nargs="+", help="Task ID(s)")
    tpa.add_argument("--parent", required=True, help="Parent task ID")
    tpa.set_defaults(func=cmd_tasks_parent)

    # tasks unparent
    tup = tasks_subs.add_parser("unparent", help="Remove task(s) parent")
    tup.add_argument("ids", nargs="+", help="Task ID(s)")
    tup.set_defaults(func=cmd_tasks_unparent)

    # projects
    projects = subs.add_parser("projects", help="Project operations")
    proj_subs = projects.add_subparsers(dest="action", required=True)

    pl = proj_subs.add_parser("list", help="List projects")
    pl.set_defaults(func=cmd_projects_list)

    pg = proj_subs.add_parser("get", help="Get project")
    pg.add_argument("id", help="Project ID")
    pg.set_defaults(func=cmd_projects_get)

    pa = proj_subs.add_parser("add", help="Create project")
    pa.add_argument("name", help="Project name")
    pa.add_argument("--view", choices=["list", "kanban", "timeline"], default="list")
    pa.set_defaults(func=cmd_projects_add)

    pr = proj_subs.add_parser("rm", help="Delete project")
    pr.add_argument("id", help="Project ID")
    pr.set_defaults(func=cmd_projects_rm)

    pe = proj_subs.add_parser("edit", help="Update project")
    pe.add_argument("id", help="Project ID")
    pe.add_argument("--name", help="New name")
    pe.add_argument("--view", choices=["list", "kanban", "timeline"], help="View mode")
    pe.set_defaults(func=cmd_projects_edit)

    # tags
    tags = subs.add_parser("tags", help="Tag operations")
    tags_subs = tags.add_subparsers(dest="action", required=True)

    tgl = tags_subs.add_parser("list", help="List tags")
    tgl.set_defaults(func=cmd_tags_list)

    tga = tags_subs.add_parser("add", help="Create tag")
    tga.add_argument("name", help="Tag name")
    tga.add_argument("--color", help="Tag color (hex)")
    tga.add_argument("--parent", help="Parent tag name")
    tga.set_defaults(func=cmd_tags_add)

    tgr = tags_subs.add_parser("rm", help="Delete tag")
    tgr.add_argument("name", help="Tag name")
    tgr.set_defaults(func=cmd_tags_rm)

    tge = tags_subs.add_parser("edit", help="Update tag")
    tge.add_argument("name", help="Tag name")
    tge.add_argument("--rename", help="New name")
    tge.add_argument("--color", help="New color (hex)")
    tge.add_argument("--parent", help="New parent tag (empty to remove)")
    tge.set_defaults(func=cmd_tags_edit)

    tgm = tags_subs.add_parser("merge", help="Merge tags")
    tgm.add_argument("source", help="Source tag to merge from")
    tgm.add_argument("target", help="Target tag to merge into")
    tgm.set_defaults(func=cmd_tags_merge)

    # folders
    folders = subs.add_parser("folders", help="Folder operations")
    fold_subs = folders.add_subparsers(dest="action", required=True)

    fl = fold_subs.add_parser("list", help="List folders")
    fl.set_defaults(func=cmd_folders_list)

    fa = fold_subs.add_parser("add", help="Create folder")
    fa.add_argument("name", help="Folder name")
    fa.set_defaults(func=cmd_folders_add)

    fr = fold_subs.add_parser("rm", help="Delete folder")
    fr.add_argument("id", help="Folder ID")
    fr.set_defaults(func=cmd_folders_rm)

    fre = fold_subs.add_parser("rename", help="Rename folder")
    fre.add_argument("id", help="Folder ID")
    fre.add_argument("name", help="New name")
    fre.set_defaults(func=cmd_folders_rename)

    # columns
    columns = subs.add_parser("columns", help="Kanban column operations")
    col_subs = columns.add_subparsers(dest="action", required=True)

    cl = col_subs.add_parser("list", help="List columns")
    cl.add_argument("--project", "-p", required=True, help="Project ID")
    cl.set_defaults(func=cmd_columns_list)

    ca = col_subs.add_parser("add", help="Create column")
    ca.add_argument("name", help="Column name")
    ca.add_argument("--project", "-p", required=True, help="Project ID")
    ca.add_argument("--sort", type=int, help="Sort order")
    ca.set_defaults(func=cmd_columns_add)

    ce = col_subs.add_parser("edit", help="Update column")
    ce.add_argument("id", help="Column ID")
    ce.add_argument("--project", "-p", required=True, help="Project ID")
    ce.add_argument("--name", help="New name")
    ce.add_argument("--sort", type=int, help="New sort order")
    ce.set_defaults(func=cmd_columns_edit)

    cr = col_subs.add_parser("rm", help="Delete column")
    cr.add_argument("id", help="Column ID")
    cr.add_argument("--project", "-p", required=True, help="Project ID")
    cr.set_defaults(func=cmd_columns_rm)

    # auth
    auth = subs.add_parser("auth", help="Authentication")
    auth_subs = auth.add_subparsers(dest="action", required=True)

    auth_subs.add_parser("status", help="Check auth status").set_defaults(func=cmd_auth_status)
    auth_subs.add_parser("clear", help="Clear cached auth").set_defaults(func=cmd_auth_clear)
    auth_subs.add_parser("login", help="Run OAuth2 login (headless/manual mode)").set_defaults(func=cmd_auth_login)

    return parser


def main() -> int:
    load_dotenv_if_available()
    parser = build_parser()

    try:
        args = parser.parse_args()
    except SystemExit:
        return 1

    try:
        if asyncio.iscoroutinefunction(args.func):
            asyncio.run(args.func(args))
        else:
            args.func(args)
        return 0
    except Exception as e:
        error(str(e))
        return 1


def cli_main() -> None:
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
