# Agent container image. The agent program is fully self-contained here;
# it only depends on the "agent" package and pyproject.toml from the repo.
# All external data (resources/, session/, memory/, agent_workspace/) is
# provided at runtime through a bind mount at AGENT_SHARED_ROOT (/shared).
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY agent ./agent

RUN pip install --no-cache-dir .

ENV AGENT_SHARED_ROOT=/shared
VOLUME ["/shared"]

EXPOSE 8000

# Default: run the browser dashboard (long-running service).
# Override the command to run one-shot CLI tasks instead, e.g.:
#   docker compose run agent agentv5 --initial_prompt "..." --workspace agent_workspace --interactive false --test false
CMD ["agentv5-web"]
