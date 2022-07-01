FROM python:3.8

WORKDIR /app/bytes

RUN mkdir /home/bytes
RUN groupadd --gid 1000 bytes
RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 bytes
RUN chown bytes:bytes /home/bytes
USER bytes
ENV PATH=/home/bytes/.local/bin:${PATH}

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY . .

CMD ["uvicorn", "bytes.api:app", "--host", "0.0.0.0", "--port", "8000"]
