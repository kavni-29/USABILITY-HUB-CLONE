# Interview guide

**Why Flask and server-rendered pages?** The existing project was plain HTML/CSS. Flask/Jinja extends it without replacing its assets or adding a frontend build system; Blueprints separate authentication, builder, participants, and analytics.

**How are passwords and sessions handled?** Werkzeug's password hashing API stores only a hash. Flask-Login manages the signed session cookie; cookies are HttpOnly and SameSite=Lax, and Secure is enabled in production. Flask-WTF protects state-changing forms with CSRF tokens.

**How are users isolated?** Private routes load a resource and compare its owner ID to the authenticated user. Foreign and missing IDs both return 404; a hidden or disabled button is never the authorization boundary.

**Why normalized tables?** A study contains ordered questions/options, and a submission answers questions. Separate rows make result aggregation queryable and keep response data out of opaque JSON blobs.

**How do publication and participant access work?** A draft has no public submissions. Published studies resolve via an opaque random token. Closed and archived states reject new responses. The server validates each answer against saved question type/options/ranges before storing.

**How do duplicate submissions work?** Each page load receives a random submission idempotency key. Replaying the same key is ignored by a unique constraint; opening the link again creates a fresh key and counts as another response. This prevents retries from double-counting, but does not identify real people.

**How are analytics presented?** Results are calculated from saved Answer rows and displayed as CSS charts: horizontal distribution bars for choice/rating questions and a daily activity chart. Multi-select percentages are per respondent and can sum above 100%; no population or causal claims are made.

**How is CSV made safe?** Python's CSV writer handles delimiters, quotes, and line breaks; cells beginning with spreadsheet formula markers are prefixed. Export routes enforce ownership.

**How are schema changes deployed on the free plan?** Current Render start configuration runs `flask db upgrade` before Gunicorn. Alembic applies only pending revisions. On scale-out, use a serialized pre-deploy/release migration step instead of every instance starting migrations.

**How does scheduled close work?** The creator picks a local date/time; the browser sends its timezone offset and the server stores UTC. Requests after the deadline are rejected. A background worker is not configured, so the visible lifecycle status updates on the next dashboard or participant request after the deadline.

**What remains?** No live PostgreSQL integration suite, rate limiting, email verification, account-deletion UI, complete test coverage, background scheduler, or formal security audit.
