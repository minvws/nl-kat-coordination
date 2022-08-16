FROM python:3.8

ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID bytes
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID bytes

USER bytes
WORKDIR /app/bytes
ENV PATH=/home/bytes/.local/bin:${PATH}

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY . .

CMD ["uvicorn", "bytes.api:app", "--host", "0.0.0.0", "--port", "8000"]
