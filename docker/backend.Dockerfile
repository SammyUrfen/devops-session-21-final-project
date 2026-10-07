# Build context: application/backend
# Alpine instead of Debian slim: far fewer OS packages, so far fewer unfixed HIGH CVEs (lesson from session 17).
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
# pip is removed after the install: the app never runs it, and its vendored libs carried fixable HIGH CVEs.
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y pip && \
    rm -rf /usr/local/lib/python3.12/ensurepip && \
    adduser -D -H -u 10001 appuser

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

USER 10001
EXPOSE 8000
# Migrate first, then serve. exec makes uvicorn PID 1 so it gets SIGTERM on pod shutdown.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
