# Standalone chat application container: exposes the in-process runner over HTTP/SSE.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY agent ./agent
RUN pip install --no-cache-dir .

COPY service/requirements.txt ./service/requirements.txt
RUN pip install --no-cache-dir -r service/requirements.txt

COPY service ./service
COPY chat ./chat

ENV AGENT_DATA_ROOT=/data
ENV PYTHONPATH=/app

VOLUME ["/data"]

EXPOSE 8100

CMD ["python", "-m", "chat.api"]
