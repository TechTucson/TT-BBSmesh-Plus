FROM python:3.11-slim

RUN pip install fastapi uvicorn

WORKDIR /app
COPY api.py .

CMD ["uvicorn","api:app","--host","0.0.0.0"]
