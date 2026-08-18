# Ethara Project Management App
## Product Requirements Document

| Field | Value |
|---|---|
| Status | Updated after the security fix branch |
| Version | 1.0 |
| Owner | Sugandh Sharma |
| Last updated | 18 August 2026 |
| Branch | `fix/security-hardening` |
| Related files | `README.md`, `DEPLOYMENT_GUIDE.md`, `backend/tests/test_security.py` |

---

## 1. Summary

Ethara is a project and task tracker for small teams. You host it yourself. The backend is FastAPI with PostgreSQL. The frontend is a React single page app. It runs on one hosting account plus one managed database.

The app handles signup and login, two roles, projects with members, tasks with a status and a due date, and a dashboard that counts what is late.

When this document was first written, the app worked but was not safe to put in front of users. A review of the code found four holes that let an outsider take over the whole deployment. Those are now fixed and covered by tests. Section 8 lists every problem found, what was done about it, and what is still open.

One item is still open and only the owner can close it. A file with the production database password was committed to a public GitHub repo. The password has to be changed in the hosting dashboard. No code change can do that.

---

## 2. The problem

Teams of three to fifteen people need to know who is doing what, and what is late. The usual tools miss for three reasons.

**Price does not fit.** Jira, Asana and Linear charge per person. A team of six pays for six seats to track forty tasks. That pricing suits a company where the tool saves salary time. For a small team it is replacing a spreadsheet.

**Too much setup.** Jira can be shaped to fit anything, which is useful if someone is paid to shape it. Without that person, sprints, epics, custom fields and permission schemes are work you do before you track a single task.

**No control of the data.** With a hosted tool, the vendor holds the data. Some teams work under client terms that make this hard. Self hosting is often only offered on the expensive plans.

Ethara is for the team that has outgrown a shared sheet, where "who owns this" and "what is late" have become questions people ask in chat. The rule that follows from this: a new user must be able to use it within minutes, with no setup.

---

## 3. Goals and non goals

### 3.1 Goals

| ID | Goal | How we check it |
|---|---|---|
| G1 | A new user gets to a working board with no setup | Signup to first task in under 3 minutes, no help |
| G2 | Answer "what is late" without running a query | The overdue count is on the dashboard when it loads |
| G3 | Runs on one hosting account and one managed database | Two services, about six settings, no server work |
| G4 | A member cannot act outside their own work | Checked on the server. A hand built request is refused |
| G5 | The schema can change without losing data | One Alembic migration per change, forward only |

### 3.2 Non goals

These were looked at and left out of v1.0. The reason is written down so the choice can be revisited later instead of argued again.

| Left out | Why |
|---|---|
| Live collaboration, presence, live cursors | This team works over hours, not seconds. Loading fresh data on page load is enough, and it keeps a always on connection layer out of the hosting setup. |
| File attachments | Brings in file storage, size limits, virus scanning and a second thing to back up. A link to Drive or Dropbox in the task description covers the real need. |
| Email or push alerts | Needs a mail provider, delivery handling, bounce handling and per person settings. The dashboard covers it for now. Look again if a team says they missed a due date. |
| Time tracking and billing | A different product for a different buyer. Adding it would pull the roadmap toward agency work. |
| Gantt charts and task dependencies | Dependencies mean scheduling logic and a critical path. That does not match how this team plans. |
| Subtasks | Doubles the query work and the permission checks, for something the team can write as two tasks. |
| Custom status names | `TODO`, `IN_PROGRESS` and `DONE` are fixed on purpose. Custom states are the first step toward the setup cost this product exists to avoid. |
| Organisations or multi tenant support | You host it yourself, so the install is already the boundary. An org layer would add a column to every table for nobody. |
| Single sign on | Email and password is fine at this size. SSO matters at the scale where paying per seat is also fine. |

---

## 4. Who uses it

### 4.1 Admin

A team lead or founder. Creates projects, picks who is on them, and wants one view across everything. Logs in a few times a day, mostly to check rather than to update. The thing that hurts them is finding out too late that a date slipped.

They need to: create projects, add and remove people, hand out work, see every task in one place, and filter by project or by person.

### 4.2 Member

