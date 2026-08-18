# Ethara Project Management App
## Product Requirements Document

### Document control

| Field | Value |
|---|---|
| Version | 1.2 |
| Status | Approved for build. Blocked on setup steps before release |
| Documentation owner | Sugandh Sharma |
| Engineering owner | Rohit Sharma |
| Last updated | 18 August 2026 |
| Code | `main`, at the security hardening merge |
| Companion documents | `DEFECTS.md`, `README.md`, `DEPLOYMENT_GUIDE.md` |

### Revision history

| Version | What changed |
|---|---|
| 0.9 | First draft. Recorded the system as built and what release would need |
| 1.0 | Rewritten after the security work. Fifteen defects closed |
| 1.2 | OQ-6 answered and shipped: task access reads wide and writes narrow. D17 closed, AC-11 added |
| 1.1 | Split the defect log into `DEFECTS.md`. Added user flows, acceptance criteria, a permission matrix, dependencies and assumptions, and how each measure would actually be taken. Added OQ-6 after the matrix exposed an inconsistency |

### How to read this

Sections 1 to 7 are the product: what it is for, who uses it, what it must do. Sections 8 to 12 are the build: what exists, what it cost, what breaks. Sections 13 to 17 are release: what has to be true before real users see it.

If you have five minutes, read section 1, the permission matrix in section 7, and the launch checklist in section 15.

---

## 1. Summary

Ethara is a project and task tracker for small teams that you host yourself. A FastAPI backend with PostgreSQL, a React single page frontend, one managed database, running on a single hosting account.

It does five things: signup and login, two roles, projects with members, tasks with a status and a due date, and a dashboard that counts what is late. It deliberately does not do a sixth thing, and section 4.2 lists which sixth things and why.

The build is complete. A review found seventeen defects, all of which are closed and covered by tests. What remains before release is not code. It is four setup steps on the hosting account and one product decision. Section 15 lists them.

---

## 2. The problem

Teams of three to fifteen people need to know who is doing what, and what is late. The tools available to them miss for three reasons.

**The price does not fit the need.** Jira, Asana and Linear charge per person. A team of six pays for six seats to track perhaps forty tasks. That pricing makes sense in a company where the tool saves salary time. For a small team it is competing with a spreadsheet, and a spreadsheet is free.

**The setup costs more than the problem.** Jira can be shaped to fit almost anything, which is a real strength if somebody is paid to shape it. Without that person, sprints, epics, custom fields and permission schemes are all work you do before tracking a single task.

**The data sits with the vendor.** Some teams work under client terms that make a hosted tool awkward, and self hosting is usually only offered on the expensive plans.

Ethara is for the team that has outgrown a shared sheet, where "who owns this" and "what is late" have become questions somebody has to ask in chat, but where a per seat tool is not justified.

One rule follows from this and shapes every decision below: a new user must be able to use it within minutes, with no setup.

---

## 3. Who it is for

### 3.1 The admin

A team lead or a founder. Creates the projects, decides who is on them, and wants one view across everything. Logs in a few times a day, mostly to check rather than to update. The thing that hurts them is finding out too late that a date has slipped.

They need to create projects, add and remove people, hand out work, see the whole picture in one place, and narrow it to one project or one person.

### 3.2 The member

Somebody doing the work, on one or more projects. Cares about their own list and what is due this week. Logs in, moves a card, leaves.

They need to see their tasks, change a status without asking permission, see due dates, and not be shown work that is not theirs.

### 3.3 A deliberate choice about what a member sees

A member sees only tasks assigned to them, not the whole project board. In `list_tasks`, a caller who is not an admin has the list filtered by `Task.assigned_to == current_user.id`.

This is not what most tools do. It was chosen so the member view has one meaning: this is your list, not a board to scan. It is also the safer default, because opening visibility up later breaks nothing, while closing it down takes something away from people who had it.

The cost is real. A member cannot see whether the task blocking them is finished, and cannot get project context without asking. This is OQ-1, and one real team should settle it before it hardens.

---

## 4. Scope

### 4.1 In scope for v1.0

Accounts and login. Two roles. Projects with an owner and members. Tasks with a title, description, status, due date and assignee. A dashboard with totals, a late count and a breakdown by status. Filters by project and by person.

