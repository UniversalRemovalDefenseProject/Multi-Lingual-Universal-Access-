# Quality gates

The smallest gate system that actually protects this repo (Django 6 + Postgres,
single package, i18n, server-rendered templates). Every gate below runs the **same
command** locally and in CI — they cannot diverge.

## Run locally

```bash
make install-dev   # one-time: .venv on the pinned Python + dev tooling
make hooks         # one-time: install pre-push + commit-msg hooks
make gate          # secret-free gates (static + build + tests) — run before every push
make gate-full     # gate + network gates (CVE audit + secret range scan) = what CI runs
```

`make gate` guards the runtime first (refuses to run on anything but the pinned
Python in `.python-version`), runs the static gates in parallel, then the test
gate. It auto-starts an ephemeral Postgres via Docker if none is reachable and
tears it down after. Individual gates are also targets: `make lint`, `make test`, etc.

## The gates

| Gate | What it catches | Command | Local | CI job |
|------|-----------------|---------|:-----:|--------|
| Format | Style drift, unreviewable diffs | `ruff format --check .` | ✅ | `static` |
| Lint (+ security, Django) | Bugs (unused/undefined names), insecure patterns (`S`/flake8-bandit), Django anti-patterns (`DJ`) | `ruff check .` | ✅ | `static` |
| Boot check | Eager-init crashes, broken settings/URLs | `python manage.py check` | ✅ | `static` |
| Migration drift | Models changed without a migration | `python manage.py makemigrations --check --dry-run` | ✅ | `static` |
| i18n build | `.po` catalogs that won't compile (the app's real build step) | `python manage.py compilemessages` | ✅ | `static` |
| Tests + coverage | Regressions in views/forms/flows; coverage below the 95% ratchet | `coverage run manage.py test && coverage report` | ✅ | `tests` |
| CVE audit | Known vulnerabilities in shipped deps | `pip-audit -r requirements.txt` | `--full` | `audit` |
| Secret scan | Credentials introduced by the PR's commits | `gitleaks git --log-opts=<range>` | `--full` | `secrets` |
| Workflow lint | Broken/injection-prone CI YAML | `actionlint` | ✅ (if installed) | `workflows` |
| Commit message | Non–Conventional-Commit headers | `.githooks/commit-msg` | hook | — |

Security lint and coverage ride inside existing gates rather than adding tools:
`ruff` runs the flake8-bandit (`S`) ruleset, and coverage's threshold lives in
`pyproject.toml` (`fail_under = 95`, just under the measured 98% baseline — raise by
hand, never auto-tune).

## CI shape

`.github/workflows/gates.yml`, on every PR and on push to `main`.

```
static ─┐
tests  ─┤
audit  ─┼──▶ gates   (the ONE required check)
secrets─┤
workflows┘
```

Five gate jobs start together (no gate needs another's artifact). The **`gates`**
job `needs` all five, runs with `if: always()`, and fails if any result is not
`success` — so a failure, cancellation, or unexpected skip can never let it pass
vacuously. Posture: read-only token, `persist-credentials: false`, actions pinned
by commit SHA, scanners pinned by version, per-ref `cancel-in-progress`, explicit
timeout on every job.

## Branch protection

Require exactly one status check — **`gates`** — on `main`. With the GitHub CLI:

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  -F 'required_status_checks[strict]=true' \
  -F 'required_status_checks[contexts][]=gates' \
  -F 'enforce_admins=true' \
  -F 'required_pull_request_reviews=' \
  -F 'restrictions='
```

(No required review, per project preference — the passing `gates` check is the bar.)

## Secret scan scope — and the one-time cleanup it defers

The secret gate scans the **PR/push commit range**, not full history, so it blocks
*newly introduced* secrets while staying green for clean branches. Full-history
scanning is deliberately **not** a blocking gate here: history already contains a
Django `django-insecure-` development key (commit `5ac6c5c`, later replaced with
`env()`), so a full-history gate could never pass. That key is a low-risk dev
placeholder, but the correct one-time remediation — tracked separately, not as a
merge blocker — is:

1. Rotate the real production `SECRET_KEY` (set via env, already the case in code).
2. Optionally scrub history (`git filter-repo`/BFG) and force-push.

## Cut gates (considered, deliberately not added)

| Gate | Why cut |
|------|---------|
| **Type check (mypy/pyright)** | Codebase has no type annotations; adding a type gate means a large baseline of noise for zero current signal. Revisit only if the team starts annotating. |
| **Standalone bandit** | Fully overlaps `ruff`'s flake8-bandit (`S`) ruleset. Kept one tool, cut the other. |
| **isort / black** | `ruff format` + `ruff check --select I` cover formatting and import order in one tool. |
| **Dead-code / unused-deps (vulture, deptry)** | 3 runtime deps; unused-dependency risk is ~nil, and `ruff` (`F401`) already flags unused imports. |
| **Browser / e2e (Playwright)** | No JS build; server-rendered templates. The Django test client already exercises whole request→response flows in the `tests` gate. A browser runner would be large new surface for little added coverage. |
| **Full-history secret scan (blocking)** | Would never pass due to the historical dev key above. Replaced by a range scan + a documented one-time cleanup. |
| **Live-model / paid-API tests** | None exist in this project — nothing to gate. |
| **Dependabot** | Kept as automation (`.github/dependabot.yml`) but it is not a pass/fail gate, so it is not part of the `gates` check. |
