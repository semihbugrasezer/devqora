FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY content_api.py .
ENV CONTENT_ROOT=/content
CMD ["python","/app/content_api.py"]
