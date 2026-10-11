# Implementation plan and feature audit

## Repository baseline (2026-10-12)

The original repository was a static HTML/CSS UsabilityHub-style landing page with local image assets, no package manager, and no backend. It is now extended with Python 3.11/3.14-compatible Flask, SQLAlchemy, Flask-Login, Flask-WTF CSRF, Alembic migrations, pytest, PostgreSQL via psycopg, and Gunicorn. Pages are server-rendered Jinja; no frontend framework or JSON REST API is present.

Git was clean at `e3a5537` before this work. The existing deployment configuration is Render Blueprint plus `wsgi.py`; on the free service, database migrations run in the start command before Gunicorn because Render pre-deploy commands require a paid service.

## Feature status

| Area | Baseline status | This work's acceptance target |
| --- | --- | --- |
| Marketing landing page | Existing HTML/CSS and assets, not a frontend framework; baseline links and mobile/focus behavior needed review | Keep the existing visual identity and make calls to action useful; rendered visual QA still requires a browser pass |
| Authentication | Flask-Login sessions, Werkzeug password hashes, Flask-WTF CSRF; registration/login/logout already existed | Preserve ownership and handle duplicate-registration races without a 500 |
| Study lifecycle | Create/edit, publish toggle, response-protected deletion; only draft/published states | Add methodology, closed/archived states and server-enforced transitions |
| Builder | Choice/preference/rating questions; edits lock after responses | Add single-choice, multi-select, text, yes/no, accessible reorder and preview |
| Participant flow | Opaque public token, published-only access, persistent answers; each POST counted separately | Validate each type and make same-form retries idempotent while allowing a fresh visit |
| Dashboard | Real study/response counts and share links | Add status metrics, search/filter, close/archive and question management |
| Analytics | Stored option counts and rating mean, owner-only CSV | Add multi-select rates, text answers, response trend, evidence-based insights and CSV formula safety |
| API | No separate JSON API; server-rendered form routes | Document actual routes, methods, and form fields; do not document imaginary REST endpoints |
| Migrations | Initial schema migration | Add a forward-only migration preserving existing records |
| Tests | Five critical-path Flask client tests | Cover new question types, transitions, idempotency, insight calculations, CSV and ownership |
| Documentation | README with architecture and interview notes | Add architecture, schema, route/API, testing, deployment, and interview docs |

## Decisions and safety

- Keep the existing Flask/Jinja stack and relational model; no React, paid AI service, or analytics dependency is needed.
- Preserve old question meaning: existing `multiple_choice` prompts are single-select, so the migration renames that type to `single_choice` before adding multi-select.
- Preserve the old publication flag during transition; new status is canonical and old deployments can be migrated without dropping study/answer data.
- Question structure can still be edited only before the first response; after that it is locked to preserve historical interpretation. Study title/description may be corrected. A study with responses is archived rather than deleted.
- A public submission has a random idempotency key so a retry of the same form post does not double-count. Opening the link again creates a fresh key and is treated as a separate submission; this is not a real-person identity guarantee.
- Insights report observed counts and sample sizes, describe ties/low samples plainly, and never claim causality or statistical significance.

## Acceptance checklist

- [x] Preserve the existing landing page and make key entry points meaningful; a full visual browser QA pass remains outstanding.
- [x] Keep authentication, resource ownership, CSRF, secure sessions, and PostgreSQL configuration; registration handles a duplicate-email race.
- [x] Add methodology and draft/published/closed/archived status transitions.
- [x] Support single-choice, multiple-choice, text response, rating, and yes/no questions with server validation.
- [x] Provide keyboard-operable question reorder controls and owner-only preview.
- [x] Reject participant submissions unless published; validate answer types and deduplicate same-key retries.
- [x] Populate dashboard status metrics from SQL and implement search/filter/actions.
- [x] Show stored-data analytics for options, multi-select rates, ratings, text answers, response timeline, and deterministic insights.
- [x] Keep CSV owner-only and formula-safe.
- [x] Add a forward migration and tests; test suite and SQLite data-preservation migration test pass.
- [x] Keep Render start command compatible with the user's no-shell plan and document migration-on-start behavior.
- [x] Document routes, implementation, deployment constraints, and limitations without claiming a live deployment or security audit.
- [ ] Verify the deployed Render registration flow from logs/browser; this workspace has no Render shell/account access and `/health` verifies connectivity only.
- [ ] Run browser-based visual/accessibility review and PostgreSQL integration tests; these are not covered by the local SQLite suite.
