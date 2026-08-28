# Quality-gate entry points. `make gate` is the one command to run before pushing.
# See quality-gates.md for the full catalog and the CI mapping.
.DEFAULT_GOAL := help
.PHONY: help gate gate-full install-dev hooks db-up db-down \
        format lint static test audit secrets

PY ?= python3.12

help: ## List targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

gate: ## Run all secret-free gates (static + build + tests). Use before every push.
	@scripts/gate.sh

gate-full: ## gate + network gates (CVE audit + secret range scan). What CI runs.
	@scripts/gate.sh --full

install-dev: ## Create .venv with pinned runtime + dev tooling.
	$(PY) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt

hooks: ## Install client-side git hooks (pre-push secret scan, commit-msg lint).
	git config core.hooksPath .githooks
	@echo "hooks installed (core.hooksPath = .githooks)"

db-up: ## Start a local Postgres 18 for tests.
	docker run -d --rm --name urdp-gate-db \
		-e POSTGRES_DB=urdp -e POSTGRES_USER=urdp -e POSTGRES_PASSWORD=postgres \
		-p 5432:5432 postgres:18

db-down: ## Stop the local Postgres.
	-docker stop urdp-gate-db

# --- individual gates (each is one atomic command; CI runs these same ones) ---
format: ## Check formatting (no writes).
	.venv/bin/ruff format --check .

lint: ## Lint + security + Django checks.
	.venv/bin/ruff check .

test: ## Run the test suite under coverage (needs a reachable Postgres).
	.venv/bin/coverage run manage.py test && .venv/bin/coverage report

audit: ## Scan dependencies for known CVEs.
	.venv/bin/pip-audit -r requirements.txt

secrets: ## Scan the PR commit range for committed secrets.
	gitleaks git --no-banner --redact --log-opts="origin/main..HEAD"
