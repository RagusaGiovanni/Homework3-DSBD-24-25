FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN pip install prometheus_client
CMD ["python", "main.py"]