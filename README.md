# ⚡ State Panel

A lightweight, decoupled status monitor and dashboard for VPS and Cloud services with dual interfaces: a **Rich terminal CLI** and a **static Web UI** deployable to Cloudflare Pages.

---

## ✨ Features

- **Dual Interface**: Rich CLI with formatted tables and latency metrics, plus a dark minimalist Web UI (Vue 3 + Tailwind CSS).
- **Decoupled & Resilient**: The public status page is 100% static (hosted on Cloudflare Pages), remaining accessible even if monitored hosts go down.
- **Privacy-First**: Internal endpoint URLs stay private on the monitor instance and are never leaked to public status JSON exports.
- **Pub/Sub Alerts**: Real-time outage notifications via `ntfy` (iOS, Android, Webhooks).
- **Flexible Storage**: Local SQLite or Turso Cloud (libSQL).

---

## 🚀 Quickstart

### 1. Install Dependencies

```bash
# Python dependencies
uv sync

# Web UI dependencies
cd web && bun install && cd ..
```

### 2. Configure Services

Edit `services.yaml` to define your target endpoints:

```yaml
settings:
  title: "System Status"
  description: "Live operational status of VPS and Cloud infrastructure"
  history_days: 30
  output_dir: "web/public/data"

ntfy:
  enabled: false
  topic: "my-alerts-topic"

services:
  - id: "outline"
    name: "Outline"
    category: "VPS Core"
    type: "http"
    target: "${OUTLINE_URL:-https://outline.example.com}"
    expected_status: 200
```

---

## 💻 CLI Usage

| Command | Description |
| :--- | :--- |
| `uv run state-panel check` | Run instant health checks |
| `uv run state-panel history --days 30` | View historical uptime summary |
| `uv run state-panel serve --port 8000` | Start local server with live API and UI |
| `uv run state-panel daemon` | Run continuous monitoring loop |
| `uv run state-panel export` | Run checks and export `status.json` |
| `uv run state-panel deploy` | Build and deploy to Cloudflare Pages |

---

## 🌐 Web & Deployment

### Local Development

```bash
# Terminal 1: Backend API
uv run state-panel serve --port 8000

# Terminal 2: Web UI with hot-reload
cd web && bun dev
```

### Deploy to Cloudflare Pages

```bash
# Automated (checks, builds, and deploys)
uv run state-panel deploy --project-name <project-name>

# Or manual deploy
uv run state-panel export
cd web && bun run build && cd ..
bunx wrangler pages deploy web/dist --project-name=<project-name>
```

---

## 🛠️ Code Quality

```bash
# Linting & Formatting
uv run ruff check .
uv run ruff format --check .

# Type Checking
uv run ty check

# Pre-commit & Commits
uv run pre-commit run --all-files
uv run cz commit
```