### 4.2 Out of scope, with reasons

Each of these was considered and left out. The reason is written down so the choice can be revisited later rather than argued again.

| Left out | Why |
|---|---|
| Live collaboration, presence, live cursors | This team coordinates over hours, not seconds. Fetching on page load is enough, and it keeps an always on connection layer out of the hosting setup |
| File attachments | Brings in object storage, size limits, virus scanning and a second thing to back up. A link in the task description covers the real need |
| Email or push alerts | Needs a mail provider, delivery handling, bounce handling and per person settings. The dashboard is the pull based substitute. Revisit when a team reports missing a due date |
| Time tracking and billing | A different product for a different buyer. It would pull the roadmap toward agency work |
| Gantt charts and dependencies | Dependencies imply scheduling logic and a critical path, which does not match how this team plans |
| Subtasks | Doubles the query work and the permission checks, for something the team can write as two tasks |
| Custom status names | The three states are fixed on purpose. Custom states are the first step back toward the setup cost this product exists to avoid |
| Organisations or multi tenancy | You host it yourself, so the install is already the boundary. An org layer would add a column to every table for nobody |
| Single sign on | Email and password is right at this size. SSO matters at the scale where per seat pricing is also acceptable |

### 4.3 Later, not scheduled

Short lived tokens with a refresh flow. Roles inside a project. Comments on tasks. Search across titles and descriptions. CSV export.

---

## 5. User flows

### 5.1 A team lead starts a project

1. Signs up. Gets a member account, because signup never grants admin.
2. Is promoted to admin. See OQ-3: this step has no path in the product yet.
3. Creates a project. Becomes its owner and its first member in one write.
4. Adds people to it.
5. Creates tasks and assigns them to members.
6. Opens the dashboard and sees the totals.

### 5.2 A member does their work

1. Signs up, or is added to a project by an admin.
2. Logs in and lands on the dashboard.
3. Sees their own tasks ordered by due date, with undated tasks last.
4. Opens a project and sees the tasks assigned to them.
5. Moves one to `IN_PROGRESS`, then later to `DONE`.

### 5.3 Somebody leaves the team

1. An admin removes them from the project.
2. Every task they held on that project becomes unassigned in the same write.
3. The tasks stay in the project and stay in the counts.
4. If the account itself is deleted, their tasks survive with no assignee.

This flow is why `assigned_to` is nullable and set to null on delete rather than cascading. Work history belongs to the team, not to whoever happened to hold it.

### 5.4 What a late task looks like

A task is late when its due date has passed and its status is not `DONE`. Nothing marks it. The dashboard counts it, and the count is on screen when the page loads, which is the whole of goal G2.

---

## 6. Requirements

### 6.1 Goals

| ID | Goal | How we check it |
|---|---|---|
| G1 | A new user reaches a working board with no setup | Signup to first task in under 3 minutes, unassisted |
| G2 | Answer "what is late" without running a query | The count is on the dashboard when it loads |
| G3 | Runs on one hosting account and one managed database | Two services, about six settings, no server work |
| G4 | A member cannot act outside their own work | Checked on the server. A hand built request is refused |
| G5 | The schema can change without losing data | One migration per change, forward only |

### 6.2 Accounts and login

| ID | Requirement | State |
|---|---|---|
| FR-1.1 | Signup takes a name, an email and a password. A repeat email returns 409 | Met |
| FR-1.2 | Passwords hashed with bcrypt and a per user salt, never stored or logged as text | Met |
| FR-1.3 | A password is between 8 and 128 characters | Met |
| FR-1.4 | Login returns a token and the user. A failure returns 401 without revealing whether the email or the password was wrong | Met |
| FR-1.5 | The token carries the user id and an expiry, and lasts 24 hours | Met |
| FR-1.6 | Every protected route refuses a missing, malformed or expired token with 401 | Met |
| FR-1.7 | The caller cannot choose their own role at signup | Met |
| FR-1.8 | The signing key has no default and the app will not start without a real one | Met |

### 6.3 Projects