Someone doing the work, on one or more projects. Cares about their own list and what is due. Logs in, changes a status, leaves.

They need to: see their tasks, change a status without asking, see due dates, and not be shown work that is not theirs.

### 4.3 A note on what a member can see

Right now a member only sees tasks assigned to them. In `list_tasks`, a caller who is not an admin gets the list filtered by `Task.assigned_to == current_user.id`. So a member on a project cannot see the other tasks on that project.

Most tools do the opposite and show the whole board to anyone on the project. This was chosen so the member view has one meaning: it is your list, not a board to scan. It is also the safer default, because opening it up later breaks nothing, while closing it down later would.

It has a real cost. A member cannot see whether the task blocking them is done, and cannot look up project context on their own. This is open question OQ-1. It should be checked with a real team before it hardens.

---

## 5. What is built

### 5.1 Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, SQLAlchemy |
| Database | PostgreSQL, Alembic migrations |
| Login | JWT signed with HS256 using PyJWT, passwords hashed with bcrypt |
| Frontend | React 18 on Vite, TailwindCSS, Zustand, Axios |
| Hosting | Render for the API, Vercel for the frontend. See D8 |

### 5.2 Data model

Four tables, each with an integer id.

**users**: `id`, `name`, `email` (unique, indexed), `password_hash`, `role` (`ADMIN` or `MEMBER`), `created_at`.

**projects**: `id`, `name`, `description`, `owner_id` pointing at `users.id` with `ON DELETE CASCADE`, `created_at`.

**project_members**: `id`, `user_id`, `project_id`. There is a unique rule on the pair, so the same person cannot be added twice, and an index on the same pair. Membership is yes or no. There is no role inside a project.

**tasks**: `id`, `title`, `description`, `status` (defaults to `TODO`), `due_date` (can be empty), `project_id` with `ON DELETE CASCADE`, `assigned_to` with `ON DELETE SET NULL`, `created_at`. There are two combined indexes, on `(project_id, status)` and on `(assigned_to, due_date)`. Those are the two shapes of query the project page and the dashboard actually run.

Why `assigned_to` can be empty and is set to null on delete: unassigned is a real state, and when someone leaves the team their tasks must stay. `project_id` cannot be empty, because a task with no project means nothing here.

### 5.3 API

| Method | Path | Who can call it |
|---|---|---|
| POST | `/api/auth/signup` | Anyone. Always creates a member |
| POST | `/api/auth/login` | Anyone |
| GET | `/api/users/me` | Any logged in user |
| GET | `/api/users` | Admin sees all. A member sees only people on their projects |
| GET | `/api/projects` | Admin sees all. A member sees their own |
| POST | `/api/projects` | Admin |
| PUT | `/api/projects/{id}` | Admin who owns the project |
| DELETE | `/api/projects/{id}` | Admin who owns the project |
| POST | `/api/projects/{id}/members` | Admin on that project |
| DELETE | `/api/projects/{id}/members/{user_id}` | Admin on that project |
| GET | `/api/projects/{id}/tasks` | Anyone on the project. A member sees only their own tasks |
| POST | `/api/projects/{id}/tasks` | Anyone on the project. A member can only assign to themselves |
| PUT | `/api/projects/{id}/tasks/{task_id}` | Admin, or the person it is assigned to |
| PATCH | `/api/projects/{id}/tasks/{task_id}/status` | Same as PUT. A short way to move a card |
| DELETE | `/api/projects/{id}/tasks/{task_id}` | Admin, or the person it is assigned to |
| GET | `/api/dashboard` | Any logged in user. A member only sees their projects |
| GET | `/health` and `/api/health` | Anyone |

---

## 6. Requirements

"Done" means it works today. "Open" means it does not, and points at the item in section 8.

### 6.1 Login

