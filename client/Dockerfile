# Independent client container. It only needs the Python standard library
# and the shared bind mount to inspect/manipulate agent data.
FROM python:3.12-slim

WORKDIR /app

COPY client ./client

ENV CLIENT_SHARED_ROOT=/shared
VOLUME ["/shared"]

ENTRYPOINT ["python", "-m", "client.cli"]
CMD ["sessions"]
