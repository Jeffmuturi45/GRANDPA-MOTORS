#!/usr/bin/env bash
set -o errexit

# Apply any migrations
python manage.py migrate

# Automatically setup admin and seed demo data if empty
python manage.py setup_admin

# Start gunicorn web server
exec gunicorn config.wsgi:application
