FROM python:3.8

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . plugin_repository/

EXPOSE 8000

CMD ["uvicorn", "plugin_repository.api.main:app", "--host", "0.0.0.0"]
