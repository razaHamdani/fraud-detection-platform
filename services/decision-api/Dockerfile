FROM python:3.11-slim

WORKDIR /app

# Install shared library (deps first for caching)
COPY shared/pyproject.toml /app/shared/pyproject.toml
COPY shared/src/ /app/shared/src/
RUN pip install --no-cache-dir /app/shared/

# Install service (deps first for caching)
COPY services/decision-api/pyproject.toml /app/service/pyproject.toml
COPY services/decision-api/src/ /app/service/src/
RUN pip install --no-cache-dir /app/service/

EXPOSE 8004
CMD ["uvicorn", "decision_api.main:app", "--host", "0.0.0.0", "--port", "8004"]
