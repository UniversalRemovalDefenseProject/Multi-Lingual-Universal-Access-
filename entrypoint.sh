#!/bin/sh
set -e

python manage.py migrate
# Django only reads .mo, and .mo is gitignored — compile on every start so a bare
# `docker run` serves translations, not just compose.
# compose mounts the repo at /app, so a developer's virtualenv would otherwise drag
# Django's own bundled catalogs into every start. Match site-packages rather than a
# venv name — the name varies (.venv, env, myenv), the install path doesn't.
python manage.py compilemessages --ignore='*/site-packages/*'

exec "$@"
