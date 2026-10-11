import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def flask_command(database_url, *args):
    env = {**os.environ, "DATABASE_URL": database_url, "SECRET_KEY": "migration-test-secret", "FLASK_ENV": "testing"}
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "wsgi", "db", *args],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, check=True,
    )


def test_expand_migration_preserves_existing_study_and_answers(tmp_path):
    database_path = tmp_path / "migration.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    flask_command(database_url, "upgrade", "bd6f43a874be")
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO user (id, email, password_hash, created_at) VALUES (1, 'owner@example.com', 'hash', '2026-01-01T00:00:00+00:00')")
        connection.execute("INSERT INTO usability_test (id, owner_id, title, description, public_token, is_published, created_at, updated_at) VALUES (1, 1, 'Old study', '', 'opaque-token', 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')")
        connection.execute("INSERT INTO question (id, test_id, prompt, question_type, required, position, rating_min, rating_max) VALUES (1, 1, 'Pick one', 'multiple_choice', 1, 0, NULL, NULL)")
        connection.execute("INSERT INTO question_option (id, question_id, label, position) VALUES (1, 1, 'A', 0), (2, 1, 'B', 1)")
        connection.execute("INSERT INTO response (id, test_id, submitted_at) VALUES (1, 1, '2026-01-02T00:00:00+00:00')")
        connection.execute("INSERT INTO answer (id, response_id, question_id, option_id, value) VALUES (1, 1, 1, 2, NULL)")
        connection.commit()
    flask_command(database_url, "upgrade")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT status, methodology FROM usability_test WHERE id=1").fetchone() == ("published", "general")
        assert connection.execute("SELECT question_type FROM question WHERE id=1").fetchone() == ("single_choice",)
        assert connection.execute("SELECT option_id FROM answer WHERE id=1").fetchone() == (2,)
        assert connection.execute("SELECT COUNT(*) FROM response").fetchone() == (1,)
