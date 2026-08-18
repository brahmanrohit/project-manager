# Ethara — Project Management Application
## Product Requirements Document

| Field | Value |
|---|---|
| **Status** | Draft for review |
| **Version** | 0.9 (documents as-built system + v1.0 requirements) |
| **Author** | Rohit Sharma |
| **Last updated** | 18 August 2026 |
| **Reviewers** | — |
| **Related** | `README.md`, `DEPLOYMENT_GUIDE.md`, `backend/alembic/versions/0001_initial.py` |

---

## 1. Summary

Ethara is a self-hosted project and task management web application for small teams — a FastAPI/PostgreSQL backend and a React SPA, deployable to a single PaaS account for roughly the cost of a database instance.

A working system exists today. It handles signup and login, admin/member roles, project CRUD with membership, task CRUD with status and due dates, and an aggregate dashboard. This document does two things: it records what is built and why, and it defines what must be true before v1.0 can be exposed to users who are not the author.

The honest state of the system is that it is **feature-complete and not yet safe to deploy**. Section 8 lists four defects that block release, one of which allows any anonymous visitor to create an administrator account. The functionality is not in question; the authorization model is.

---

## 2. Problem statement

Small teams — three to fifteen people — need to know who is doing what and what is late. The tools available to them fail at one of three things:

**Cost at the wrong threshold.** Jira, Asana, and Linear price per seat. A six-person team pays for six seats to track perhaps forty tasks. The pricing is designed for organizations where the tool replaces coordination overhead measured in salaries; for a small team it replaces a spreadsheet.

**Complexity that outruns the need.** Jira's configurability is a genuine asset to a team with a dedicated administrator and a liability to one without. Sprints, epics, workflow states, custom fields, and permission schemes are a setup cost paid before any task is tracked.

**No data control.** SaaS tools hold the data. Teams working under client confidentiality terms, or in contexts where an external processor requires review, cannot always use them. Self-hosting is often not offered at all below enterprise tiers.

Ethara targets the team that has outgrown a shared spreadsheet — where "who owns this" and "what is overdue" have become questions someone has to ask in chat — but for whom a per-seat tool is not justified. The design constraint that follows is that the tool must be usable within minutes of first login, without configuration, by someone who has never used it.

---

## 3. Goals and non-goals

### 3.1 Goals

| ID | Goal | How it is measured |
|---|---|---|
| G1 | A new user reaches a usable board without configuration | Signup to first task created in under 3 minutes, no docs |
| G2 | Answer "what is late" without a query | Overdue count is on the dashboard at page load |
| G3 | Deploy on one PaaS account with a managed Postgres | Two services, ~6 environment variables, no infra work |
| G4 | Members cannot act outside their assignment | Enforced server-side; a crafted request is rejected |
| G5 | Schema evolves without data loss | Alembic migration per change, forward-only |

### 3.2 Non-goals

These were considered and deliberately excluded from v1.0. Each is recorded with the reason, so the decision can be revisited rather than re-litigated.

| Excluded | Reason |
|---|---|
| **Real-time collaboration** (WebSockets, live cursors, presence) | The target team coordinates over hours, not seconds. Polling on page load is sufficient and removes a persistent-connection tier from the deployment. |
| **File attachments** | Introduces object storage, upload limits, virus scanning, and a second backup surface. A link to Drive or Dropbox in the task description covers the actual need. |
| **Email or push notifications** | Requires a mail provider, deliverability handling, bounce processing, and per-user preferences. The dashboard is a pull-based substitute. Reconsider when a team reports missing due dates. |
| **Time tracking and billing** | A different product with different buyers. Adding it would pull the roadmap toward agency workflows. |
| **Gantt charts and dependencies** | Task dependency graphs imply scheduling logic, critical path, and a UI that does not fit the target team's planning horizon. |
| **Subtasks / nested hierarchy** | Doubles query complexity and permission checks for a structure the target team can express with two tasks. |
| **Custom workflow states** | `TODO / IN_PROGRESS / DONE` is fixed on purpose. Configurable states are the first step toward the Jira setup cost this product exists to avoid. |
| **Multi-tenancy / organizations** | Ethara is self-hosted; the deployment *is* the tenant boundary. Adding an org layer would add a foreign key to every table for no current user. |
| **SSO / OAuth** | Email and password is sufficient at this team size. SSO becomes relevant at the scale where per-seat pricing is also acceptable. |

