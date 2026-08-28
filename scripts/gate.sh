#!/usr/bin/env bash
# The single local runner. Every gate below is ALSO run by CI
# (.github/workflows/gates.yml) using the SAME underlying command — local and CI
# never diverge in what they check.
#
#   scripts/gate.sh          secret-free, offline gates (static + build + tests)
#   scripts/gate.sh --full   appends the network gates (CVE audit + secret range scan)
#
# This project has no gate that needs a credential, so there is nothing to skip:
# --full adds the checks that merely need the network, not secrets. CI runs everything.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Prefer the project venv if present so tools resolve to pinned versions.
[ -d .venv/bin ] && PATH="$ROOT/.venv/bin:$PATH"
PYBIN="${PYBIN:-python}"

# Deterministic, secret-free env so gates run on a bare clone with no .env.
# django-environ only fills keys absent from the environment, so these win.
export DJANGO_SETTINGS_MODULE=urdp.settings
export SECRET_KEY="${SECRET_KEY:-dev-not-a-secret}"
export DEBUG="${DEBUG:-True}"
export POSTGRES_DB="${POSTGRES_DB:-urdp}"
export POSTGRES_USER="${POSTGRES_USER:-urdp}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
export POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"

FULL=0
[ "${1:-}" = "--full" ] && FULL=1

# --- runtime pin guard: refuse a mismatched runtime BEFORE any cached step ---
want="$(tr -d ' \n\r' < .python-version)"
have="$("$PYBIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
if [ "$want" != "$have" ]; then
  echo "✗ runtime: pinned Python $want but got '${have:-none}'." >&2
  echo "  Install $want (e.g. 'pyenv install $want' or 'brew install python@$want')" >&2
  echo "  and recreate the venv, or set PYBIN to a $want interpreter." >&2
  exit 1
fi

# --- gate registry ----------------------------------------------------------
STATIC_NAMES=(); STATIC_CMDS=()
add_static() { STATIC_NAMES+=("$1"); STATIC_CMDS+=("$2"); }

# format + lint are one tool (ruff); security lint (flake8-bandit "S" rules) and
# Django anti-pattern rules ("DJ") ride along in `ruff check`.
add_static "format"       "ruff format --check ."
add_static "lint"         "ruff check ."
# Build/boot: import every app, validate settings/URLs; catches eager-init crashes.
add_static "django-check" "$PYBIN manage.py check"
# Data layer: models and migration files must not have drifted apart.
add_static "migrations"   "$PYBIN manage.py makemigrations --check --dry-run"
# Real build step for this app: compile the .po translation catalogs to .mo.
add_static "i18n-build"   "$PYBIN manage.py compilemessages --ignore='*/site-packages/*'"
# Lint the CI workflows themselves (syntax + injection / mutable-ref checks).
command -v actionlint >/dev/null 2>&1 && add_static "workflows" "actionlint"

run_parallel() {  # runs registered static gates concurrently; fails if any fail
  local -a names=("$@") pids=() logs=()
  local i fail=0
  for i in "${!STATIC_NAMES[@]}"; do
    logs[i]="$(mktemp)"
    bash -c "${STATIC_CMDS[$i]}" >"${logs[i]}" 2>&1 &
    pids[i]=$!
  done
  for i in "${!STATIC_NAMES[@]}"; do
    if wait "${pids[i]}"; then
      echo "  ✓ ${STATIC_NAMES[$i]}"
    else
      echo "  ✗ ${STATIC_NAMES[$i]} — FAILED"
      sed 's/^/      /' "${logs[i]}"
      fail=1
    fi
    rm -f "${logs[i]}"
  done
  return $fail
}

run_one() {  # name, command — serial; streams output; returns command status
  local name="$1"; shift
  echo "▶ $name"
  if bash -c "$*"; then echo "  ✓ $name"; return 0; else echo "  ✗ $name — FAILED"; return 1; fi
}

# --- ephemeral Postgres for the test gate (local only; CI uses a service) ----
STARTED_DB=0
DB_CONTAINER="urdp-gate-db"
db_reachable() {
  "$PYBIN" - <<'PY' 2>/dev/null
import os, socket, sys
s = socket.socket(); s.settimeout(1)
try:
    s.connect((os.environ["POSTGRES_HOST"], int(os.environ["POSTGRES_PORT"])))
except Exception:
    sys.exit(1)
PY
}
ensure_db() {
  db_reachable && return 0
  if ! command -v docker >/dev/null 2>&1; then
    echo "✗ tests need Postgres at $POSTGRES_HOST:$POSTGRES_PORT and Docker is not available." >&2
    echo "  Start a Postgres yourself or install Docker, then re-run." >&2
    return 1
  fi
  echo "  · starting ephemeral Postgres ($DB_CONTAINER)"
  docker run -d --rm --name "$DB_CONTAINER" \
    -e POSTGRES_DB="$POSTGRES_DB" -e POSTGRES_USER="$POSTGRES_USER" \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" -p "$POSTGRES_PORT:5432" \
    postgres:18 >/dev/null || return 1
  STARTED_DB=1
  local i
  for i in $(seq 1 30); do
    docker exec "$DB_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "✗ Postgres did not become ready in time." >&2
  return 1
}
cleanup() { [ "$STARTED_DB" = 1 ] && docker stop "$DB_CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# --- run: static (parallel) → heavy (serial) → full-only (network) ----------
echo "▶ static gates"
run_parallel || { echo "✗ static gates failed — stopping before heavy gates."; exit 1; }

ensure_db || exit 1
run_one "tests+coverage" "coverage run manage.py test && coverage report" || exit 1

if [ "$FULL" = 1 ]; then
  run_one "audit (CVEs)" "pip-audit -r requirements.txt" || exit 1
  if command -v gitleaks >/dev/null 2>&1; then
    run_one "secrets (PR range)" \
      "gitleaks git --no-banner --redact --log-opts='${GITLEAKS_RANGE:-origin/main..HEAD}'" || exit 1
  else
    echo "  · gitleaks not installed — skipping local secret scan (CI still enforces it)"
  fi
fi

echo "✓ all gates passed"
