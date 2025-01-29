FROM python:3.10-slim

WORKDIR /usr/src/app

# Add a non-root user
RUN adduser --disabled-password --gecos '' nonroot

RUN pip install --no-cache-dir httpx

COPY . .

# Switch to the non-root user
USER nonroot

ENTRYPOINT ["python"]
