# Testing

Run with Python 3.11+:

```sh
python -m pytest -q
python -m compileall -q app tests
python -m flask --app wsgi db check
```

`tests/conftest.py` creates an in-memory SQLite database per test fixture and tears it down after use. The Flask test client covers registration/password hashing, protected routes, ownership checks, public submission validation, repeat-submit behavior, response charts, scheduled closes, CSV, assets, and health. The migration test verifies existing records survive schema conversion. The current chart/schedule revision passes 9 tests and `python -m compileall -q app tests`. Tests do not connect to production or a live PostgreSQL database. Before production schema changes, review migrations and test them against a disposable PostgreSQL database when available. The default local `usabilityhub.db` is not used by the test fixture.
