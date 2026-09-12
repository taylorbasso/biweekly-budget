FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

ENV BUDGET_DB_PATH=/data/budget.sqlite3
VOLUME ["/data"]
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "budget.wsgi:app"]
