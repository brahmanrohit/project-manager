from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ProjectMember, User, UserRole
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Admins see everyone. Members only see people on their own projects.

    This used to hand the whole user directory, names and emails included, to
    anyone with a login.
    """
    if current_user.role == UserRole.ADMIN:
        return db.query(User).order_by(User.name.asc()).all()

    my_projects = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
    return (
        db.query(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id.in_(my_projects))
        .order_by(User.name.asc())
        .distinct()
        .all()
    )
