# Persistent agent-runner service: imports the agent engine in-process and
# exposes it over HTTP/SSE (see Agent GUI Integration.pdf recommendations).
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY agent ./agent
RUN pip install --no-cache-dir .

COPY service/requirements.txt ./service/requirements.txt
RUN pip install --no-cache-dir -r service/requirements.txt
COPY service ./service

ENV AGENT_DATA_ROOT=/data
ENV PYTHONPATH=/app

VOLUME ["/data"]

EXPOSE 8100

CMD ["python", "-m", "service.api"]
