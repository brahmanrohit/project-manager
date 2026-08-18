from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ProjectMember, Task, TaskStatus, User, UserRole
from app.schemas import DashboardResponse, TaskOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    project_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Counts come from the database. Only one page of tasks is returned.

    This used to pull every task the caller could see into memory and count
    them in a Python loop, which for an admin meant the whole table on each
    dashboard load.
    """
    now = datetime.now(timezone.utc)

    def scoped(query):
        if current_user.role != UserRole.ADMIN:
            query = query.join(ProjectMember, Task.project_id == ProjectMember.project_id).filter(
                ProjectMember.user_id == current_user.id
            )
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if user_id:
            query = query.filter(Task.assigned_to == user_id)
        return query

    overdue_flag = case(
        (
            (Task.due_date.isnot(None)) & (Task.due_date < now) & (Task.status != TaskStatus.DONE),
            1,
        ),
        else_=0,
    )

    totals = scoped(
        db.query(
            func.count(Task.id).label("total"),
            func.coalesce(func.sum(overdue_flag), 0).label("overdue"),
        )
    ).one()

    by_status = scoped(db.query(Task.status, func.count(Task.id))).group_by(Task.status).all()

    status_breakdown = {"TODO": 0, "IN_PROGRESS": 0, "DONE": 0}
    for status_value, count in by_status:
        key = status_value.value if hasattr(status_value, "value") else str(status_value)
        status_breakdown[key] = count

    tasks = (
        scoped(db.query(Task))
        .order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.id.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return DashboardResponse(
        total_tasks=int(totals.total or 0),
        overdue_tasks=int(totals.overdue or 0),
        status_breakdown=status_breakdown,
        tasks=[TaskOut.model_validate(t) for t in tasks],
    )
