"""TickTick MCP Help Documentation."""

TOOL_DOCS = {
    "ticktick_tasks": """
## ticktick_tasks

Task operations: create, get, list, update, complete, delete, move, pin, search, set_parents, unparent.

### Parameters
- **action** (str, required): One of the actions below
- **response_format** (str): 'markdown' (default) or 'json'

### Actions

#### create
Create tasks in batch.
- **tasks** (list): Task specs with title (required), project_id, content, kind, priority, start_date, due_date, tags, reminders, recurrence, parent_id

```json
{"action": "create", "tasks": [{"title": "Buy groceries"}]}
{"action": "create", "tasks": [{"title": "Daily standup", "start_date": "2026-01-20", "recurrence": "RRULE:FREQ=DAILY"}]}
```
**Note:** Recurrence requires start_date!

#### get
Get task by ID.
- **task_id** (str, required): 24-char hex ID
- **project_id** (str): For V1 API fallback

```json
{"action": "get", "task_id": "abc123def456..."}
```

#### list
List tasks with filtering.
- **status** (str): 'active' (default), 'completed', 'abandoned', 'deleted'
- **project_id**, **column_id**, **tag**, **priority**: Filters
- **due_today**, **overdue** (bool): Date filters
- **from_date**, **to_date** (str): YYYY-MM-DD for completed/abandoned
- **days** (int): Lookback days (default 7)
- **limit** (int): Max results (default 50)

```json
{"action": "list", "status": "active", "project_id": "abc123"}
{"action": "list", "status": "completed", "days": 14}
```

#### update
Update task properties.
- **tasks** (list): Updates with task_id, project_id (required), plus fields to change

```json
{"action": "update", "tasks": [{"task_id": "abc", "project_id": "proj1", "priority": "high"}]}
```

#### complete
Mark tasks complete.
- **tasks** (list): [{task_id, project_id}, ...]

```json
{"action": "complete", "tasks": [{"task_id": "abc", "project_id": "proj1"}]}
```

#### delete
Delete tasks (move to trash).
- **tasks** (list): [{task_id, project_id}, ...]

#### move
Move tasks between projects.
- **moves** (list): [{task_id, from_project_id, to_project_id}, ...]

```json
{"action": "move", "moves": [{"task_id": "abc", "from_project_id": "p1", "to_project_id": "p2"}]}
```

#### pin
Pin/unpin tasks.
- **tasks** (list): [{task_id, project_id, pin: true/false}, ...]

#### search
Search tasks.
- **query** (str, required): Search text
- **limit** (int): Max results

```json
{"action": "search", "query": "meeting"}
```

#### set_parents
Make tasks into subtasks.
- **tasks** (list): [{task_id, project_id, parent_id}, ...]

#### unparent
Remove tasks from parents.
- **tasks** (list): [{task_id, project_id}, ...]
""",

    "ticktick_projects": """
## ticktick_projects

Project operations: list, get, create, update, delete.

### Parameters
- **action** (str, required): One of the actions below
- **response_format** (str): 'markdown' (default) or 'json'

### Actions

#### list
List all projects.

```json
{"action": "list"}
```

#### get
Get project details.
- **project_id** (str, required)
- **include_tasks** (bool): Include all tasks

```json
{"action": "get", "project_id": "abc123", "include_tasks": true}
```

#### create
Create a project.
- **name** (str, required)
- **kind** (str): 'TASK' (default) or 'NOTE'
- **view_mode** (str): 'list' (default), 'kanban', 'timeline'
- **color** (str): Hex color
- **folder_id** (str): Parent folder

```json
{"action": "create", "name": "Sprint Board", "view_mode": "kanban"}
```

#### update
Update project properties.
- **project_id** (str, required)
- **name**, **color**, **folder_id** (use 'NONE' to remove from folder)

```json
{"action": "update", "project_id": "abc123", "color": "#FF5733"}
```

#### delete
Delete project and all tasks.
- **project_id** (str, required)

**Warning:** This permanently deletes all tasks!
""",

    "ticktick_folders": """
## ticktick_folders

Folder operations: list, create, rename, delete.

### Parameters
- **action** (str, required): One of the actions below
- **response_format** (str): 'markdown' (default) or 'json'

### Actions

#### list
List all folders.

```json
{"action": "list"}
```

#### create
Create a folder.
- **name** (str, required)

```json
{"action": "create", "name": "Work Projects"}
```

#### rename
Rename a folder.
- **folder_id** (str, required)
- **name** (str, required)

```json
{"action": "rename", "folder_id": "abc123", "name": "New Name"}
```

#### delete
Delete a folder (projects become ungrouped).
- **folder_id** (str, required)

```json
{"action": "delete", "folder_id": "abc123"}
```
""",

    "ticktick_tags": """
## ticktick_tags

Tag operations: list, create, update, delete, merge.

### Parameters
- **action** (str, required): One of the actions below
- **response_format** (str): 'markdown' (default) or 'json'

### Actions

#### list
List all tags.

```json
{"action": "list"}
```

#### create
Create a tag.
- **name** (str, required)
- **color** (str): Hex color
- **parent** (str): Parent tag name for nesting

```json
{"action": "create", "name": "urgent", "color": "#FF0000"}
```

#### update
Update tag properties.
- **name** (str, required): Current tag name
- **color** (str): New color
- **parent** (str): New parent ('' to remove)
- **label** (str): New name (rename)

```json
{"action": "update", "name": "old-tag", "label": "new-tag"}
```

#### delete
Delete a tag.
- **name** (str, required)

```json
{"action": "delete", "name": "unused-tag"}
```

#### merge
Merge source tag into target.
- **source** (str, required): Tag to delete
- **target** (str, required): Tag to keep

```json
{"action": "merge", "source": "work", "target": "professional"}
```
""",

    "ticktick_columns": """
## ticktick_columns

Kanban column operations: list, create, update, delete.

### Parameters
- **action** (str, required): One of the actions below
- **response_format** (str): 'markdown' (default) or 'json'

### Actions

#### list
List columns for a project.
- **project_id** (str, required)

```json
{"action": "list", "project_id": "abc123"}
```

#### create
Create a column.
- **project_id** (str, required)
- **name** (str, required)
- **sort_order** (int): Display order

```json
{"action": "create", "project_id": "abc123", "name": "In Progress"}
```

#### update
Update a column.
- **column_id** (str, required)
- **project_id** (str, required)
- **name** (str): New name
- **sort_order** (int): New order

```json
{"action": "update", "column_id": "col123", "project_id": "proj1", "name": "Done"}
```

#### delete
Delete a column (tasks become unassigned).
- **column_id** (str, required)
- **project_id** (str, required)

```json
{"action": "delete", "column_id": "col123", "project_id": "proj1"}
```
""",

    "ticktick_help": """
## ticktick_help

Get documentation for TickTick tools.

### Parameters
- **tool** (str): Tool name (or omit for overview)

### Examples
```json
{"tool": "tasks"}
{"tool": "habits"}
```
""",
}

