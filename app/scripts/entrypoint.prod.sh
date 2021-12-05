#!/bin/sh

set -e

python manage.py migrate --no-input
python manage.py collectstatic --no-input

gunicorn cradle_of_mankind.wsgi:application --bind 0.0.0.0:8000