---

## 4. Users

### 4.1 Admin

A team lead or founder. Creates projects, decides who is on them, and needs a portfolio view across everything. Logs in a few times a day, mostly to check status rather than to update it. Their failure mode is discovering a slipped deadline late.

**Needs:** create and structure projects · add and remove members · assign work · see every task in one view · filter to a project or a person.

### 4.2 Member

An individual contributor on one or more projects. Cares about their own queue and what is due. Logs in to change a status and leave.

**Needs:** see their assigned tasks · change status without asking permission · see due dates · not be presented with work that is not theirs.

### 4.3 Explicit scope note on the member view

The current implementation restricts a member to *only tasks assigned to them* — `list_tasks` filters non-admin callers by `Task.assigned_to == current_user.id`, so a member on a project cannot see the project's other tasks.

This is not the conventional choice. Most tools show the whole board to anyone on the project. It was chosen to keep the member view unambiguous — the list is a personal queue, not a board to be scanned — and it is the more conservative default, since widening visibility later is a non-breaking change while narrowing it is not.

It has a real cost: a member cannot see whether a blocking task is done, and cannot self-serve context about the project. **This is Open Question OQ-1** and should be validated with a real team before v1.0 hardens it.

---

## 5. Current state (as-built)

### 5.1 Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, SQLAlchemy ORM |
| Database | PostgreSQL, Alembic migrations |
| Auth | JWT (HS256) via `python-jose`, bcrypt password hashing |
| Frontend | React 18 (Vite), TailwindCSS, Zustand, Axios |
| Deploy | Railway *or* Render + Vercel — see D8 |

### 5.2 Data model

Four tables. Integer surrogate keys throughout.

**`users`** — `id`, `name`, `email` (unique, indexed), `password_hash`, `role` (enum `ADMIN`/`MEMBER`), `created_at`

**`projects`** — `id`, `name`, `description`, `owner_id` → `users.id` `ON DELETE CASCADE`, `created_at`

**`project_members`** — `id`, `user_id`, `project_id`; unique constraint on `(user_id, project_id)`, composite index on the same pair. A pure join table: membership is binary, with no per-project role.

**`tasks`** — `id`, `title`, `description`, `status` (enum, default `TODO`), `due_date` (nullable), `project_id` → `projects.id` `ON DELETE CASCADE`, `assigned_to` → `users.id` `ON DELETE SET NULL`, `created_at`. Composite indexes on `(project_id, status)` and `(assigned_to, due_date)` — the two query shapes the dashboard and the project view actually issue.

**Design note on `assigned_to`:** it is nullable with `SET NULL` on delete, which makes unassigned a first-class state and prevents a departing user from deleting the team's task history. `project_id` is deliberately not nullable — a task without a project has no meaning here.

### 5.3 API surface

| Method | Path | Access as implemented |
|---|---|---|
| POST | `/api/auth/signup` | Public |
| POST | `/api/auth/login` | Public |
| GET | `/api/users/me` | Authenticated |
| GET | `/api/users` | Authenticated — returns all users |
| GET | `/api/projects` | Admin: all · Member: own memberships |
| POST | `/api/projects` | Admin (global role) |
| PUT | `/api/projects/{id}` | Admin (global role) |
| DELETE | `/api/projects/{id}` | Admin (global role) |
| POST | `/api/projects/{id}/members` | Admin (global role) |
| DELETE | `/api/projects/{id}/members/{user_id}` | Admin (global role) |
| GET | `/api/projects/{id}/tasks` | Project access; members see only own tasks |
| POST | `/api/projects/{id}/tasks` | Project access; members may only self-assign |
| PUT | `/api/projects/{id}/tasks/{task_id}` | Admin, or the assignee |
| PATCH | `/api/projects/{id}/tasks/{task_id}/status` | Same as PUT — thin wrapper |
| DELETE | `/api/projects/{id}/tasks/{task_id}` | Admin, or the assignee |
| GET | `/api/dashboard?project_id=&user_id=` | Authenticated; member results scoped to memberships |
| GET | `/health` | Public |

---

