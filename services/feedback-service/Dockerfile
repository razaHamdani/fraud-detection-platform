FROM python:3.11-slim

WORKDIR /app

COPY shared/ /app/shared/
RUN pip install --no-cache-dir /app/shared/

COPY services/feedback-service/ /app/service/
RUN pip install --no-cache-dir /app/service/

CMD ["uvicorn", "feedback_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
