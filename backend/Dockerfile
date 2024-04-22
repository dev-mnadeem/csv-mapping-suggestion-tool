# Build the dependency layer once, then copy only the application in.
FROM python:3.12-slim AS deps

WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/opt/venv -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

COPY --from=deps /opt/venv /opt/venv

WORKDIR /app
COPY app ./app
COPY scripts ./scripts

# The SQLite file lives on a volume, so the directory has to belong to the
# unprivileged user that runs the server.
RUN useradd --create-home --uid 10001 mapper \
    && mkdir -p /app/data \
    && chown -R mapper:mapper /app
USER mapper

EXPOSE 7241

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7241/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7241"]
