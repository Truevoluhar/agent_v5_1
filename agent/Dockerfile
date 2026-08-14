# Standalone container for the agent execution engine.
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY agent ./agent

RUN pip install --no-cache-dir .

ENV AGENT_DATA_ROOT=/data

VOLUME ["/data"]

ENTRYPOINT ["agentv5"]
