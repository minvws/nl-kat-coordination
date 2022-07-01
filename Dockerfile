FROM python:3.8

ARG PIP_PACKAGES=requirements.txt

RUN groupadd --gid 1000 scheduler
RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 scheduler

USER scheduler
ENV PATH=/home/scheduler/.local/bin:${PATH}

WORKDIR /app/scheduler

COPY ["requirements.txt", "${PIP_PACKAGES}", "logging.json", "./"]
RUN pip install -r ${PIP_PACKAGES}

COPY scheduler/ /app/scheduler/

CMD ["python", "-m", "scheduler"]
