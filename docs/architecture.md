# Architecture

```mermaid
flowchart LR
  Browser[HTML/CSS/Jinja pages] --> Flask[Flask application factory]
  Flask --> Auth[auth blueprint]
  Flask --> Dashboard[dashboard blueprint]
  Flask --> Participant[participant blueprint]
  Flask --> Analytics[analytics blueprint]
  Auth --> ORM[SQLAlchemy models]
  Dashboard --> ORM
  Participant --> ORM
  Analytics --> Insights[deterministic insights module]
  Insights --> ORM
  ORM --> DB[(PostgreSQL on Render / SQLite locally and in tests)]
```

`app.create_app()` wires Flask-Login, CSRF, SQLAlchemy, Flask-Migrate, static assets, and blueprints. Route functions validate requests, apply ownership/status checks, and commit a transaction through the ORM. Jinja autoescapes titles, descriptions, prompts, and text answers. Static design assets remain under `assets/`; app workflow styles are in `app/static/app.css`.

An owner creates a draft; questions/options are stored as rows. Publication gives participants a random opaque token. A participant GET resolves only published studies. POST validates question IDs and type-specific values against the current saved question configuration, checks the idempotency key, then stores one submission and its answers in a transaction. Owners query aggregated values through authenticated result/export routes. Insights are pure deterministic calculations over these same persisted answer rows.

Database migrations are forward-only. Render's current free-plan configuration runs `flask --app wsgi db upgrade` before Gunicorn in the start command. On every process start Alembic checks and applies pending revisions; for this single-instance portfolio service, this avoids dependence on an inaccessible Render Shell. Scale-out should move migrations to a serialized release/pre-deploy job before adding instances.
