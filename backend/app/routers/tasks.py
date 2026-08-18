from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Project, ProjectMember, Task, TaskStatus, User, UserRole
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


def _ensure_project_access(db: Session, project_id: int, user: User, *, write: bool = False) -> Project:
    """Read wide, write narrow.

    An admin may read any project's tasks, which is what makes the whole
    install visible on the dashboard. Changing anything needs an actual
    relationship to the project: ownership or membership. Without that split,
    an admin who cannot delete a project could still delete every task in it.

    A member always needs membership, for reading and for writing.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
        .first()
        is not None
    )

    if user.role == UserRole.ADMIN:
        if not write or project.owner_id == user.id or is_member:
            return project
        raise HTTPException(status_code=403, detail="Not authorized to change this project's tasks")

    if not is_member:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


def _ensure_assignee_is_member(db: Session, project_id: int, assigned_to: int | None) -> None:
    """A task may only be given to someone who can actually open the project."""
    if assigned_to is None:
        return
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == assigned_to)
        .first()
    )
    if not member:
        raise HTTPException(status_code=400, detail="Assignee is not a member of this project")


@router.get("", response_model=list[TaskOut])
def list_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_project_access(db, project_id, current_user)
    query = db.query(Task).filter(Task.project_id == project_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Task.assigned_to == current_user.id)
    return query.all()


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_project_access(db, project_id, current_user, write=True)
    if current_user.role.value != "ADMIN" and payload.assigned_to not in (None, current_user.id):
        raise HTTPException(status_code=403, detail="Members can only assign tasks to themselves")
    _ensure_assignee_is_member(db, project_id, payload.assigned_to)
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        due_date=payload.due_date,
        project_id=project_id,
        assigned_to=payload.assigned_to,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    project_id: int,
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_project_access(db, project_id, current_user, write=True)
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role.value != "ADMIN" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")
    if current_user.role.value != "ADMIN" and payload.assigned_to not in (None, current_user.id):
        raise HTTPException(status_code=403, detail="Members can only assign tasks to themselves")

    if "assigned_to" in payload.model_fields_set:
        _ensure_assignee_is_member(db, project_id, payload.assigned_to)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_project_access(db, project_id, current_user, write=True)
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role.value != "ADMIN" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    db.delete(task)
    db.commit()


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_status(
    project_id: int,
    task_id: int,
    status_value: TaskStatus = Query(..., alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_task(project_id, task_id, TaskUpdate(status=status_value), db, current_user)
