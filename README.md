# agent_v5_1
Generic Agentic Loop

## Architecture

The project is split into three independent parts:

- **agent/** - the execution engine (CLI-only). Packaged/containerized on its own (`agent/Dockerfile`).
- **client/** - an independent tool (CLI + web dashboard) for browsing/manipulating the shared data: sessions, memory, workspace files. Packaged/containerized on its own (`client/Dockerfile`). Has no dependency on the `agent` package.
- **data/** - the shared bind mount (`session/`, `memory/`, `resources/`, `agent_workspace/`). Both `agent` and `client` only agree on this directory's layout; they don't share Python code.

```
AGENT  <-->  data/ (bind mount)  <-->  CLIENT
```

Locally (no containers) both default to `<repo>/data`. In Docker, both containers mount `./data` on the host to `/data`, controlled by the `AGENT_DATA_ROOT` env var.

## How to run

### With Docker
```
docker compose build
docker compose run --rm agent --username alice --workspace agent_workspace --interactive false --test false --initial_prompt "..."
docker compose up client   # dashboard at http://localhost:8000/?username=alice
```

### Locally (no containers)
First, you need to prepare python environment. Agent settings are defined in **pyproject.toml** (`agentv5` package, `agent/` folder only). The client has its own dependencies in `client/requirements.txt`.

```
pip install -e .
pip install -r client/requirements.txt
agentv5 --username alice --workspace agent_workspace --interactive false --test false --initial_prompt "..."
python -m client.cli sessions-list --username alice
python -m client.api   # dashboard at http://localhost:8000/?username=alice
```

## Agent Source Code
Agent Source code is in **agent** folder.

## Client Source Code
Client source code is in **client** folder.

