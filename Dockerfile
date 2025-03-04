FROM python:3.12
RUN apt-get update -y \
    && apt-get install -y git

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN git config --global --add safe.directory /app