| ID | Requirement | State |
|---|---|---|
| FR-1.1 | Signup takes a name, an email and a password. A repeat email gets a 409 | Done |
| FR-1.2 | Passwords are hashed with bcrypt and a per user salt. Never stored or logged as text | Done |
| FR-1.3 | Password must be 8 to 128 characters | Done |
| FR-1.4 | Login returns a token and the user. A failure returns 401 and does not say whether the email or the password was wrong | Done |
| FR-1.5 | The token holds the user id and an expiry time. It lasts 24 hours | Done |
| FR-1.6 | Every protected route refuses a missing, broken or expired token with a 401 | Done |
| FR-1.7 | The caller cannot pick their own role at signup | Done. Was D1 |
| FR-1.8 | The signing key has no default and the app will not start without a real one | Done. Was D2 |

### 6.2 Permissions

| ID | Requirement | State |
|---|---|---|
| FR-2.1 | Two roles, `ADMIN` and `MEMBER`, stored on the user | Done |
| FR-2.2 | A member only sees projects they are on | Done |
| FR-2.3 | A member can only change or delete tasks assigned to them | Done |
| FR-2.4 | A member cannot hand a task to someone else | Done |
| FR-2.5 | Every check runs on the server. Hiding a button in the UI is a courtesy, not a control | Done |
| FR-2.6 | Changing or deleting a project needs an admin who owns it | Done. Was D3 |
| FR-2.7 | The user list is not handed to every member | Done. Was D4 |

### 6.3 Projects

| ID | Requirement | State |
|---|---|---|
| FR-3.1 | An admin creates a project with a name and an optional description | Done |
| FR-3.2 | The creator is saved as the owner and added as a member in the same write | Done |
| FR-3.3 | An admin adds a member. A repeat gets 409, an unknown user gets 404 | Done |
| FR-3.4 | An admin removes a member. Removing someone who is not there gets 404 | Done |
| FR-3.5 | Deleting a project also deletes its members and tasks | Done |
| FR-3.6 | Removing a member frees the tasks they held on that project | Done. Was D5 |

### 6.4 Tasks

| ID | Requirement | State |
|---|---|---|
| FR-4.1 | A task has a title, an optional description, a status, an optional due date and an optional owner | Done |
| FR-4.2 | Status is one of the three values. Anything else gets a 422 | Done |
| FR-4.3 | Moving a card has its own short call, so the client does not have to send the whole task | Done |
| FR-4.4 | A partial update only touches the fields that were sent | Done |
| FR-4.5 | A task is late when the due date has passed and it is not done | Done |
| FR-4.6 | A task can be left with nobody on it | Done |
| FR-4.7 | A task can only be given to someone on that project | Done |

### 6.5 Dashboard

| ID | Requirement | State |
|---|---|---|
| FR-5.1 | Returns a total, a late count, and a count per status | Done |
| FR-5.2 | An admin sees everything. A member sees their projects | Done |
| FR-5.3 | Can be filtered by project, by person, or both | Done |
| FR-5.4 | All three status keys are always present, set to zero if empty, so the client needs no fallback | Done |
| FR-5.5 | The counts are worked out by the database, and the task list comes back one page at a time | Done. Was D6 |

---

## 7. Choices and what they cost

Each one says what was picked, what was turned down, and what it costs.

### 7.1 A signed token instead of a server session

**Picked** because the API then holds no state. There is no session store, requests do not have to land on the same server, and a restart does not log everyone out. On a free hosting plan where containers sleep and wake, this matters.

**Turned down:** sessions kept in Postgres or Redis. Redis is a third thing to pay for. A session table adds a read and a write to every single request.

**Cost:** a token cannot be cancelled before it expires. If one is stolen it works for up to a day, and a role change or a deleted account does not take effect until it runs out. This is on the backlog, not in v1.0.

### 7.2 A token that lasts 24 hours

**Picked** so nobody has to log in again during a working day, since there is no refresh flow.

**Turned down:** a short token of about 15 minutes plus a refresh token. That is the better design and it roughly triples the login code, because it brings in rotation, storing the refresh token, and spotting reuse.

**Cost:** the window in 7.1 is a full day instead of a few minutes. This is the weakest choice in the app on purpose, and the first one to revisit if Ethara ever holds real client data.

### 7.3 Two roles for the whole app, not per project

**Picked** because roles inside each project multiply the checks and need a screen to manage them, at a team size where "lead on this one, helper on that one" is usually just understood rather than enforced.

**Turned down:** a role column on `project_members`. That is the more flexible design and would be a small migration.

