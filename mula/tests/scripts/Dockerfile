FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r /app/requirements.txt
ENTRYPOINT ["python3", "/app/load.py"]
