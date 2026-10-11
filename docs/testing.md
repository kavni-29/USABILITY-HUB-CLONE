# Testing

Run with Python 3.11+:

```sh
python -m pytest -q
python -m compileall -q app tests
python -m flask --app wsgi db check
```

`tests/conftest.py` creates an in-memory SQLite database per test fixture and tears it down after use. The Flask test client covers registration/password hashing, protected routes, ownership checks, public submission validation, repeat-submit behavior, analytics/CSV, assets, and health. Additional tests cover question types and state transitions, pure insight calculations, and migration of existing records. The verified run for this revision is 11 passing tests plus successful `compileall`. These tests do not connect to production or a live PostgreSQL database. Before production schema changes, review migrations and test them against a disposable PostgreSQL database when available. The default local `usabilityhub.db` is not used by the test fixture.
