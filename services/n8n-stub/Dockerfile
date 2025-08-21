FROM python:3.11-slim
WORKDIR /app
COPY health_stub.py /app/health_stub.py
RUN pip install --no-cache-dir flask==3.0.3 gunicorn==22.0.0
EXPOSE 7056
CMD ["gunicorn","-w","1","-b","0.0.0.0:7056","health_stub:app"]

