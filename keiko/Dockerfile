ARG PYTHON_VERSION=3.11
FROM python:$PYTHON_VERSION-bookworm AS dev

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
        chktex \
        fonts-recommended \
        latexmk \
        texlive-fonts-recommended \
        texlive-lang-european \
        texlive-latex-base \
        texlive-latex-extra \
        texlive-latex-recommended \
        texlive-xetex \
    && rm -rf /var/lib/apt/lists/*

ENV KEIKO_REPORTS_FOLDER=/reports
RUN mkdir -p "$KEIKO_REPORTS_FOLDER" && chown -f -R keiko:keiko "$KEIKO_REPORTS_FOLDER"
VOLUME /reports

# Build with "docker build --build-arg ENVIRONMENT=dev" to install dev
# dependencies
ARG ENVIRONMENT

COPY requirements.txt requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$ENVIRONMENT" = "dev" ]; then pip install -r requirements-dev.txt; fi

USER keiko

FROM dev

COPY . .

CMD ["uvicorn", "keiko.app:api", "--host", "0.0.0.0", "--port", "8000"]
