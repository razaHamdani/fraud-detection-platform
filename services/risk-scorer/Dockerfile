FROM python:3.11-slim

WORKDIR /app

COPY shared/ /app/shared/
RUN pip install --no-cache-dir /app/shared/

COPY services/risk-scorer/ /app/service/
RUN pip install --no-cache-dir /app/service/

CMD ["uvicorn", "risk_scorer.main:app", "--host", "0.0.0.0", "--port", "8003"]