**Cost:** the model cannot describe a project lead who is not also an app admin. This is also what caused D3. Because the old check only looked at the app wide role, it handed authority over every project. The fix was a per project check, not a new role.

### 7.4 Membership as a plain join table

**Picked** so the database itself refuses a duplicate member, instead of the app trying to remember to check. The combined index also answers "which projects is this person on" directly.

**Cost:** no extra information about the membership, such as when they joined or who added them. That can be added later without touching anything else.

### 7.5 The project id lives in the task URL

Task routes sit under `/api/projects/{project_id}/tasks`, and every handler calls `_ensure_project_access` before it touches anything. So the project check cannot be skipped by accident, and a task id from another project returns 404, because every query filters on both the task id and the project id.

**Turned down:** a flat `/api/tasks/{id}` with the project looked up from the row. Shorter URL, and one more place to forget the check.

### 7.6 Alembic owns the schema

The app used to call `create_all()` at startup as well as having migrations. That was handy for a fresh clone and it caused a real problem, described in D7. Alembic now owns the schema on its own, and `alembic upgrade head` is a required step before the API starts.

### 7.7 Where it is hosted

Both a Railway config and a Render config are in the repo, and the two guides disagree. `README.md` describes Railway. `DEPLOYMENT_GUIDE.md` describes Render for the API and Vercel for the frontend. The move happened for the Vercel build experience and the free Render database. The old files were never cleaned up. See D8.

---

## 8. Problems found, and what was done

Ordered by how bad they were. D1 to D4 were release blockers. All the code items below are fixed on `fix/security-hardening` and covered by `backend/tests/test_security.py`, which has seven tests that fail on the old code.

### D0. The production database password is in a public repo. Still open

`backend/.env.production` was committed in the first commit and pushed to the project's public GitHub repository. It holds a Render `DATABASE_URL` with a username and a password.

The cause is that `.gitignore` covered `.env` and `.env.local` but not `.env.production`. So the local file stayed private and the production one went public.

The host in the URL is Render's internal name, which cannot be reached from outside their network. That helps, but not much. The same username and password work on the external address, and the external address is the internal name plus the region plus `render.com`. There are only a handful of regions to try. Treat the password as public.

**Done in code:** both `.env.production` files are no longer tracked, and `.gitignore` now covers every `.env` variant while keeping the example files.

**Still to do, and only the owner can do it:**

1. Change the database password in the Render dashboard, or delete the database if it holds nothing worth keeping. This is the step that actually closes the hole.
2. Make the repo private, or decide to keep it public now the file is gone.
3. Check that Render has a real `SECRET_KEY` set. The value in the committed file started with `your-`, which is a placeholder. If that is what production is running on, anyone can forge a login for any user.
4. Decide whether to rewrite the git history. Once the password is changed the old value is worthless, so this is tidying rather than a rescue, and it rewrites a public history.

### D1. Anyone could sign up as an admin. Fixed

`UserCreate` had a `role` field, so `role` was part of the signup request. Sending `{"role": "ADMIN"}` to the open signup route returned an admin account and a working token, with no login needed. Together with D3, that gave a stranger full control of every project and task.

**Fix:** `role` is gone from the signup model, and the route always creates a member. Test: `test_signup_cannot_make_an_admin`.

### D2. The signing key had a working default. Fixed

`config.py` set `secret_key` to `"change-me-in-production"`. The app started and issued real tokens with it. If the setting was missing or misspelled on the server, everything looked fine, and anybody who read the repo could sign a token for any user.

**Fix:** the key is now required. The app refuses to start if it is missing, if it matches a known placeholder, or if it is under 32 characters in production. Test: `test_placeholder_secret_is_refused`.

### D3. Any admin could delete any project. Fixed

The old check only asked whether the role was `ADMIN`. It never asked whether this admin had anything to do with this project. So any admin could rename, delete, or change the membership of any project, and deleting one takes all its tasks with it.

**Fix:** a new `require_project_admin` check. It needs an admin who owns the project, or is a member of it. Renaming and deleting need ownership. Test: `test_admin_cannot_touch_a_project_they_do_not_own`.

