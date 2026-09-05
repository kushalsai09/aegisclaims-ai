FROM python:3.13.14-alpine3.24 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup -S app && adduser -S -G app app
WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages/backend/src ./packages/backend/src
RUN python -m pip install .

RUN apk add --no-cache --upgrade openssl=3.5.8-r0
RUN chown -R app:app /app
USER app
STOPSIGNAL SIGTERM
CMD ["python", "-m", "insurance_platform.delivery.worker"]
