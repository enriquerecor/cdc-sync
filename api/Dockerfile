FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY api /app/api

FROM base AS runtime

RUN pip install --no-cache-dir ./api

CMD ["uvicorn", "cdc_sync_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test

RUN pip install --no-cache-dir ./api[dev]

CMD ["pytest", "api/tests", "-v"]
