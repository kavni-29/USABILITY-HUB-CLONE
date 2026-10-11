# UsabilityHub

A lightweight usability research platform built around the original HTML/CSS landing page. Owners can create and publish studies, share a public participant link, collect answers, and inspect counts, percentages, rating averages, or a CSV export.

## Architecture

```mermaid
flowchart LR
  Browser[Browser: existing HTML, CSS, assets] --> Flask[Flask app / blueprints]
  Flask --> Auth[Authentication]
  Flask --> Builder[Test builder and dashboard]
  Flask --> Participant[Public participant flow]
  Flask --> Analytics[Results and CSV]
  Auth --> DB[(PostgreSQL / local SQLite)]
  Builder --> DB
  Participant --> DB
  Analytics --> DB
```

```mermaid
erDiagram
  USER ||--o{ USABILITY_TEST : owns
  USABILITY_TEST ||--o{ QUESTION : contains
  QUESTION ||--o{ QUESTION_OPTION : offers
  USABILITY_TEST ||--o{ RESPONSE : receives
  RESPONSE ||--o{ ANSWER : contains
  QUESTION ||--o{ ANSWER : answers
  QUESTION_OPTION ||--o{ ANSWER : selected
```

## Stack and design choices

- Python 3 and Flask Blueprints keep request handling modular and explainable.
- Flask-SQLAlchemy maps normalized relational models; Flask-Migrate/Alembic manages schema changes.
- PostgreSQL is configured for deployment. Local development defaults to SQLite.
- Flask-Login provides cookie-based sessions; Werkzeug provides password hashing; Flask-WTF applies CSRF protection.
- Server-rendered Jinja pages reuse the existing landing page instead of replacing the frontend with a framework.

## Local setup

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; on macOS/Linux use cp
```

Set `SECRET_KEY` to a private random value before real use. With SQLite (the default), apply the schema and launch:

```sh
flask --app wsgi db upgrade
flask --app wsgi run --debug
```

The repository includes the initial migration. When changing models during development, create a new revision with `flask --app wsgi db migrate -m "Describe schema change"`, review the generated migration, then apply it with `flask --app wsgi db upgrade`.

To use PostgreSQL locally, set `DATABASE_URL` to a PostgreSQL connection string. Commit generated migration revisions; deployments run `flask --app wsgi db upgrade` as part of the Render build command. Never point tests or development at production data.

## Tests

```sh
pytest
```

The suite uses an isolated in-memory SQLite database and checks password hashing, login, protected pages, resource ownership, public submissions, unpublished-link rejection, analytics, and CSV access. It is an initial critical-path suite, not a complete security assessment.

## Render deployment

1. Push this repository to GitHub and create a Render Blueprint from `render.yaml`.
2. Review the web service and managed PostgreSQL instance in Render. The blueprint creates the service resources; it does not mean the application is already deployed.
3. Render generates `SECRET_KEY` and injects the managed database URL. Keep both out of source control.
4. The build command installs dependencies. The start command applies committed Alembic migrations before launching `gunicorn wsgi:app`. This keeps the free-plan setup self-contained; `flask db upgrade` applies only pending revisions on each process start. `/health` checks the database and reports only availability.
5. Confirm the deployed health check and perform an account creation, test publishing, and participant submission in the deployed environment.

The app trusts one proxy hop in production for HTTPS scheme/host forwarding. Secure session cookies are enabled when `FLASK_ENV=production`. Configure an explicit `SECRET_KEY` and a PostgreSQL `DATABASE_URL` in any non-Render hosting environment too.

## Configuration

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session and CSRF signing key; required in production. |
| `DATABASE_URL` | SQLAlchemy database URL; defaults to local `sqlite:///usabilityhub.db`. |
| `FLASK_ENV` | Set to `production` for secure-cookie/proxy configuration. |

## Route overview

| Route | Purpose |
| --- | --- |
| `/` | Existing public marketing page |
| `/auth/register`, `/auth/login`, `/auth/logout` | Account lifecycle |
| `/dashboard` | Current user's studies and response counts |
| `/tests/new`, `/tests/<id>/edit` | Create and manage studies/questions |
| `/tests/<id>/publish` | Publish/unpublish |
| `/p/<token>` | Public participant flow |
| `/tests/<id>/results`, `/tests/<id>/export.csv` | Owner-only analytics/export |
| `/health` | Application/database availability |

## Security and data policy

Passwords are hashed, state-changing forms use CSRF tokens, queries are parameterized through SQLAlchemy, private study access checks ownership, participant links use 256-bit random tokens, and rendered user text is escaped by Jinja. CSV cells beginning with spreadsheet formula markers are prefixed to reduce formula injection risk. Production should use HTTPS and a private environment secret. The application stores account email, test/question content, response timestamps, and submitted answers; it does not request participant identity. A public link permits repeat submissions and each is counted independently; browser identity is not treated as a person-level uniqueness guarantee.

Questions cannot be changed after the first response, and a study with responses cannot be deleted. This preserves the meaning and provenance of collected answers. Tests without responses can be deleted. Account deletion cascades through the account's studies and data at the database relationship level; there is no self-service account deletion screen yet.

## Known limitations and next steps

This is a portfolio-ready foundation, not a claim of production security or penetration testing. Question types are single-select multiple-choice/preference and numeric rating. Editing individual questions, pagination, account deletion UX, rate limiting, email verification, and audit logs remain future work. Expand automated tests for malformed answers, migration execution against PostgreSQL, constraint failures, and every management edge case before handling sensitive research.

## Files added or changed

- `index.html`: preserves the landing design while linking signup and usable product entry points.
- `config.py`, `wsgi.py`: environment config and WSGI entry point.
- `app/`: Flask factory, extensions, models, blueprints, templates, and responsive app styling.
- `tests/`: isolated critical-path Flask client tests.
- `requirements.txt`, `.env.example`, `.gitignore`: dependencies and local configuration hygiene.
- `render.yaml`: Render web service and managed PostgreSQL blueprint.

No live deployment has been created or verified.

## Interview notes

- **Why separate `Response` and `Answer`?** One submission can answer many questions; relational rows preserve queryable results and avoid a large opaque JSON blob.
- **How is ownership enforced?** Every private operation loads the resource and compares its `owner_id` to the authenticated session user; unknown and foreign IDs both return 404.
- **How does the participant lifecycle work?** A random public token resolves only to a published study. Server-side validation checks required values, option membership, and rating bounds before committing one response plus its answers.
- **How are old results protected?** Question structure locks after a first submission; deletion is blocked when responses exist. This prevents existing answers being reinterpreted.
- **Why no unique participant ID?** The app collects no unnecessary identity data. Repeat submissions are allowed and counted separately; a cookie would not prove distinct real people.
- **What would you improve next?** Add rate limiting and email verification, broader PostgreSQL integration tests, edit/reorder UX before publication, account deletion, and a clearer privacy/retention workflow.