## 6. Functional requirements

Requirements marked **[built]** exist and work. **[gap]** marks a requirement the current code does not satisfy — each maps to a defect in §8.

### 6.1 Authentication

| ID | Requirement | State |
|---|---|---|
| FR-1.1 | Signup accepts name, email, password; rejects a duplicate email with 409 | built |
| FR-1.2 | Passwords hashed with bcrypt and per-user salt; never stored or logged in plaintext | built |
| FR-1.3 | Password minimum 8 characters, maximum 128, enforced at the schema layer | built |
| FR-1.4 | Login returns a signed JWT and the user object; failure returns 401 without distinguishing unknown email from wrong password | built |
| FR-1.5 | Token carries the user id as `sub` and an `exp` claim; expiry is 24 hours | built |
| FR-1.6 | Every protected route rejects a missing, malformed, or expired token with 401 | built |
| FR-1.7 | **Role must not be settable by the signup caller** | **gap — D1** |
| FR-1.8 | The signing secret must have no usable default; the app must refuse to start in production without one | **gap — D2** |

### 6.2 Authorization

| ID | Requirement | State |
|---|---|---|
| FR-2.1 | Two roles: `ADMIN` and `MEMBER`, stored on the user record | built |
| FR-2.2 | Members may read only projects they are a member of | built |
| FR-2.3 | Members may update or delete only tasks assigned to them | built |
| FR-2.4 | Members may not assign a task to another user | built |
| FR-2.5 | All authorization is enforced server-side; the UI hides controls as a convenience only | built |
| FR-2.6 | **Project mutation must be restricted to admins with a relationship to that project** — currently any admin can edit or delete any project | **gap — D3** |
| FR-2.7 | **`GET /api/users` must not expose the full user directory to every member** | **gap — D4** |

### 6.3 Projects

| ID | Requirement | State |
|---|---|---|
| FR-3.1 | Admin creates a project with name (2–180 chars) and optional description | built |
| FR-3.2 | Creator is recorded as `owner_id` and auto-added as a member in the same transaction | built |
| FR-3.3 | Admin adds a member; a duplicate returns 409, an unknown user returns 404 | built |
| FR-3.4 | Admin removes a member; a non-membership returns 404 | built |
| FR-3.5 | Deleting a project cascades to its memberships and tasks | built |
| FR-3.6 | Removing a member must unassign that member's tasks in the project | **gap — D5** |

### 6.4 Tasks

| ID | Requirement | State |
|---|---|---|
| FR-4.1 | Task has title (2–180 chars), optional description, status, optional due date, optional assignee | built |
| FR-4.2 | Status is one of `TODO`, `IN_PROGRESS`, `DONE`; invalid values rejected with 422 | built |
| FR-4.3 | Status change available as a dedicated `PATCH` so the common action needs no full payload | built |
| FR-4.4 | Partial update semantics — `exclude_unset=True`, so omitted fields are untouched | built |
| FR-4.5 | A task is overdue when `due_date` is past and status is not `DONE` | built |
| FR-4.6 | Assignee may be cleared, leaving the task unassigned | built |

### 6.5 Dashboard

| ID | Requirement | State |
|---|---|---|
| FR-5.1 | Returns total task count, overdue count, and a per-status breakdown | built |
| FR-5.2 | Admin sees all tasks; member sees tasks in their projects | built |
| FR-5.3 | Optional filters by `project_id` and `user_id`, combinable | built |
| FR-5.4 | Status breakdown always includes all three keys, zero-filled, so the client needs no defaulting | built |
| FR-5.5 | Aggregate counts must be computed in SQL, and the task list must be paginated | **gap — D6** |

---

## 7. Key decisions

Each decision records what was chosen, what was rejected, and what it costs.

### D-A. JWT bearer tokens over server-side sessions

**Chosen** because it keeps the API stateless: no session store, no sticky sessions, and the backend can scale to more than one instance or restart without logging everyone out. On a free PaaS tier where containers sleep and restart, this matters more than it would on a persistent host.

**Rejected:** server-side sessions in Postgres or Redis. Redis is a third billable service; a session table adds a write and a read to every request.

**Cost accepted:** tokens cannot be revoked before expiry. A compromised token is valid for up to 24 hours, and a role change or an account deletion does not take effect until the token expires. Mitigation deferred to the backlog in §12.

