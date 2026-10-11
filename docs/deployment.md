# Render deployment

The Git repository has a Blueprint at its root, so leave Render Root Directory blank. It provisions a Python web service and managed PostgreSQL database. Set `SECRET_KEY` using Render's generated value and let Render inject `DATABASE_URL` from the database connection string. Do not copy secrets into GitHub.

Build command: `pip install -r requirements.txt`.

Start command for the current no-shell/free-plan setup: `flask --app wsgi db upgrade && gunicorn wsgi:app`. This applies pending Alembic revisions, then starts the app. The migration command is idempotent, but this startup strategy assumes a single service instance. Render documents pre-deploy commands as paid-service-only; on a paid service, prefer a pre-deploy migration command and `gunicorn wsgi:app` for startup.

The service must have `SECRET_KEY`, `DATABASE_URL`, and `FLASK_ENV=production`. `/health` checks connectivity with `SELECT 1`. After deployment, validate account registration, publishing, participant submission, results, and CSV. A healthy `/health` does not prove all schema migrations have run.

No deployment has been remotely inspected by this repository workflow. Use Render's deploy logs to confirm the migration command ran; the application code should not expose database credentials or tracebacks to visitors.