| ID | Requirement | State |
|---|---|---|
| FR-2.1 | An admin creates a project with a name of 2 to 180 characters and an optional description | Met |
| FR-2.2 | The creator is recorded as owner and added as a member in the same transaction | Met |
| FR-2.3 | Adding a member twice returns 409. Adding an unknown user returns 404 | Met |
| FR-2.4 | Removing somebody who is not a member returns 404 | Met |
| FR-2.5 | Deleting a project removes its memberships and its tasks | Met |
| FR-2.6 | Removing a member frees the tasks they held on that project | Met |

### 6.4 Tasks

| ID | Requirement | State |
|---|---|---|
| FR-3.1 | A task has a title of 2 to 180 characters, an optional description, a status, an optional due date and an optional assignee | Met |
| FR-3.2 | Status is one of three values. Anything else returns 422 | Met |
| FR-3.3 | Changing status has its own short call, so moving a card does not require sending the whole task | Met |
| FR-3.4 | A partial update touches only the fields that were sent | Met |
| FR-3.5 | A task can be left with nobody on it | Met |
| FR-3.6 | A task can only be assigned to somebody on that project | Met |

### 6.5 Dashboard

| ID | Requirement | State |
|---|---|---|
| FR-4.1 | Returns a total, a late count and a count per status | Met |
| FR-4.2 | Can be filtered by project, by person, or both | Met |
| FR-4.3 | All three status keys are always present and zero filled, so the client needs no fallback | Met |
| FR-4.4 | Counts are computed by the database and the task list is paginated, 50 by default and 200 at most | Met |
| FR-4.5 | Tasks are ordered by due date, with undated tasks last | Met |

### 6.6 Acceptance criteria

| ID | Given | When | Then |
|---|---|---|---|
| AC-1 | I am not logged in | I post a signup with `role` set to `ADMIN` | The account is created as a member and the role field is ignored |
| AC-2 | I am an admin | I create a project | I am its owner and a member of it, both in one transaction |
| AC-3 | I am an admin who does not own a project | I try to rename or delete it | I get 403 and the project is unchanged |
| AC-4 | I am a member of a project | I list its tasks | I see only tasks assigned to me |
| AC-5 | I am a member | I create a task and assign it to somebody else | I get 403 |
| AC-6 | I am an admin | I assign a task to somebody not on the project | I get 400 |
| AC-7 | I am an admin | I remove a member who holds tasks | Their tasks on that project become unassigned and stay in the project |
| AC-8 | My token has expired | I call any protected route | I get 401, the stored login is cleared, and the browser returns to login |
| AC-9 | I am a member | I request the user list | I see only people who share a project with me |
| AC-10 | The signing key is missing or is a known placeholder | The service starts | Startup fails with a message naming the problem, rather than running insecurely |
| AC-11 | I am an admin with no tie to a project | I list its tasks, then try to change one | The list succeeds. The change returns 403 and the task is untouched |

AC-1, AC-3, AC-4, AC-6, AC-7, AC-8, AC-9, AC-10 and AC-11 have tests in `backend/tests/test_security.py`.

---

## 7. Permission matrix

Read down a column for what somebody in that position can do. "Off project" means an admin with no ownership of and no membership in the project being acted on.

| Action | Anonymous | Member, off | Member, on | Admin, off | Admin, member | Admin, owner |
|---|---|---|---|---|---|---|
| Sign up, log in | Yes | Yes | Yes | Yes | Yes | Yes |
| See own profile | No | Yes | Yes | Yes | Yes | Yes |
| List users | No | Shared projects only | Shared projects only | Everyone | Everyone | Everyone |
| List projects | No | Own only | Own only | All | All | All |
| Create a project | No | No | No | Yes | Yes | Yes |
| Rename a project | No | No | No | No | No | Yes |
| Delete a project | No | No | No | No | No | Yes |
| Add or remove a member | No | No | No | No | Yes | Yes |
| List tasks | No | No | Own tasks only | All tasks | All tasks | All tasks |
| Create a task | No | No | Self assigned only | No | Yes | Yes |
| Edit or delete a task | No | No | Own tasks only | No | Any task | Any task |
| Dashboard | No | Own projects | Own projects | Everything | Everything | Everything |

The admin column reads wide and writes narrow, which is the answer to OQ-6. An admin sees every task and the whole dashboard, because that install wide view is the point of section 3.1. Changing anything needs a real tie to the project, ownership or membership, because an admin who is not allowed to delete a project should not be able to empty it one task at a time. Before this, they could. See D17 in `DEFECTS.md`.