### D-B. 24-hour token lifetime

**Chosen** to avoid re-login during a working day, since there is no refresh-token flow.

**Rejected:** a 15-minute access token with a refresh token. That is the correct design and roughly triples the auth surface — rotation, refresh storage, reuse detection.

**Cost accepted:** the exposure window in D-A is a full day rather than minutes. This is the weakest deliberate trade-off in the system and the first thing to revisit if Ethara is ever used with real client data.

### D-C. Two global roles, not per-project roles

**Chosen** because per-project roles multiply permission checks and require a role-management UI, for a team size where the distinction between "lead on project A, contributor on project B" is usually social rather than enforced.

**Rejected:** a `role` column on `project_members`, which is the more general design and would be a small migration.

**Cost accepted:** the model cannot express a project lead who is not a global admin. This is also the root of defect D3 — because `require_admin` checks only the global role, it grants authority over every project, which is a broader grant than the model intends. **The v1.0 fix is a per-project authorization check, not a new role.**

### D-D. Membership as a plain join table

**Chosen** for a unique constraint that makes double-add impossible at the database level rather than in application code, and a composite index that serves the "projects for this user" query directly.

**Cost accepted:** no membership metadata — no joined-at date, no invited-by. Adding it later is an additive migration.

### D-E. Project scoping in the task URL

Task routes are nested under `/api/projects/{project_id}/tasks`, and every handler calls `_ensure_project_access` before touching a task. The project check therefore cannot be forgotten, and a task id from another project 404s because every query filters on both `Task.id` and `Task.project_id`.

**Rejected:** flat `/api/tasks/{id}` with the project derived from the row, which is a shorter URL and one more place to forget the check.

### D-F. `create_all()` on startup alongside Alembic

**Chosen** so a fresh clone runs without a migration step — a real convenience during development.

**Cost accepted:** two sources of schema truth. `create_all` does not alter existing tables, so it silently does nothing when a migration is pending, and the app starts against a stale schema and fails at query time instead of boot time. **This must be removed before v1.0** — see D7.

### D-G. Deploy target

Both `railway.json` and `render.yaml` are committed, and the two guides disagree: `README.md` documents Railway for both services, `DEPLOYMENT_GUIDE.md` documents Render for the backend and Vercel for the frontend. The move away from Railway was driven by the frontend build experience on Vercel and the Render free Postgres tier. **The repository was never cleaned up afterward** — see D8.

---

## 8. Known defects

Ranked by severity. D1 through D4 block v1.0.

### D1 — Privilege escalation via signup *(critical, blocking)*

`UserCreate` declares `role: UserRole = UserRole.MEMBER`, so `role` is an accepted field of the signup request body. A caller who posts `{"name": "...", "email": "...", "password": "...", "role": "ADMIN"}` to the public `/api/auth/signup` endpoint receives an administrator account and a valid token. No authentication is required to reach it.

Combined with D3, this gives any anonymous visitor full read and write access to every project and task in the deployment.

**Fix:** remove `role` from `UserCreate`. Assign `UserRole.MEMBER` server-side unconditionally. Promotion becomes a separate admin-only endpoint, or a manual database operation for the first admin. Add a regression test that posts `role: ADMIN` to signup and asserts the created user is a member.

### D2 — Default signing secret *(critical, blocking)*

`config.py` sets `secret_key: str = "change-me-in-production"`. The application starts and issues valid tokens with this value. If `SECRET_KEY` is unset or misspelled in the deployment environment, everything works — and anyone who has read the repository can forge a token for any user id.

**Fix:** make `secret_key` a required setting with no default. Fail startup with an explicit error when `env == "production"` and the secret is absent or equal to any known placeholder.

### D3 — Global admin authority over every project *(high, blocking)*

`require_admin` checks only `current_user.role != UserRole.ADMIN`. It does not check ownership or membership. Any admin can therefore update, delete, or change the membership of any project, including projects they have no relationship to. `delete_project` cascades to all of that project's tasks.

**Fix:** add an authorization helper that requires admin **and** a relationship to the target project — ownership for destructive operations, membership for the rest. Apply it to `PUT /projects/{id}`, `DELETE /projects/{id}`, and both member endpoints.

