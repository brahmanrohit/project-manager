from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ProjectMember, Task, User
from app.schemas import DashboardResponse, TaskOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    project_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task)

    if current_user.role.value != "ADMIN":
        query = query.join(ProjectMember, Task.project_id == ProjectMember.project_id).filter(
            ProjectMember.user_id == current_user.id
        )

    if project_id:
        query = query.filter(Task.project_id == project_id)
    if user_id:
        query = query.filter(Task.assigned_to == user_id)

    tasks = query.all()
    now = datetime.now(timezone.utc)
    overdue = [t for t in tasks if t.due_date and t.due_date < now and t.status.value != "DONE"]

    status_breakdown = {"TODO": 0, "IN_PROGRESS": 0, "DONE": 0}
    for task in tasks:
        status_breakdown[task.status.value] = status_breakdown.get(task.status.value, 0) + 1

    return DashboardResponse(
        total_tasks=len(tasks),
        overdue_tasks=len(overdue),
        status_breakdown=status_breakdown,
        tasks=[TaskOut.model_validate(t) for t in tasks],
    )
