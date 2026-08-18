from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin, require_project_admin
from app.models import Project, ProjectMember, Task, User
from app.schemas import ProjectCreate, ProjectMemberChange, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.value == "ADMIN":
        return db.query(Project).all()

    return (
        db.query(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    project = Project(name=payload.name, description=payload.description, owner_id=admin_user.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(user_id=admin_user.id, project_id=project.id))
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    project = require_project_admin(project_id, db, admin_user, owner_only=True)

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    project = require_project_admin(project_id, db, admin_user, owner_only=True)
    db.delete(project)
    db.commit()


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    payload: ProjectMemberChange,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    require_project_admin(project_id, db, admin_user)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Member already added")

    db.add(ProjectMember(project_id=project_id, user_id=payload.user_id))
    db.commit()
    return {"message": "Member added"}


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    require_project_admin(project_id, db, admin_user)

    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    # Hand their tasks back to the project instead of leaving them pointed at
    # someone who can no longer open the project.
    db.query(Task).filter(Task.project_id == project_id, Task.assigned_to == user_id).update(
        {Task.assigned_to: None}, synchronize_session=False
    )
    db.delete(membership)
    db.commit()
