# Standalone container for the agent execution engine.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY agent ./agent

RUN pip install --no-cache-dir .

ENV AGENT_DATA_ROOT=/data

VOLUME ["/data"]

ENTRYPOINT ["agentv5"]
