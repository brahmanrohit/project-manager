# Ethara Defect Log

| Field | Value |
|---|---|
| Owner | Sugandh Sharma (documentation) |
| Engineering | Rohit Sharma |
| Last updated | 18 August 2026 |
| Companion document | `PRD.md` |
| Tests | `backend/tests/test_security.py` |

This is the full record of every defect found during the review of the Ethara
codebase, what caused it, and what was done. The PRD summarises this list in
one table and points here for detail.

Items are numbered in the order they were found, not by severity. D0 to D4
were release blockers. D15 and D16 were found by failing deploys rather than
by reading code, and D17 was found while building the permission matrix for
the PRD.

---

### D0. A production settings file was committed to a public repo. Closed

`backend/.env.production` was committed in the first commit and pushed to the project's public GitHub repository. It held a `DATABASE_URL` with a username and a password.

The cause is that `.gitignore` covered `.env` and `.env.local` but not `.env.production`. So the local file stayed private and the production one went public.

**Why it is closed.** The database it pointed at was a free tier instance that the host reclaimed after a period of inactivity. It no longer exists, so the exposed connection string opens nothing. The signing key in the same file was a placeholder that was never used in production; the running service had a real random key set as an environment variable instead.

This was closed by the free tier expiring rather than by anyone acting on it, which is luck, not process.

**Done in code:** both `.env.production` files are no longer tracked, and `.gitignore` now covers every `.env` variant while keeping the example files.

**Still worth doing:**

1. Rewrite the git history to drop the two files, or start the remote fresh. Optional now that the values are dead, but it stops the next person who reads the repo from thinking they found something live.
2. Keep every real secret in the host's environment settings and never in a file the repository can see. That is the habit that would have prevented this.

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

There is a fourth. `render.yaml` describes a web service and a `ethara-db` database, and sets a start command that runs migrations. None of it is used, because the live service was created by hand in the dashboard rather than from that file. So the repository holds a deploy description that looks authoritative and controls nothing. Two later problems, D15 and D16, both came from this gap.

**Fix so far:** the API now answers on both `/health` and `/api/health`. Still to do: pick one host, delete the other config, and either adopt `render.yaml` properly or delete it so nobody trusts it.

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

### D15. The Python version pin was silently ignored. Fixed

`backend/runtime.txt` is supposed to hold one line naming the Python version. It held two:

```
python-3.11.9
git commit -m "Configure production database and Python version"
```

A shell command had been pasted into the file. The host could not parse it, ignored the file, and fell back to its own newest default, so the service ran on Python 3.14 while every config file in the repository said 3.11.9.

Nothing broke because of it in the end, but it is the kind of drift that produces a bug that cannot be reproduced locally. The versions pinned in D11 were chosen against 3.11.

**Fix:** the file now holds the single line it should.

### D16. Migrations had never run on the server. Fixed

`alembic upgrade head` failed with `ModuleNotFoundError: No module named 'app'`. The cause is that `alembic/env.py` imports `app.config`, but `alembic.ini` was missing `prepend_sys_path`, the setting whose whole job is putting the project on the import path. Run from the console script, nothing added the `backend` directory, so the import failed before a single migration was read.

The reason nobody noticed is D7. While `create_all()` ran at startup, the tables appeared anyway and the deploy looked healthy. Migrations were dead the whole time and the app was quietly building its schema by a route that could never apply a change to an existing table.

Taking `create_all()` out did not cause this. It revealed it.

**Fix:** `prepend_sys_path = .` added to `alembic.ini`. Checked by running the migration until it reached real SQL.

### D17. The project scoping fix was incomplete. Open

D3 stopped an admin acting on a project they have nothing to do with. That fix
was applied to `projects.py` only. `tasks.py` still carries the original
shortcut:

```python
if user.role.value == "ADMIN":
    return project
```

`_ensure_project_access` returns straight away for any admin, without checking
ownership or membership. So an admin with no connection to a project cannot
rename or delete it, but can still list, create, edit and delete every task
inside it. Deleting all of a project's tasks is about as damaging as deleting
the project, so the two rules contradict each other.

`dashboard.py` has the same shortcut at line 33, though that one may be
intended. Section 4.1 of the PRD says an admin needs to see every task in one
place, so a wide read only dashboard is arguably the feature working as
designed. Writing to another team's tasks is not.

This is a gap in the D3 fix rather than a new problem, and it needs a product
decision before it is closed. See OQ-6 in the PRD.

