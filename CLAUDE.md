# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**myassistant** is a Python 3.14 application that runs as a scheduled task (currently daily at 11:00 AM UTC) via cron. The project is containerized with Docker. It includes credential and token files indicating integration with external APIs/services.

### Key Files
- `main.py` — Entry point for the application
- `pyproject.toml` — Project metadata and dependencies
- `crontab` — Scheduling configuration (runs `/app/main.py` daily at 11:00 AM)
- `Dockerfile` — Container image definition
- `.python-version` — Python 3.14 specified for pyenv

## Development Setup

### Prerequisites
- Python 3.14+
- Virtual environment already initialized at `.venv/`

### Initial Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (currently none, but future-proofing)
pip install -e .
```

## Common Commands

### Run the application
```bash
python main.py
```

### Add dependencies
Update `pyproject.toml` in the `dependencies` array, then:
```bash
pip install -e .
```

### Check project info
```bash
python -m pip show myassistant
```

## Architecture Notes

The project is in early stages. The main application logic lives in `main.py`. As it grows:
- Keep the entry point minimal; move complex logic into modules
- Credential files (`credentials.json`, `token.json`) should be loaded at runtime, not committed
- Cron scheduling is managed via the `crontab` file; if adding new scheduled tasks, update both the file and the Dockerfile

## Important Context

- **Credentials**: The project uses `credentials.json` and `token.json` for API authentication. These should never be committed to git (already in `.gitignore` is recommended).
- **Containerization**: The Dockerfile likely sets up the runtime environment. When modifying dependencies or the entry point, ensure the Docker image will still work correctly.
- **Scheduled Execution**: This is a cron-based application, not a persistent daemon. Design functions to be idempotent and handle interruptions gracefully.
