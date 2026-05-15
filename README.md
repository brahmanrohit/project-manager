# Ethara Project Management App

Production-ready full-stack project management web app with JWT auth, role-based access control (Admin/Member), project/task workflows, dashboard analytics, and Railway deployment support.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: React (Vite), TailwindCSS, Zustand, Axios
- Auth: JWT bearer token + bcrypt password hashing
- Deployment: Railway (backend + frontend services)

## Folder Structure

```text
Ethara_project/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── projects.py
│   │   │   ├── tasks.py
│   │   │   └── users.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── deps.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 0001_initial.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── .env.example
│   ├── alembic.ini
│   ├── railway.json
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── ProjectPage.jsx
│   │   │   └── SignupPage.jsx
│   │   ├── store/authStore.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── .env.example
│   ├── package.json
│   ├── railway.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── docker-compose.yml
└── README.md
```

## Core Features Implemented

### Authentication
- Signup/login endpoints
- bcrypt password hashing (`passlib[bcrypt]`)
- JWT creation and validation
- Protected API routes with dependency-based auth

### Role-Based Access Control
- Roles: `admin`, `member`
- Admin can create/update/delete projects and manage members
- Member can view assigned projects and manage assigned tasks only

### Project Management
- Create/list/update/delete projects
- Add/remove members in projects
- Ownership and membership relationships with cascading deletes

### Task Management
- Create/list/update/delete tasks inside projects
- Assign tasks to users
- Update status (`todo`, `in-progress`, `done`)
- Due-date support and overdue logic

### Dashboard
- Task list
- Status breakdown
- Overdue task count
- Filters by `project_id` and `user_id`

## Database Design

Tables:
- `users (id, name, email, password_hash, role)`
- `projects (id, name, description, owner_id)`
- `project_members (id, user_id, project_id)`
- `tasks (id, title, description, status, due_date, project_id, assigned_to)`

Includes:
- Foreign keys + constraints
- Indexes for common query paths
- Cascading delete behavior on project/user relationships
- Alembic initial migration in `backend/alembic/versions/0001_initial.py`

## Local Setup

### 1) Start PostgreSQL

```bash
docker compose up -d
```

### 2) Backend Setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

> Note: `Base.metadata.create_all()` runs on startup so tables auto-create if migrations were not run.

### 3) Frontend Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend: [http://localhost:5173](http://localhost:5173)

## API Overview

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/users/me`
- `GET /api/users`
- `GET /api/projects`
- `POST /api/projects` (admin)
- `PUT /api/projects/{project_id}` (admin)
- `DELETE /api/projects/{project_id}` (admin)
- `POST /api/projects/{project_id}/members` (admin)
- `DELETE /api/projects/{project_id}/members/{user_id}` (admin)
- `GET /api/projects/{project_id}/tasks`
- `POST /api/projects/{project_id}/tasks`
- `PUT /api/projects/{project_id}/tasks/{task_id}`
- `DELETE /api/projects/{project_id}/tasks/{task_id}`
- `GET /api/dashboard?project_id=&user_id=`

## Railway Deployment

Deploy as 2 Railway services from the same repository:

1. **Backend service**
   - Root directory: `backend`
   - Uses `backend/railway.json`
   - Set environment variables:
     - `DATABASE_URL` (Railway PostgreSQL URL; use SQLAlchemy format)
     - `SECRET_KEY`
     - `FRONTEND_URL` (your frontend Railway domain)
     - `ENV=production`
     - `DEBUG=false`
2. **Frontend service**
   - Root directory: `frontend`
   - Uses `frontend/railway.json`
   - Set `VITE_API_URL=https://<your-backend-domain>/api`

### Railway CLI (optional)

```bash
railway login
railway link
railway up
```

## Production Notes

- Replace default `SECRET_KEY` with a strong random secret.
- Keep `.env` out of source control.
- Use Alembic migrations for schema evolution in production.
- Configure CORS via `FRONTEND_URL`.

## Verification Status

- Backend source compilation passed (`python -m compileall app`)
- Frontend production build passed (`npm run build`)