### D4. CORS allowed every origin with credentials. Fixed

The API sent `allow_origins=["*"]` together with `allow_credentials=True`. Browsers reject that pair, so the credentialed path failed in a way that is hard to debug, and the `frontend_url` setting that existed for this was never read.

**Fix:** allowed origins now come from `FRONTEND_URL`, with localhost added outside production.

### D5. Removing a member left their tasks stranded. Fixed

Removing someone deleted the membership row and nothing else. Their tasks still pointed at them. They could no longer open the project, so the task sat assigned to somebody who could not see it. It vanished from every view while still counting toward the project totals.

**Fix:** those tasks are set back to unassigned in the same write. Test: `test_removing_a_member_frees_their_tasks`.

### D6. The dashboard read every task into memory. Fixed

The old code fetched every task the caller could see, then counted the late ones and the statuses in a Python loop, and returned every row. No page size, no limit. For an admin on a busy install that was the whole task table on every load.

**Fix:** the counts are SQL aggregates now, and the task list is paged, 50 by default and 200 at most.

### D7. Two things owned the schema. Fixed

`create_all()` ran at every startup while Alembic also owned the schema. The migration is raw SQL and every statement says `IF NOT EXISTS`, which made this worse than untidy. `create_all` built the tables first, then `alembic upgrade head` did nothing and marked the migration as applied. Alembic then believed it had built a database it had never touched, and every later migration would run against a schema it did not know.

**Fix:** the startup call is gone. Alembic owns the schema and `alembic upgrade head` runs before the API starts.

### D8. The deploy guides contradict each other. Partly fixed

Three things disagreed. `README.md` said Railway while `DEPLOYMENT_GUIDE.md` said Render and Vercel. Both config files were committed. The guide set the health check to `/api/health` while the code only had `/health`, so the platform would call a URL that returns 404 and mark the service unhealthy.

**Fix so far:** the API now answers on both `/health` and `/api/health`. Still to do: pick one host, delete the other config, and cut the second guide down to a short note.

### D9. Tokens are kept in browser local storage. Accepted for now

The token sits in `localStorage`, which any script on the page can read. So a script injection bug would become a full account takeover. The alternative, an httpOnly cookie, needs CSRF protection and a cross site cookie policy across two different domains. Left as is for v1.0, because the app does not render any user supplied HTML. Revisit if that changes.

### D10. Old startup hook. Fixed

`@app.on_event("startup")` is deprecated. It went away with D7.

### D11. Nothing was pinned. Fixed

Every line in `requirements.txt` was a `>=` with no upper limit and no lock file, so two deploys a month apart could install different versions. The one that mattered was the login library. `python-jose` is not maintained and has known advisories about algorithm confusion and a token that expands to exhaust memory.

**Fix:** moved to PyJWT and pinned every version.

### D12. The migration could drop every table. Fixed

`downgrade()` dropped all four tables with no guard. One command in the wrong shell and the data is gone. It now refuses to run unless `ALLOW_DESTRUCTIVE_DOWNGRADE=1` is set.

### D13. Delete rules disagreed with each other. Fixed

The column said `ON DELETE SET NULL` on `tasks.assigned_to`, while the ORM relationship said `cascade="all, delete"`. So deleting a user through the ORM destroyed their tasks, and deleting the same user in SQL kept them. The ORM cascade is gone. A person leaving must not take the team's history with them.

### D14. An expired token left a broken page. Fixed

The router only checked that a token existed, not that it still worked. So an expired token rendered the page and then every call failed with a 401 and no redirect. There is now a response handler that clears the stored login and sends the user to the login page.

---

## 9. Edge cases

| Case | What happens now | What should happen |
|---|---|---|
| The last admin is deleted or demoted | Not guarded. The install can end up with no admin and no way to make one from the UI | Refuse the change when it would remove the final admin |
| Two people edit the same task at once | The last write wins, quietly. Partial updates narrow the overlap but do not remove it | Fine for this team size. Add a check on a last changed timestamp if anyone reports losing an edit |
| A task is given to someone not on the project | Refused with a 400 | Fixed |
| A user with tasks is deleted | Their tasks stay and go back to unassigned | Fixed |
| A task is created with a due date in the past | Accepted and immediately late | Correct. Writing down a task you already missed is normal |
| The database is unreachable | An unhandled error becomes a 500, and with debug on it shows a stack trace | Keep `DEBUG=false` in production. Add a handler that returns a plain 503 |
| The token expires while someone is working | They are sent back to the login page | Fixed |
| Someone signs up with an email already in use | 409 with a clear message | Correct |
| A member creates a task for themselves | Allowed | On purpose. Written here so it is not mistaken for a hole |

