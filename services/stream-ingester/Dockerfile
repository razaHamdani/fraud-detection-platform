FROM python:3.11-slim

WORKDIR /app

# Install shared library (deps first for caching)
COPY shared/pyproject.toml /app/shared/pyproject.toml
COPY shared/src/ /app/shared/src/
RUN pip install --no-cache-dir /app/shared/

# Install service (deps first for caching)
COPY services/stream-ingester/pyproject.toml /app/service/pyproject.toml
COPY services/stream-ingester/src/ /app/service/src/
RUN pip install --no-cache-dir /app/service/

EXPOSE 8001
CMD ["uvicorn", "stream_ingester.main:app", "--host", "0.0.0.0", "--port", "8001"]
