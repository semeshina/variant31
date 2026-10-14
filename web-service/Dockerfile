FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask==3.0.3

COPY service.py .

EXPOSE 5001

CMD ["python", "service.py"]
