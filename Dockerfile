FROM python:3.8

ARG PIP_PACKAGES=requirements.txt
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID scheduler
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID scheduler

USER scheduler
ENV PATH=/home/scheduler/.local/bin:${PATH}

WORKDIR /app/scheduler

COPY ["requirements.txt", "${PIP_PACKAGES}", "logging.json", "./"]
RUN pip install -r ${PIP_PACKAGES}

COPY scheduler/ /app/scheduler/

CMD ["python", "-m", "scheduler"]
