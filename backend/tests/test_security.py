"""Regression tests for the four holes fixed on this branch.

Each test fails on the code as it was before.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import PLACEHOLDER_SECRETS, Settings
from app.models import Project, ProjectMember, Task, UserRole


def test_signup_cannot_make_an_admin(client, db_session):
    """D1. Posting role=ADMIN to the open signup route used to hand out admin."""
    response = client.post(
        "/api/auth/signup",
        json={
            "name": "Attacker",
            "email": "attacker@example.com",
            "password": "password123",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["user"]["role"] == "MEMBER"

    from app.models import User

    created = db_session.query(User).filter(User.email == "attacker@example.com").one()
    assert created.role == UserRole.MEMBER


@pytest.mark.parametrize("bad_secret", sorted(PLACEHOLDER_SECRETS) + [None, ""])
def test_placeholder_secret_is_refused(bad_secret):
    """D2. The app must not boot on a leftover example secret."""
    with pytest.raises(ValueError):
        Settings(secret_key=bad_secret, env="production", _env_file=None)


def test_admin_cannot_touch_a_project_they_do_not_own(client, db_session, make_user, auth_header):
    """D3. Being an admin used to mean authority over every project."""
    owner = make_user("owner@example.com", UserRole.ADMIN)
    outsider = make_user("outsider@example.com", UserRole.ADMIN)

    project = Project(name="Owner project", description=None, owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(ProjectMember(user_id=owner.id, project_id=project.id))
    db_session.commit()

    headers = auth_header("outsider@example.com")

    assert client.delete(f"/api/projects/{project.id}", headers=headers).status_code == 403
    assert client.put(f"/api/projects/{project.id}", json={"name": "Taken"}, headers=headers).status_code == 403

    db_session.expire_all()
    assert db_session.query(Project).filter(Project.id == project.id).one().name == "Owner project"


def test_member_cannot_read_another_members_task(client, db_session, make_user, auth_header):
    """A member sees their own queue, not the whole board."""
    admin = make_user("lead@example.com", UserRole.ADMIN)
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")

    project = Project(name="Shared", description=None, owner_id=admin.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    for user in (admin, alice, bob):
        db_session.add(ProjectMember(user_id=user.id, project_id=project.id))
    db_session.add(Task(title="Bob only", project_id=project.id, assigned_to=bob.id))
    db_session.commit()

    response = client.get(f"/api/projects/{project.id}/tasks", headers=auth_header("alice@example.com"))
    assert response.status_code == 200
    assert response.json() == []


def test_expired_token_is_rejected(client, make_user):
    """An old token must not keep working."""
    from app.config import settings

    make_user("stale@example.com")
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_task_cannot_be_given_to_a_non_member(client, db_session, make_user, auth_header):
    """A task assigned to an outsider disappears from every view."""
    admin = make_user("boss@example.com", UserRole.ADMIN)
    outsider = make_user("nobody@example.com")

    project = Project(name="Closed", description=None, owner_id=admin.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(ProjectMember(user_id=admin.id, project_id=project.id))
    db_session.commit()

    response = client.post(
        f"/api/projects/{project.id}/tasks",
        json={"title": "Orphan", "assigned_to": outsider.id},
        headers=auth_header("boss@example.com"),
    )
    assert response.status_code == 400


def test_removing_a_member_frees_their_tasks(client, db_session, make_user, auth_header):
    """D5. Their tasks used to stay pointed at someone locked out of the project."""
    admin = make_user("chief@example.com", UserRole.ADMIN)
    worker = make_user("worker@example.com")

    project = Project(name="Handover", description=None, owner_id=admin.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(ProjectMember(user_id=admin.id, project_id=project.id))
    db_session.add(ProjectMember(user_id=worker.id, project_id=project.id))
    task = Task(title="In flight", project_id=project.id, assigned_to=worker.id)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.delete(
        f"/api/projects/{project.id}/members/{worker.id}",
        headers=auth_header("chief@example.com"),
    )
    assert response.status_code == 204

    db_session.expire_all()
    assert db_session.query(Task).filter(Task.id == task.id).one().assigned_to is None


def test_member_directory_is_scoped(client, db_session, make_user, auth_header):
    """A member should not be handed every account on the server."""
    admin = make_user("owner2@example.com", UserRole.ADMIN)
    inside = make_user("inside@example.com")
    make_user("stranger@example.com")

    project = Project(name="Scoped", description=None, owner_id=admin.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    db_session.add(ProjectMember(user_id=admin.id, project_id=project.id))
    db_session.add(ProjectMember(user_id=inside.id, project_id=project.id))
    db_session.commit()

    emails = {u["email"] for u in client.get("/api/users", headers=auth_header("inside@example.com")).json()}
    assert "stranger@example.com" not in emails
    assert "owner2@example.com" in emails