---

## 8. What is built

### 8.1 Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, SQLAlchemy |
| Database | PostgreSQL with Alembic migrations |
| Login | JWT signed with HS256 using PyJWT, passwords hashed with bcrypt |
| Frontend | React 18 on Vite, TailwindCSS, Zustand, Axios |
| Hosting | Render for the API, Vercel for the frontend |
| Python | 3.11.9, pinned in `runtime.txt` |

### 8.2 Data model

Four tables, each with an integer id.

**users**: `id`, `name`, `email` which is unique and indexed, `password_hash`, `role`, `created_at`.

**projects**: `id`, `name`, `description`, `owner_id` pointing at `users.id` with `ON DELETE CASCADE`, `created_at`.

**project_members**: `id`, `user_id`, `project_id`. A unique rule on the pair makes a double add impossible in the database rather than in application code, and an index on the same pair answers "which projects is this person on" directly. Membership is yes or no, with no role inside a project.

**tasks**: `id`, `title`, `description`, `status` defaulting to `TODO`, `due_date` which may be empty, `project_id` with `ON DELETE CASCADE`, `assigned_to` with `ON DELETE SET NULL`, `created_at`. Two combined indexes, on `(project_id, status)` and on `(assigned_to, due_date)`, which are the two query shapes the project page and the dashboard actually run.

`assigned_to` is nullable and set to null on delete because unassigned is a real state, and a departing person must not take the team's history with them. `project_id` is not nullable, because a task with no project means nothing here.

### 8.3 API

| Method | Path |
|---|---|
| POST | `/api/auth/signup`, `/api/auth/login` |
| GET | `/api/users/me`, `/api/users` |
| GET, POST | `/api/projects` |
| PUT, DELETE | `/api/projects/{id}` |
| POST, DELETE | `/api/projects/{id}/members` |
| GET, POST | `/api/projects/{id}/tasks` |
| PUT, PATCH, DELETE | `/api/projects/{id}/tasks/{task_id}` |
| GET | `/api/dashboard` |
| GET | `/health`, `/api/health` |

Task routes are nested under their project, and every handler checks project access before touching anything. The check therefore cannot be skipped by accident, and a task id from another project returns 404, because every query filters on both the task id and the project id.

---

## 9. Decisions and what they cost

### 9.1 A signed token instead of a server session

**Chosen** because the API then holds no state. No session store, no need for a request to reach the same server twice, and a restart does not log everybody out. On a free hosting plan where containers sleep and wake, that matters more than it would on a machine that stays up.

**Turned down:** sessions in Postgres or Redis. Redis is a third thing to pay for, and a session table adds a read and a write to every request.

**Cost:** a token cannot be cancelled before it expires. A stolen one works for up to a day, and a role change or a deleted account does not take effect until it runs out.

### 9.2 A token that lasts 24 hours

**Chosen** so nobody logs in twice in a working day, since there is no refresh flow.

**Turned down:** a fifteen minute token with a refresh token. That is the better design and it roughly triples the login code, because it brings in rotation, storage and reuse detection.

**Cost:** the window in 9.1 is a day rather than minutes. This is the weakest deliberate choice in the system and the first to revisit if Ethara ever holds real client data.

### 9.3 Two roles for the whole app, not roles inside a project

**Chosen** because per project roles multiply the checks and need a screen to manage them, at a size where "lead on this one, helper on that one" is usually understood rather than enforced.

**Turned down:** a role column on `project_members`, which is more flexible and would be a small migration.

**Cost:** the model cannot describe a project lead who is not also an app admin. This produced D3, and it is what OQ-6 is still arguing about. Every question of the form "which admin" traces back to this one choice.

### 9.4 Alembic owns the schema on its own

The app used to call `create_all()` at startup as well as having migrations. That was convenient for a fresh clone and it hid a real problem for months. See D7 and D16 in `DEFECTS.md`.

**Cost:** `alembic upgrade head` is now a required part of the start command. Forgetting it means a running API with no tables.

---

## 10. Edge cases

