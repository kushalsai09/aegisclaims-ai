#!/bin/sh
set -eu

alembic upgrade head
python -m insurance_platform.seed
exec "$@"