### D4 — CORS permits all origins with credentials *(high, blocking)*

`main.py` configures `allow_origins=["*"]` together with `allow_credentials=True`. This combination is rejected by browsers as invalid, so the credentialed path fails in a way that is confusing to debug — and the `frontend_url` setting that exists in `config.py` for exactly this purpose is never read.

**Fix:** set `allow_origins=[settings.frontend_url]`, with a permissive list only when `env == "development"`.

### D5 — Member removal leaves task assignments intact *(medium)*

`remove_project_member` deletes the `ProjectMember` row and nothing else. Tasks assigned to that user keep pointing at them. The user can no longer read the project, so the task is assigned to someone who cannot see it, and it silently disappears from every view while still counting toward the project's totals.

**Fix:** in the same transaction, null the `assigned_to` of that user's tasks in that project. Decide and document whether the task should also be flagged for reassignment.

### D6 — Dashboard loads every task into memory *(medium)*

`get_dashboard` calls `query.all()`, then computes the overdue count and the status breakdown in a Python loop, and returns every task row in the response. There is no pagination and no limit. For an admin on a mature deployment this is the entire task table on every dashboard load.

**Fix:** compute counts with SQL aggregates (`COUNT`, `GROUP BY status`, and a filtered count for overdue). Paginate the task list with `limit`/`offset`, defaulting to 50.

### D7 — Dual schema management *(medium)*

Per D-F. `Base.metadata.create_all()` runs on every startup while Alembic also owns the schema.

**Fix:** remove the startup call. Document `alembic upgrade head` as a required deploy step, and add it to the start command.

### D8 — Deployment documentation contradicts itself *(low)*

Three inconsistencies: `README.md` says Railway while `DEPLOYMENT_GUIDE.md` says Render plus Vercel; both `railway.json` and `render.yaml` are committed; and the guide sets the health check to `/api/health` while `main.py` registers `/health` — a health check against the documented path returns 404 and the platform will report the service unhealthy.

**Fix:** pick one target, delete the other config, correct the health path, and reduce the second guide to a short note.

### D9 — Token stored in `localStorage` *(low, accepted for v1.0)*

`authStore.js` persists the token in `localStorage`, which is readable by any script on the origin, so an XSS flaw becomes full account takeover. The alternative — an httpOnly cookie — requires CSRF protection and a same-site strategy across two deploy domains. Accepted for v1.0 with the SPA's limited injection surface as the mitigating factor. Revisit if user-supplied HTML is ever rendered.

### D10 — Deprecated startup hook *(low)*

`@app.on_event("startup")` is deprecated in current FastAPI. Resolved for free by D7's removal; otherwise migrate to the `lifespan` context manager.

---

## 9. Edge cases

| Case | Behavior today | Required for v1.0 |
|---|---|---|
| Last admin deleted or demoted | Not guarded. The deployment can reach a state with no admin and no way to create one through the UI. | Block the operation when it would remove the final admin. |
| Concurrent edits to one task | Last write wins, silently. `exclude_unset` narrows but does not eliminate the overlap. | Accepted for v1.0 at this team size. Add an `updated_at` precondition check if a team reports lost edits. |
| Assigning a non-member to a task | Not validated. `assigned_to` accepts any user id, producing a task assigned to someone who cannot read the project. | Validate that the assignee is a member of the project; return 400. |
| Deleting a user with assigned tasks | Contradictory. The database says `ON DELETE SET NULL` on `tasks.assigned_to`, while the `User.assigned_tasks` relationship declares `cascade="all, delete"`. An ORM delete destroys the tasks; a SQL delete preserves them and nulls the assignee. | Remove the ORM cascade. `SET NULL` is the intended behavior — a departing user must not delete the team's history. |
| Task due date in the past at creation | Accepted, immediately overdue. | Correct — backfilling a missed task is legitimate. No change. |
| Database unreachable | Unhandled `SQLAlchemyError` surfaces as a 500 with a stack trace when `debug=true`. | Ensure `DEBUG=false` in production; add a handler returning a generic 503. |
| Expired token mid-session | API returns 401; the SPA has no global interceptor, so the failure surfaces as a broken page rather than a redirect. | Add an Axios response interceptor: on 401, clear the store and route to login. |
| Duplicate email signup | 409 with a clear message. | Correct. No change. |
| Member self-assigns a task in a project | Allowed — members may create tasks assigned to themselves. | Intentional. Documented here so it is not mistaken for a gap. |

