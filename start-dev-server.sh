#!/usr/bin/env bash

# Mirrors entrypoint.sh, which already imports agents on every container boot —
# without this, editing a prompt file locally does nothing until you remember to
# run importagents by hand. Deliberately not fatal: a malformed prompt file
# should print an error, not stop you starting the server.
./env/bin/python manage.py importagents

./env/bin/gunicorn --reload justcanora.wsgi:application --bind 0.0.0.0:8000
