FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py /app/
CMD ["gunicorn","-w","2","-b","0.0.0.0:7001","bot_api:app"]
