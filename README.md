# ticktick-mcp: AI-Optimized TickTick MCP Server

A token-optimized [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) server for [TickTick](https://ticktick.com), designed for AI assistants like Claude.

**Fork of [ticktick-sdk](https://github.com/dev-mirzabicer/ticktick-sdk)** - Consolidated from 43 tools to 6 action-based tools, achieving **94% reduction in token usage**.

## Why This Fork?

The original ticktick-sdk exposed 43 individual MCP tools. While comprehensive, this creates significant overhead for AI agents:

| Metric | Original | This Fork | Improvement |
|--------|----------|-----------|-------------|
| **Tool Count** | 43 tools | 6 tools | 86% fewer |
| **Token Usage** | ~25,000 tokens | ~1,500 tokens | **94% reduction** |
| **Context Efficiency** | Low | High | Faster responses |

### What Changed

**Consolidated Architecture**: 43 individual endpoints → 6 action-based tools with smart routing:

| Original Tools | Consolidated Tool |
|----------------|-------------------|
| `ticktick_create_tasks`, `ticktick_get_task`, `ticktick_list_tasks`, `ticktick_update_tasks`, `ticktick_complete_tasks`, `ticktick_delete_tasks`, `ticktick_move_tasks`, `ticktick_set_task_parents`, `ticktick_unparent_tasks`, `ticktick_search_tasks`, `ticktick_pin_tasks` | `ticktick_tasks` |
| `ticktick_list_projects`, `ticktick_get_project`, `ticktick_create_project`, `ticktick_update_project`, `ticktick_delete_project` | `ticktick_projects` |
| `ticktick_list_folders`, `ticktick_create_folder`, `ticktick_rename_folder`, `ticktick_delete_folder` | `ticktick_folders` |
| `ticktick_list_tags`, `ticktick_create_tag`, `ticktick_update_tag`, `ticktick_delete_tag`, `ticktick_merge_tags` | `ticktick_tags` |
| `ticktick_list_columns`, `ticktick_create_column`, `ticktick_update_column`, `ticktick_delete_column` | `ticktick_columns` |
| — | `ticktick_help` |

**Removed Tools** (rarely used, unstable, or read-only):

| Removed | Reason |
|---------|--------|
| `ticktick_habits`, `ticktick_habit`, `ticktick_habit_sections`, `ticktick_create_habit`, `ticktick_update_habit`, `ticktick_delete_habit`, `ticktick_checkin_habits`, `ticktick_habit_checkins` | Undocumented V2 API with unreliable sync behavior |
| `ticktick_get_profile`, `ticktick_get_status`, `ticktick_get_statistics`, `ticktick_get_preferences` | Read-only informational, rarely needed by AI |
| `ticktick_focus_heatmap`, `ticktick_focus_by_tag` | Read-only analytics, rarely needed by AI |

---

## Available Tools

| Tool | Actions | Description |
|------|---------|-------------|
| `ticktick_tasks` | create, get, list, update, complete, delete, move, pin, search, set_parents, unparent | Full task lifecycle management |
| `ticktick_projects` | list, get, create, update, delete | Project/list management |
| `ticktick_folders` | list, create, rename, delete | Folder organization |
| `ticktick_tags` | list, create, update, delete, merge | Tag management with hierarchy |
| `ticktick_columns` | list, create, update, delete | Kanban column management |
| `ticktick_help` | — | Get documentation for any tool |

All mutation operations support **batch processing** (1-100 items per call).

---

## Installation

### Claude.ai (Cloud MCP)

This server is deployed on Railway with SSE transport for Claude.ai integration:

**URL**: `https://ticktick-mcp-production.up.railway.app/sse`

Add to Claude.ai's MCP settings with your TickTick credentials.

### Claude Code (Local)

```bash
pip install ticktick-sdk
```

```bash
claude mcp add ticktick \
  -e TICKTICK_CLIENT_ID=your_client_id \
  -e TICKTICK_CLIENT_SECRET=your_client_secret \
  -e TICKTICK_ACCESS_TOKEN=your_access_token \
  -e TICKTICK_USERNAME=your_email \
  -e TICKTICK_PASSWORD=your_password \
  -- ticktick-sdk
```

### Getting Credentials

1. **Register App**: Go to [TickTick Developer Portal](https://developer.ticktick.com/manage), create an app with redirect URI `http://127.0.0.1:8080/callback`

2. **Get OAuth2 Token**:
```bash
TICKTICK_CLIENT_ID=your_id TICKTICK_CLIENT_SECRET=your_secret ticktick-sdk auth
```

3. Copy the access token to your configuration

---

## Usage Examples

### Tasks

```json
// Create a task
{"action": "create", "tasks": [{"title": "Buy groceries", "priority": "high"}]}

// List active tasks
{"action": "list", "status": "active"}

// Complete tasks
{"action": "complete", "tasks": [{"task_id": "abc123", "project_id": "proj1"}]}

// Search
{"action": "search", "query": "meeting"}
```

### Projects

```json
// Create kanban board
{"action": "create", "name": "Sprint Board", "view_mode": "kanban"}

// Get project with tasks
{"action": "get", "project_id": "abc123", "include_tasks": true}
```

### Tags

```json
// Create with color
{"action": "create", "name": "urgent", "color": "#FF0000"}

// Merge tags
{"action": "merge", "source": "old-tag", "target": "new-tag"}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `TICKTICK_CLIENT_ID` | Yes | OAuth2 client ID |
| `TICKTICK_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `TICKTICK_ACCESS_TOKEN` | Yes | OAuth2 access token |
| `TICKTICK_USERNAME` | Yes | TickTick email |
| `TICKTICK_PASSWORD` | Yes | TickTick password |
| `TICKTICK_HOST` | No | `ticktick.com` (default) or `dida365.com` |

---

## Architecture

This fork maintains the original's dual-API architecture:

- **V1 API (OAuth2)**: Official, documented - project with tasks, basic operations
- **V2 API (Session)**: Unofficial, reverse-engineered - tags, folders, subtasks, advanced features

The unified client automatically routes operations to the appropriate API.

---

## Acknowledgments

- [Original ticktick-sdk](https://github.com/dev-mirzabicer/ticktick-sdk) by dev-mirzabicer
- [TickTick](https://ticktick.com) for the task management platform
- [Model Context Protocol](https://modelcontextprotocol.io/) for the AI integration standard
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework

---

## License

MIT License - see [LICENSE](LICENSE) for details.