| Case | Behaviour today | Wanted |
|---|---|---|
| The last admin is deleted or demoted | Not guarded. The install can reach a state with no admin and no way to make one | Refuse the change when it would remove the final admin |
| Two people edit one task at once | Last write wins, quietly. Partial updates narrow the overlap without removing it | Acceptable at this size. Add a check on a last changed timestamp if anyone reports a lost edit |
| A task is assigned to somebody off the project | Refused with 400 | Correct |
| A user with tasks is deleted | Tasks stay and become unassigned | Correct |
| A task is created already past its due date | Accepted and immediately late | Correct. Recording a task you already missed is normal |
| The database is unreachable | An unhandled error becomes a 500 | Return a plain 503. Scheduled for v1.1 |
| A token expires mid session | The stored login is cleared and the browser returns to login | Correct |
| A duplicate email signs up | 409 with a clear message | Correct |
| A member creates a task for themselves | Allowed | Intended. Recorded here so it is not mistaken for a hole |

---

## 11. Other requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | Dashboard speed | Under 500 ms for 95 loads in 100, at 1,000 tasks |
| NFR-2 | People using it at once | 50 without slowing down. Not designed beyond that |
| NFR-3 | Password storage | bcrypt with a per user salt |
| NFR-4 | Traffic | HTTPS only in production |
| NFR-5 | Schema changes | One migration per change, forward only, reviewed before deploy |
| NFR-6 | Hosting size | Two services and one managed database |
| NFR-7 | Browsers | Current Chrome, Firefox, Safari and Edge |
| NFR-8 | Small screens | Usable at 375 px. Wide tables scroll rather than wrap |
| NFR-9 | Errors | Correct status codes with a short message, and no stack traces in production |

---

## 12. Dependencies and assumptions

### 12.1 What this depends on

| Dependency | Why it matters | What happens if it goes |
|---|---|---|
| Render free tier | Hosts the API and the database | The free database is reclaimed after a period of inactivity. This has already happened once and took the whole install with it |
| Vercel free tier | Hosts the frontend | The frontend goes offline. The API is unaffected |
| Managed PostgreSQL | All data | No fallback. There is no backup schedule, which is a gap |
| PyJWT, bcrypt, SQLAlchemy, FastAPI | Login and data access | All pinned to exact versions, so a surprise upgrade cannot break a deploy |

### 12.2 Assumptions

These are believed rather than proven. If one turns out false, the section it supports needs rewriting.

1. Teams are three to fifteen people. The permission model and the absence of paging on projects both assume this.
2. A team has one person willing to be the admin. The product cannot run without one.
3. Coordination happens over hours, not seconds. This is what rules out live collaboration.
4. Nobody except an admin needs to see a project's full board. This is OQ-1 and it is the least well supported assumption here.
5. The free hosting tier is enough for real use. Untested. NFR-1 and NFR-2 have never been measured.

---

## 13. How we will know it works

Every measure below needs instrumentation that does not exist yet. That gap is itself on the v1.1 list.

| Measure | Target | How it would be taken | Why this one |
|---|---|---|---|
| Signup to first task | Under 3 minutes, unassisted | Difference between `users.created_at` and that user's first `tasks.created_at` | This is G1. If it needs explaining, the setup goal failed |
| Still active in week two | 60 in 100 signups | Users with a task update in days 8 to 14 after signup | A tracker used once is a tracker that lost to the spreadsheet |
| Share of tasks late | Falling across four weeks | The dashboard already computes it. Record it weekly | The point of the dashboard is catching a slip early enough to act |
| Task updates per active person per week | At least 5 | Needs an updated timestamp on tasks, which the schema does not have | Below this, people track status somewhere else and this data is stale |
| Admin dashboard opens per week | At least 3 | Needs request logging, which does not exist | Shows whether the wide view answers a real question |

Two of the five cannot be measured without a schema change. Adding `updated_at` to `tasks` would also enable the concurrent edit check in section 10, so it earns its place twice.

---

## 14. Defects

The full record is in `DEFECTS.md`. Summary:

