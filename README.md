# agent_v5_1
Generic Agentic Loop

## Architecture

The project is split into three independent entities that only talk to each
other through a shared filesystem (bind mount):

```
AGENT  <-->  BIND MOUNT (resources/, agent_workspace/, session/, memory/)  <-->  CLIENT
```

- **agent/** – the agent program. It is self-contained and only depends on
  `pyproject.toml` + `agent/`. It never assumes `resources/`, `session/`,
  `memory/` or `agent_workspace/` live next to it on disk; those are read
  through a configurable shared root (`AGENT_SHARED_ROOT`, defaults to the
  repo root for local/dev use, `/shared` inside Docker).
- **client/** – a separate, independent program (no dependency on the
  `agent` package) that reads/writes the same shared data root to inspect
  sessions and manipulate files (`resources`, `agent_workspace`, etc.).
- **resources/, agent_workspace/, session/, memory/** – external data. In
  Docker these are bind-mounted into both the agent and client containers at
  `/shared/<name>`.

## How to run

### Docker (recommended)

```bash
cp .env.example .env   # set OPENAI_API_KEY
docker compose up --build agent      # starts the browser dashboard on :8000
docker compose run client sessions   # inspect shared data from the client
docker compose run client ls agent_workspace
```

### Local (no Docker)

First, you need to prepare python environment. Project settings are defined in **pyproject.toml**. You can see in pyproject.toml that only **agent** folder is part of the program, **resources** and **agent_workspace** are basically external resources.

Without `AGENT_SHARED_ROOT` set, the agent falls back to the repository root, so the existing local layout (`./resources`, `./agent_workspace`, `./session`, `./memory`) keeps working unchanged. The client behaves the same way via `CLIENT_SHARED_ROOT`.

```bash
python -m client.cli sessions
python -m client.cli ls agent_workspace
```

## Agent Source Code
Agent Source code is in **agent** folder.

## Client Source Code
Client source code is in **client** folder.

