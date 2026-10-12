from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, verify_csrf_token
from app.repositories.task_repository import TaskRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskSubmitForReview,
    TaskReviewDecision,
    TaskResponse,
    TaskMessageCreate,
    TaskMessageResponse,
    ReportingOfficerOption,
)

router = APIRouter(prefix="/tasks", tags=["Task Management & Chat Workflow"])


def get_task_repo() -> TaskRepository:
    return TaskRepository(mongodb_manager.get_database())


def get_emp_repo() -> EmployeeRepository:
    return EmployeeRepository(mongodb_manager.get_database())


@router.get("/reporting-officers", response_model=List[ReportingOfficerOption])
async def list_reporting_officers(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Returns eligible reporting officers and managers for task assignment.
    """
    return await repo.list_eligible_reporting_officers()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf_token)])
async def create_employee_task(
    payload: TaskCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    task_repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_emp_repo),
):
    """
    Employee creates a personal or operational task, assigns a reporting officer, and saves in database.
    """
    emp_doc = await emp_repo.resolve_employee_doc(current_user)
    task_doc = await task_repo.create_task(payload, current_user, emp_doc)
    return await task_repo.serialize_task(task_doc)


@router.get("/my", response_model=List[TaskResponse])
async def list_my_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Returns tasks created by or assigned to the logged-in employee.
    """
    return await repo.list_my_tasks(current_user, status_filter)


@router.get("/review-queue", response_model=List[TaskResponse])
async def list_tasks_for_review(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Returns tasks where the authenticated user is the designated Reporting Officer.
    """
    return await repo.list_review_queue(current_user, status_filter)


@router.get("/all", response_model=List[TaskResponse])
async def list_all_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Governance overview: Returns all organizational tasks. Accessible to Super Admin and HR.
    """
    role = current_user.get("role", "")
    if role not in ["SUPER_ADMIN", "ADMIN", "HR"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Super Admin or HR required.")
    return await repo.list_all_tasks(status_filter)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_details(
    task_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Fetches detailed metadata, completion note, review history, and chat summary for a task.
    """
    doc = await repo.get_task_by_id(task_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return await repo.serialize_task(doc)


@router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(verify_csrf_token)])
async def update_task(
    task_id: str = Path(...),
    payload: TaskUpdate = ...,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Updates task details when permitted by ownership or role.
    """
    return await repo.update_task(task_id, payload, current_user)


@router.post("/{task_id}/submit", response_model=TaskResponse, dependencies=[Depends(verify_csrf_token)])
async def submit_task_for_review(
    task_id: str = Path(...),
    payload: TaskSubmitForReview = ...,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Workflow Step 1: Employee marks task as done, enters completion notes/evidence,
    and submits for formal review by their reporting officer.
    """
    return await repo.submit_task_for_review(task_id, payload, current_user)


@router.post("/{task_id}/review", response_model=TaskResponse, dependencies=[Depends(verify_csrf_token)])
async def review_task_submission(
    task_id: str = Path(...),
    payload: TaskReviewDecision = ...,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Workflow Step 2: Reporting Officer reviews the submitted work and either
    Approves (marking status COMPLETED) or Requests Revisions (marking status REVISIONS_REQUIRED).
    """
    return await repo.review_task(task_id, payload, current_user)


@router.get("/{task_id}/messages", response_model=List[TaskMessageResponse])
async def get_task_chat_messages(
    task_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Task-Specific Chat: Fetches chronological discussion thread.
    Restricted strictly to the Employee, Assigned Reporting Officer, and Super Admin.
    """
    return await repo.list_task_messages(task_id, current_user)


@router.post("/{task_id}/messages", response_model=TaskMessageResponse, dependencies=[Depends(verify_csrf_token)])
async def post_task_chat_message(
    task_id: str = Path(...),
    payload: TaskMessageCreate = ...,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    repo: TaskRepository = Depends(get_task_repo),
):
    """
    Task-Specific Chat: Posts a message to the task conversation and notifies counterpart participants.
    """
    return await repo.send_task_message(task_id, payload.message, current_user)