---

## 10. Other requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | Dashboard speed | Under 500 ms for 95 out of 100 loads at 1,000 tasks |
| NFR-2 | People using it at once | 50 without slowing down. Not designed past that |
| NFR-3 | Password storage | bcrypt with a per user salt |
| NFR-4 | Traffic | HTTPS only in production |
| NFR-5 | Schema changes | One migration per change, forward only, reviewed before deploy |
| NFR-6 | Hosting size | Two services and one managed database |
| NFR-7 | Browsers | Current Chrome, Firefox, Safari and Edge |
| NFR-8 | Small screens | Usable at 375 px wide. Wide tables scroll rather than wrap |
| NFR-9 | Errors | Correct status codes with a short message. No stack traces in production |

---

## 11. How we know it works

| Measure | Target | Why this one |
|---|---|---|
| Signup to first task | Under 3 minutes with no help | This is G1. If it needs explaining, the setup goal failed |
| Still using it in week two | 60 out of 100 signups | A tracker used once is a tracker that lost to the spreadsheet |
| Share of tasks that are late | Falling over four weeks of real use | The whole point of the dashboard is catching a slip early enough to act |
| Task updates per person per week | At least 5 | Below that, people are tracking status somewhere else and this data is stale |
| Admin dashboard opens per week | At least 3 | Shows whether the one big view answers a real question |

---

## 12. Plan

**v1.0, done on this branch.** D0 code side, D1, D2, D3, D4, D5, D6, D7, D10, D11, D12, D13, D14, plus seven tests.

**Before v1.0 ships, owner action.** Change the database password. Check the production signing key. Decide on repo visibility.

**v1.1.** The last admin guard. A plain 503 when the database is down. Finish D8 by picking one host and deleting the other config.

**Backlog, not scheduled.** Short tokens with a refresh flow (7.2). Roles inside a project (7.3). Opening up what a member can see, once OQ-1 is answered. Comments on tasks. Search across titles and descriptions. CSV export.

---

## 13. Open questions

| ID | Question | Owner | Needed by |
|---|---|---|---|
| OQ-1 | Should a member see the whole project board, or only their own tasks? Section 4.3 argues both sides. One real team should decide it | Owner | Before v1.1 |
| OQ-2 | When a member is removed, should their tasks be freed quietly, or flagged so somebody picks them up? Freeing them quietly loses the record of who was on it | Owner | v1.1 |
| OQ-3 | Now that signup always makes a member, how is the first admin created? A seed command, a setting, or a manual database change | Owner | Before the next deploy |
| OQ-4 | Should the free database row limit be enforced in the app, or just watched? | Owner | Before real use |
| OQ-5 | `DEPLOYMENT_GUIDE.md` points at a different repository than the actual remote. Fix the reference before sharing this document | Owner | Before sharing |

---

## 14. Where these claims come from

Everything in this document was checked against the code, not assumed.

- Tables and delete rules: `backend/app/models.py`
- Field limits and the signup role of D1: `backend/app/schemas.py`
- Token building and expiry: `backend/app/security.py`
- The signing key of D2: `backend/app/config.py`
- The permission checks of D3: `backend/app/deps.py`
- CORS and the startup hook: `backend/app/main.py`
- Route by route permissions: `backend/app/routers/`
- The dashboard counts of D6: `backend/app/routers/dashboard.py`
- Token storage of D9 and the 401 handling of D14: `frontend/src/api/client.js`
- The migration and its downgrade: `backend/alembic/versions/0001_initial.py`
- The committed password of D0: `git log --all -- backend/.env.production`
- Tests: `backend/tests/test_security.py`, 14 passing
