# Standalone container for the client - manipulates the shared bind mount only.
FROM python:3.11-slim

WORKDIR /app

COPY client/requirements.txt ./client/requirements.txt
RUN pip install --no-cache-dir -r client/requirements.txt

COPY client ./client

ENV AGENT_DATA_ROOT=/data
ENV PYTHONPATH=/app

VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "-m", "client.api"]
