FROM python:3.8

EXPOSE 8000

ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /app/octopoes

#ENTRYPOINT ["/app/octopoes/entrypoint.sh"]

RUN groupadd --gid $USER_GID octopoes
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID octopoes

ENV PATH=/home/octopoes/.local/bin:${PATH}

# Build with "docker build --build-arg ENVIRONMENT=dev" to install dev
# dependencies
ARG ENVIRONMENT

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN ["chmod", "+x", "/app/octopoes/entrypoint.sh"]

USER octopoes

CMD ["python", "-m", "octopoes"]
