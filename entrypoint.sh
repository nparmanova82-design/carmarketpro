#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py seed_brands

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi

exec "$@"