TOOL_CATEGORIES = {
    "Core Tools": [
        "ticktick_tasks",
        "ticktick_projects",
        "ticktick_folders",
        "ticktick_tags",
        "ticktick_columns",
        "ticktick_help",
    ],
}


def get_help(tool_name: str | None = None) -> str:
    """Get help documentation for TickTick tools."""
    if tool_name is None:
        lines = ["# TickTick MCP Tools (Consolidated)", ""]
        lines.append("Use `ticktick_help` with `tool` parameter for detailed docs.")
        lines.append("")
        lines.append("## Available Tools")
        lines.append("")
        lines.append("| Tool | Actions |")
        lines.append("|------|---------|")
        lines.append("| `ticktick_tasks` | create, get, list, update, complete, delete, move, pin, search, set_parents, unparent |")
        lines.append("| `ticktick_projects` | list, get, create, update, delete |")
        lines.append("| `ticktick_folders` | list, create, rename, delete |")
        lines.append("| `ticktick_tags` | list, create, update, delete, merge |")
        lines.append("| `ticktick_columns` | list, create, update, delete |")
        lines.append("| `ticktick_help` | Get documentation |")
        return "\n".join(lines)

    name = tool_name.lower().strip()
    if not name.startswith("ticktick_"):
        name = f"ticktick_{name}"

    if name in TOOL_DOCS:
        return TOOL_DOCS[name]

    matches = [t for t in TOOL_DOCS if name in t or t in name]
    if matches:
        return f"Tool '{tool_name}' not found. Did you mean: {', '.join(matches)}?"

    return f"Tool '{tool_name}' not found. Use ticktick_help() to see available tools."
