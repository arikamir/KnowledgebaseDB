FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app --home /app app

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts/runtime/run-core-migration.sh ./scripts/run-migration.sh

RUN pip install .
RUN chmod 0555 /app/scripts/run-migration.sh \
    && chown -R app:app /app

# Keep the runtime identity numeric so Kubernetes can enforce runAsNonRoot
# without relying on image metadata name resolution.
USER 10001

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
