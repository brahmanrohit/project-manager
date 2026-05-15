"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-30 21:00:00
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types safely (idempotent - skips if already exist)
    op.execute("DO $$ BEGIN CREATE TYPE userrole AS ENUM ('ADMIN', 'MEMBER'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE taskstatus AS ENUM ('TODO', 'IN_PROGRESS', 'DONE'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    # Create all tables via raw SQL — avoids SQLAlchemy auto-creating enum types
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL NOT NULL,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role userrole NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL NOT NULL,
            name VARCHAR(180) NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_id ON projects (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_owner_id ON projects (owner_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_members (
            id SERIAL NOT NULL,
            user_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            CONSTRAINT uq_project_member_user_project UNIQUE (user_id, project_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_id ON project_members (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_user_id ON project_members (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_project_id ON project_members (project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_members_user_project ON project_members (user_id, project_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL NOT NULL,
            title VARCHAR(180) NOT NULL,
            description TEXT,
            status taskstatus NOT NULL DEFAULT 'TODO',
            due_date TIMESTAMPTZ,
            project_id INTEGER NOT NULL,
            assigned_to INTEGER,
            created_at TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_id ON tasks (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_due_date ON tasks (due_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_project_id ON tasks (project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assigned_to ON tasks (assigned_to)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_project_status ON tasks (project_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assigned_to_due_date ON tasks (assigned_to, due_date)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks")
    op.execute("DROP TABLE IF EXISTS project_members")
    op.execute("DROP TABLE IF EXISTS projects")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