---

## 10. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | Dashboard response time | p95 under 500 ms at 1,000 tasks — requires D6 |
| NFR-2 | Concurrent users | 50 without degradation; not a design target beyond that |
| NFR-3 | Password storage | bcrypt, per-user salt, cost factor at library default |
| NFR-4 | Transport | HTTPS enforced by the platform; no plaintext in production |
| NFR-5 | Schema changes | Alembic migration per change, forward-only, reviewed before deploy |
| NFR-6 | Deploy footprint | Two services plus one managed Postgres |
| NFR-7 | Browsers | Current Chrome, Firefox, Safari, Edge. No IE. |
| NFR-8 | Responsive layout | Usable at 375 px width; tables scroll rather than reflow |
| NFR-9 | Error responses | Correct status codes with a `detail` string; no stack traces in production |

---

## 11. Success metrics

| Metric | Target | Why this one |
|---|---|---|
| Signup → first task created | Under 3 minutes, unassisted | Directly tests G1. If setup needs explaining, the complexity goal failed. |
| Week-2 return rate | ≥60% of signups active in week two | A tracker used once is a tracker that lost to the spreadsheet. |
| Overdue ratio trend | Declining over 4 weeks of team use | The dashboard's whole purpose is surfacing lateness early enough to act. |
| Tasks updated per active user per week | ≥5 | Below this, people are updating status elsewhere and the data is stale. |
| Admin dashboard loads per week | ≥3 | Measures whether the portfolio view answers a real question. |

---

## 12. Release plan

### v1.0 — Security hardening *(blocking)*

D1, D2, D3, D4. Plus regression tests: signup cannot set a role; an unrelated admin cannot delete a project; a member cannot read another member's task; an expired token is rejected.

### v1.1 — Correctness

D5, D6, D7. The last-admin guard, assignee-membership validation, the ORM cascade contradiction, and the 401 interceptor.

### v1.2 — Cleanup

D8, D10. One deploy path, correct health check, one guide.

### Backlog *(not scheduled)*

Refresh tokens with short access-token lifetime (D-B) · per-project roles (D-C) · widened member visibility pending OQ-1 · task comments · full-text search across titles and descriptions · CSV export.

---

## 13. Open questions

| ID | Question | Owner | Needed by |
|---|---|---|---|
| OQ-1 | Should a member see the whole project board, or only their assigned tasks? §4.3 argues both ways; needs one real team's input. | Author | Before v1.1 |
| OQ-2 | Should removing a member unassign their tasks silently, or flag them for reassignment? Silent nulling loses the record of who was working on it. | Author | With D5 |
| OQ-3 | Is a first-admin bootstrap needed once D1 lands — a seed command, a `FIRST_ADMIN_EMAIL` variable, or manual promotion? | Author | With D1 |
| OQ-4 | Should the free-tier Postgres row ceiling be an enforced limit or a monitored one? | Author | Before first real deployment |
| OQ-5 | Repository attribution — `DEPLOYMENT_GUIDE.md` points at `Shreysharma1602/Project-Manager`. Confirm the canonical remote before this document is shared. | Author | Before external sharing |

---

## 14. Appendix — verification

Claims in this document were checked against the source at the stated version:

- Data model and cascade behavior — `backend/app/models.py`
- Validation bounds and the `role` field of D1 — `backend/app/schemas.py`
- Token construction and lifetime — `backend/app/security.py`
- Default secret of D2 — `backend/app/config.py`
- `require_admin` scope of D3 — `backend/app/deps.py`
- CORS configuration of D4 and the startup hook of D10 — `backend/app/main.py`
- Endpoint-level authorization — `backend/app/routers/*.py`
- Dashboard aggregation of D6 — `backend/app/routers/dashboard.py`
- Token persistence of D9 — `frontend/src/store/authStore.js`
- Deployment contradictions of D8 — `README.md`, `DEPLOYMENT_GUIDE.md`, `backend/railway.json`, `backend/render.yaml`
