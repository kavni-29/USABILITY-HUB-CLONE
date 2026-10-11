# Route and form reference

The application uses Flask-rendered HTML forms, not a JSON REST API. State-changing requests include a Flask-WTF CSRF token. Authenticated private routes check ownership and return 404 for foreign resources.

| Method and route | Access | Behavior / fields |
| --- | --- | --- |
| `GET /` | Public | Existing marketing page. |
| `GET, POST /auth/register` | Public | Form: `email`, `password`. |
| `GET, POST /auth/login` | Public | Form: `email`, `password`. |
| `POST /auth/logout` | Signed in | Ends the session. |
| `GET /dashboard` | Signed in | Current owner's studies and metrics. Optional query parameters: `q`, `status`. |
| `GET, POST /tests/new` | Signed in | Form: `title`, `description`, `methodology`. Creates draft. |
| `GET, POST /tests/<id>/edit` | Owner | `action=details`, `question`, `update_question`, `delete_question`, or `reorder`; form values are validated server-side. |
| `GET /tests/<id>/preview` | Owner | Participant-style preview; never accepts answers. |
| `POST /tests/<id>/publish` | Owner | Draft/published lifecycle action. |
| `POST /tests/<id>/close`, `/reopen`, `/archive`, `/delete` | Owner | Enforced state transitions; deletion is blocked after responses. |
| `GET, POST /p/<token>` | Public | Published-study form and response submission; hidden idempotency key protects POST retries. |
| `GET /tests/<id>/results` | Owner | Question summaries, trend, and evidence-based insights. |
| `GET /tests/<id>/export.csv` | Owner | Formula-safe answer-level CSV download. |
| `GET /health` | Public | Availability and database connection status; does not verify all migrations. |

Question form types: `single_choice` and `yes_no` use one option value; `multiple_choice` accepts repeated `q_<question_id>` values; `text_response` accepts one string; `rating` accepts an integer in the configured range. The participant endpoint accepts standard form encoding. Internal numeric study/question IDs are only used inside authenticated pages; public access uses the token.
