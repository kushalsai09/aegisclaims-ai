FROM python:3.13.14-alpine3.24 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup -S app && adduser -S -G app app
WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages/backend/src ./packages/backend/src
RUN python -m pip install .

COPY alembic.ini ./
COPY migrations ./migrations
COPY data/synthetic/manifests ./data/synthetic/manifests
COPY scripts/container-entrypoint.sh ./scripts/container-entrypoint.sh
RUN apk add --no-cache --upgrade openssl=3.5.8-r0
RUN test -f ./data/synthetic/manifests/phase2-scenarios.json \
    && chmod 0555 ./scripts/container-entrypoint.sh \
    && chown -R app:app /app

USER app
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1
ENTRYPOINT ["./scripts/container-entrypoint.sh"]
CMD ["uvicorn", "insurance_platform.delivery.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
