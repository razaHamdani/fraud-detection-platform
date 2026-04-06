FROM python:3.11-slim

WORKDIR /app

COPY shared/ /app/shared/
RUN pip install --no-cache-dir /app/shared/

COPY services/feature-engine/ /app/service/
RUN pip install --no-cache-dir /app/service/

CMD ["uvicorn", "feature_engine.main:app", "--host", "0.0.0.0", "--port", "8002"]
