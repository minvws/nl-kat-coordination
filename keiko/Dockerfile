FROM python:3.8

EXPOSE 8000

ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID keiko
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID keiko

WORKDIR /app/keiko
ENV PATH=/home/keiko/.local/bin:${PATH}

# LateX dependencies
RUN apt update -y \
    && apt install -y --no-install-recommends \
    texlive-latex-base texlive-latex-extra texlive-latex-recommended texlive-lang-european texlive-fonts-recommended chktex

# Build with "docker build --build-arg ENVIRONMENT=dev" to install dev
# dependencies
ARG ENVIRONMENT

COPY requirements.txt requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$ENVIRONMENT" = "dev" ]; then pip install -r requirements-dev.txt; fi

COPY . .

ENV KEIKO_REPORTS_FOLDER=/reports
RUN mkdir -p "$KEIKO_REPORTS_FOLDER" && chown -f -R keiko:keiko "$KEIKO_REPORTS_FOLDER"
VOLUME /reports

USER keiko

CMD ["uvicorn", "keiko.app:api", "--host", "0.0.0.0", "--port", "8000"]