| Range | Subject | State |
|---|---|---|
| D0 | A production settings file committed to a public repository | Closed |
| D1 to D4 | Release blockers. Signup granted admin, the signing key had a working default, any admin could act on any project, CORS was misconfigured | Closed, with tests |
| D5 to D7 | Stranded task assignments, a dashboard that read the whole table into memory, two things owning the schema | Closed |
| D8 | Deploy documentation contradicts itself and describes a setup that is not in use | Partly closed |
| D9 | Tokens in browser local storage | Accepted for v1.0 |
| D10 to D14 | A deprecated hook, unpinned dependencies, an unguarded destructive migration, contradictory delete rules, no handling of an expired token | Closed |
| D15, D16 | A corrupted Python version pin, and migrations that had never once run on the server | Closed |
| D17 | The project scoping fix was applied to projects but not to tasks | Closed |

D16 is the one worth reading. Migrations failed on every deploy and nobody noticed, because `create_all()` was quietly building the tables by a route that could never apply a change to an existing table. Removing it did not break migrations. It revealed that they had never worked.

---

## 15. Release plan

### 15.1 Done

All seventeen defects closed. Ten regression tests covering sixteen cases, all passing. Merged to `main` and pushed.

### 15.2 Launch checklist

| # | Step | Owner | Blocking |
|---|---|---|---|
| 1 | Create a PostgreSQL instance and set `DATABASE_URL` | Engineering | Yes. The previous one was reclaimed and nothing runs without it |
| 2 | Set a fresh `SECRET_KEY` in the hosting environment | Engineering | Yes |
| 3 | Set the start command to run `alembic upgrade head` before the server | Engineering | Yes. Nothing else creates the tables |
| 4 | Confirm `/api/health` returns ok, then sign up a test user | Engineering | Yes |
| 5 | Decide OQ-3, how the first admin is created | Both | Yes. Signup can no longer produce one |
| 6 | ~~Decide OQ-6~~ Decided: read wide, write narrow. Shipped | Both | Done |
| 7 | Set repository visibility deliberately | Engineering | No |

Steps 1 to 4 are hosting setup and need no code. Steps 5 and 6 are product decisions.

### 15.3 v1.1

The last admin guard. A plain 503 when the database is unreachable. An `updated_at` column on tasks, which unlocks two of the five measures in section 13 and the concurrent edit check in section 10. Finish D8 by choosing one host and deleting the other config.

---

## 16. Open questions

| ID | Question | Owner | Needed by |
|---|---|---|---|
| OQ-1 | Should a member see the whole project board, or only their own tasks? Section 3.3 argues both sides, and assumption 4 rests on it | Both | Before v1.1 |
| OQ-2 | When a member is removed, should their tasks be freed quietly or flagged for somebody to pick up? Freeing them quietly loses the record of who was on it | Both | v1.1 |
| OQ-3 | How is the first admin created, now that signup always produces a member? A seed command, an environment variable, or a manual database change | Engineering | Before release |
| OQ-4 | Should the free tier row limit be enforced in the app, or just watched? | Engineering | Before real use |
| OQ-5 | `DEPLOYMENT_GUIDE.md` points at a different repository than the actual remote | Documentation | Before sharing |
| OQ-6 | ~~Is an admin a superuser for the whole install, or a lead over their own projects?~~ Answered: neither exactly. An admin reads everything and writes only where they have a tie. Shipped with two tests | Both | Closed |

OQ-6 is answered. The rule it set, read wide and write narrow, is the one to apply to any future permission question, because section 9.3 shows they all trace back to the same choice. OQ-3 is now the only release blocker left in this table.

---

## 17. Where these claims come from

Everything here was checked against the code rather than assumed.

| Claim | Source |
|---|---|
| Tables, indexes and delete rules | `backend/app/models.py` |
| Field limits and signup behaviour | `backend/app/schemas.py`, `backend/app/routers/auth.py` |
| Token construction and expiry | `backend/app/security.py` |
| Startup refusal on a placeholder key | `backend/app/config.py` |
| The permission matrix in section 7 | `backend/app/deps.py`, `backend/app/routers/` |
| Dashboard counts and paging | `backend/app/routers/dashboard.py` |
| Expired token handling | `frontend/src/api/client.js` |
| Migration behaviour | `backend/alembic/versions/0001_initial.py`, `backend/alembic.ini` |
| Acceptance criteria marked as tested | `backend/tests/test_security.py`, 14 passing |
