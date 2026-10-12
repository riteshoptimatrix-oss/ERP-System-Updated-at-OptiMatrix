from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskSubmitForReview,
    TaskReviewDecision,
    TaskResponse,
    TaskMessageResponse,
    TaskStatus,
    TaskPriority,
    ReportingOfficerOption,
)


class TaskRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.tasks_col = db["tasks"]
        self.messages_col = db["task_messages"]
        self.users_col = db["users"]
        self.employees_col = db["employees"]
        self.notifications_col = db["notifications"]

    async def list_eligible_reporting_officers(self) -> List[ReportingOfficerOption]:
        """
        Returns authorized officers and managers who can be assigned as reporting officers:
        Super Admin, HR, Department Managers, and Supervisors.
        """
        officers: List[ReportingOfficerOption] = []
        seen_emails = set()

        # 1. Fetch authorized administrative & management users
        users_cursor = self.users_col.find({
            "is_active": True,
            "role": {"$in": ["SUPER_ADMIN", "ADMIN", "HR", "PRODUCTION_MANAGER", "INVENTORY_MANAGER", "QC_INSPECTOR", "SALES_DISPATCH"]}
        }).sort("role", 1)
        users = await users_cursor.to_list(length=100)

        # Build mapping of employee details for user emails
        emp_cursor = self.employees_col.find({"is_active": True})
        employees = await emp_cursor.to_list(length=200)
        emp_map = {e.get("email"): e for e in employees if e.get("email")}

        for u in users:
            email = u.get("email")
            if not email or email in seen_emails:
                continue
            seen_emails.add(email)

            emp = emp_map.get(email, {})
            designation = emp.get("designation") or u.get("role", "Management Officer").replace("_", " ").title()
            department = emp.get("department") or "Operations & Governance"

            officers.append(
                ReportingOfficerOption(
                    id=str(u["_id"]),
                    user_id=str(u["_id"]),
                    name=u.get("full_name") or f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or email,
                    email=email,
                    designation=designation,
                    department=department,
                    role=u.get("role", "ADMIN"),
                )
            )

        # 2. Also include any employee with Manager / Supervisor / Head designation
        for emp in employees:
            email = emp.get("email")
            if not email or email in seen_emails:
                continue
            desig = (emp.get("designation") or "").lower()
            if any(k in desig for k in ["manager", "supervisor", "head", "lead", "director"]):
                seen_emails.add(email)
                officers.append(
                    ReportingOfficerOption(
                        id=str(emp["_id"]),
                        user_id=str(emp.get("user_id", emp["_id"])),
                        name=f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or emp.get("full_name") or email,
                        email=email,
                        designation=emp.get("designation", "Manager"),
                        department=emp.get("department", "Management"),
                        role=emp.get("account_type", "OFFICER"),
                    )
                )

        return officers

    async def create_task(
        self,
        payload: TaskCreate,
        current_user: Dict[str, Any],
        emp_doc: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new employee task, persists in MongoDB, and notifies the designated reporting officer.
        """
        now = datetime.now(timezone.utc)

        # Generate unique task sequence number
        count = await self.tasks_col.count_documents({})
        year = now.year
        task_number = f"TSK-{year}-{count + 1:04d}"

        # Resolve assigned reporting officer
        officer_name = "Assigned Reporting Officer"
        officer_email = payload.reporting_officer_id
        officer_user_id = payload.reporting_officer_id

        # Try matching by user ObjectId or email
        officer_user = None
        if ObjectId.is_valid(payload.reporting_officer_id):
            officer_user = await self.users_col.find_one({"_id": ObjectId(payload.reporting_officer_id)})
        if not officer_user:
            officer_user = await self.users_col.find_one({"email": payload.reporting_officer_id})

        if officer_user:
            officer_name = officer_user.get("full_name") or officer_user.get("email", officer_name)
            officer_email = officer_user.get("email", officer_email)
            officer_user_id = str(officer_user["_id"])
        else:
            # Check employees collection
            emp_officer = None
            if ObjectId.is_valid(payload.reporting_officer_id):
                emp_officer = await self.employees_col.find_one({"_id": ObjectId(payload.reporting_officer_id)})
            if not emp_officer:
                emp_officer = await self.employees_col.find_one({"email": payload.reporting_officer_id})
            if emp_officer:
                first = emp_officer.get("first_name", "")
                last = emp_officer.get("last_name", "")
                officer_name = f"{first} {last}".strip() or emp_officer.get("full_name") or emp_officer.get("email")
                officer_email = emp_officer.get("email")
                officer_user_id = str(emp_officer.get("user_id") or emp_officer["_id"])

        creator_name = (
            current_user.get("full_name")
            or (f"{emp_doc.get('first_name', '')} {emp_doc.get('last_name', '')}".strip() if emp_doc else None)
            or current_user.get("email", "Employee")
        )
        creator_code = emp_doc.get("code") if emp_doc else current_user.get("employee_code")

        task_doc = {
            "task_number": task_number,
            "title": payload.title.strip(),
            "description": payload.description.strip(),
            "priority": payload.priority.value,
            "status": TaskStatus.PENDING.value,
            "due_date": payload.due_date,
            "reporting_officer_id": officer_user_id,
            "reporting_officer_name": officer_name,
            "reporting_officer_email": officer_email,
            "created_by_id": str(current_user["_id"]),
            "created_by_code": creator_code,
            "created_by_name": creator_name,
            "created_by_email": current_user["email"],
            "attachments": payload.attachments or [],
            "source_module": "task_management",
            "unit_id": payload.unit_id or (emp_doc.get("unit_id") if emp_doc else "Unit_1") or "Unit_1",
            "created_at": now,
            "updated_at": now,
            "completion_note": None,
            "completion_evidence": None,
            "submitted_at": None,
            "submitted_by": None,
            "reviewed_at": None,
            "reviewed_by": None,
            "review_feedback": None,
        }

        res = await self.tasks_col.insert_one(task_doc)
        task_doc["_id"] = res.inserted_id

        # Dispatch notification to reporting officer
        await self.notifications_col.insert_one({
            "user_id": officer_user_id,
            "employee_code": None,
            "title": f"New Task Assigned: {task_number}",
            "message": f"{creator_name} created task '{payload.title}' and designated you as Reporting Officer.",
            "notification_type": "TASK",
            "is_read": False,
            "link": "/employee/tasks",
            "created_at": now,
            "metadata": {
                "task_id": str(res.inserted_id),
                "task_number": task_number,
                "created_by": creator_name,
            },
        })

        return task_doc

    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        query = {"_id": ObjectId(task_id)} if ObjectId.is_valid(task_id) else {"_id": task_id}
        doc = await self.tasks_col.find_one(query)
        if not doc:
            doc = await self.tasks_col.find_one({"task_number": task_id})
        return doc

    async def count_task_messages(self, task_id: str) -> int:
        return await self.messages_col.count_documents({"task_id": str(task_id)})

    async def serialize_task(self, doc: Dict[str, Any]) -> TaskResponse:
        task_id = str(doc["_id"])
        msg_count = await self.count_task_messages(task_id)
        return TaskResponse(
            id=task_id,
            task_number=doc.get("task_number", f"TSK-{task_id[:6]}"),
            title=doc.get("title", ""),
            description=doc.get("description", ""),
            priority=TaskPriority(doc.get("priority", "MEDIUM")),
            status=TaskStatus(doc.get("status", "PENDING")),
            due_date=doc.get("due_date"),
            reporting_officer_id=doc.get("reporting_officer_id"),
            reporting_officer_name=doc.get("reporting_officer_name"),
            reporting_officer_email=doc.get("reporting_officer_email"),
            created_by_id=str(doc.get("created_by_id", "")),
            created_by_code=doc.get("created_by_code"),
            created_by_name=doc.get("created_by_name", "Employee"),
            created_by_email=doc.get("created_by_email", ""),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at"),
            submitted_at=doc.get("submitted_at"),
            submitted_by=doc.get("submitted_by"),
            completion_note=doc.get("completion_note"),
            completion_evidence=doc.get("completion_evidence"),
            reviewed_at=doc.get("reviewed_at"),
            reviewed_by=doc.get("reviewed_by"),
            review_feedback=doc.get("review_feedback"),
            attachments=doc.get("attachments", []),
            source_module=doc.get("source_module", "task_management"),
            unit_id=doc.get("unit_id", "Unit_1"),
            message_count=msg_count,
        )

    async def list_my_tasks(
        self,
        current_user: Dict[str, Any],
        status_filter: Optional[str] = None,
    ) -> List[TaskResponse]:
        """
        Tasks created by or assigned to the current employee.
        """
        user_id = str(current_user["_id"])
        email = current_user.get("email")

        query: Dict[str, Any] = {
            "$or": [
                {"created_by_id": user_id},
                {"created_by_email": email},
            ]
        }
        if status_filter and status_filter != "ALL":
            query["status"] = status_filter

        cursor = self.tasks_col.find(query).sort("created_at", -1).limit(100)
        docs = await cursor.to_list(length=100)
        return [await self.serialize_task(d) for d in docs]

    async def list_review_queue(
        self,
        current_user: Dict[str, Any],
        status_filter: Optional[str] = None,
    ) -> List[TaskResponse]:
        """
        Tasks where current user is the designated Reporting Officer or Super Admin.
        """
        user_id = str(current_user["_id"])
        email = current_user.get("email")
        role = current_user.get("role", "")

        query: Dict[str, Any] = {}
        if role == "SUPER_ADMIN":
            # Super admin can see all tasks needing review or in workflow
            pass
        else:
            query["$or"] = [
                {"reporting_officer_id": user_id},
                {"reporting_officer_email": email},
            ]

        if status_filter and status_filter != "ALL":
            query["status"] = status_filter

        cursor = self.tasks_col.find(query).sort("created_at", -1).limit(100)
        docs = await cursor.to_list(length=100)
        return [await self.serialize_task(d) for d in docs]

    async def list_all_tasks(self, status_filter: Optional[str] = None) -> List[TaskResponse]:
        """
        Governance view for Super Admin and HR.
        """
        query: Dict[str, Any] = {}
        if status_filter and status_filter != "ALL":
            query["status"] = status_filter

        cursor = self.tasks_col.find(query).sort("created_at", -1).limit(200)
        docs = await cursor.to_list(length=200)
        return [await self.serialize_task(d) for d in docs]

    async def update_task(
        self,
        task_id: str,
        payload: TaskUpdate,
        current_user: Dict[str, Any],
    ) -> TaskResponse:
        task = await self.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        # Permission check: Creator, Assigned Officer, or Super Admin
        is_creator = str(task.get("created_by_id")) == str(current_user["_id"]) or task.get("created_by_email") == current_user["email"]
        is_officer = str(task.get("reporting_officer_id")) == str(current_user["_id"]) or task.get("reporting_officer_email") == current_user["email"]
        is_admin = current_user.get("role") == "SUPER_ADMIN"

        if not (is_creator or is_officer or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this task.")

        now = datetime.now(timezone.utc)
        update_fields: Dict[str, Any] = {"updated_at": now}

        if payload.title:
            update_fields["title"] = payload.title.strip()
        if payload.description:
            update_fields["description"] = payload.description.strip()
        if payload.due_date is not None:
            update_fields["due_date"] = payload.due_date
        if payload.priority:
            update_fields["priority"] = payload.priority.value
        if payload.status:
            update_fields["status"] = payload.status.value
        if payload.attachments is not None:
            update_fields["attachments"] = payload.attachments

        if payload.reporting_officer_id:
            # Resolve officer info
            officer = await self.users_col.find_one({
                "$or": [
                    {"_id": ObjectId(payload.reporting_officer_id)} if ObjectId.is_valid(payload.reporting_officer_id) else {"_id": None},
                    {"email": payload.reporting_officer_id},
                ]
            })
            if officer:
                update_fields["reporting_officer_id"] = str(officer["_id"])
                update_fields["reporting_officer_name"] = officer.get("full_name", officer["email"])
                update_fields["reporting_officer_email"] = officer["email"]

        await self.tasks_col.update_one({"_id": task["_id"]}, {"$set": update_fields})
        updated = await self.get_task_by_id(task_id)
        return await self.serialize_task(updated)

    async def submit_task_for_review(
        self,
        task_id: str,
        payload: TaskSubmitForReview,
        current_user: Dict[str, Any],
    ) -> TaskResponse:
        """
        Employee marks task as done and formally submits completion note to Reporting Officer.
        Changes status to SUBMITTED_FOR_REVIEW and triggers notification.
        """
        task = await self.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        # Check authorization (Creator or Super Admin)
        is_creator = str(task.get("created_by_id")) == str(current_user["_id"]) or task.get("created_by_email") == current_user["email"]
        is_admin = current_user.get("role") == "SUPER_ADMIN"
        if not (is_creator or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the employee who owns this task can submit it for review.")

        now = datetime.now(timezone.utc)
        existing_attachments = task.get("attachments", [])
        if payload.attachments:
            for att in payload.attachments:
                if att not in existing_attachments:
                    existing_attachments.append(att)

        update_data = {
            "status": TaskStatus.SUBMITTED_FOR_REVIEW.value,
            "submitted_at": now,
            "submitted_by": current_user.get("full_name") or current_user.get("email"),
            "completion_note": payload.completion_note.strip(),
            "completion_evidence": payload.completion_evidence.strip() if payload.completion_evidence else None,
            "attachments": existing_attachments,
            "updated_at": now,
        }

        await self.tasks_col.update_one({"_id": task["_id"]}, {"$set": update_data})

        # Send notification to assigned reporting officer
        officer_id = task.get("reporting_officer_id")
        officer_email = task.get("reporting_officer_email")
        if officer_id or officer_email:
            await self.notifications_col.insert_one({
                "user_id": officer_id,
                "employee_code": None,
                "title": f"Review Required: {task.get('task_number')} Submitted",
                "message": f"{current_user.get('full_name')} submitted task '{task.get('title')}' for your formal approval. Note: {payload.completion_note[:90]}...",
                "notification_type": "TASK",
                "is_read": False,
                "link": "/employee/tasks",
                "created_at": now,
                "metadata": {
                    "task_id": str(task["_id"]),
                    "task_number": task.get("task_number"),
                    "action": "SUBMITTED_FOR_REVIEW",
                },
            })

        updated = await self.get_task_by_id(task_id)
        return await self.serialize_task(updated)

    async def review_task(
        self,
        task_id: str,
        payload: TaskReviewDecision,
        current_user: Dict[str, Any],
    ) -> TaskResponse:
        """
        Reporting Officer reviews completion submission and either Approves (COMPLETED)
        or Requests Revisions (REVISIONS_REQUIRED) with mandatory feedback.
        """
        task = await self.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        # Check authorization (Assigned Reporting Officer, HR, or Super Admin)
        is_officer = str(task.get("reporting_officer_id")) == str(current_user["_id"]) or task.get("reporting_officer_email") == current_user["email"]
        is_admin = current_user.get("role") in ["SUPER_ADMIN", "ADMIN", "HR"]
        if not (is_officer or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the designated reporting officer or super admin can review this task.")

        decision = payload.decision.upper()
        if decision not in ["APPROVED", "REVISIONS_REQUIRED"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be 'APPROVED' or 'REVISIONS_REQUIRED'.")

        now = datetime.now(timezone.utc)
        reviewer_name = current_user.get("full_name") or current_user.get("email")

        new_status = TaskStatus.COMPLETED.value if decision == "APPROVED" else TaskStatus.REVISIONS_REQUIRED.value

        update_data = {
            "status": new_status,
            "reviewed_at": now,
            "reviewed_by": reviewer_name,
            "review_feedback": payload.feedback_note.strip(),
            "updated_at": now,
        }

        await self.tasks_col.update_one({"_id": task["_id"]}, {"$set": update_data})

        # Send notification to the employee creator
        creator_id = str(task.get("created_by_id"))
        status_label = "Approved & Completed" if decision == "APPROVED" else "Revisions Requested"
        await self.notifications_col.insert_one({
            "user_id": creator_id,
            "employee_code": task.get("created_by_code"),
            "title": f"Task {task.get('task_number')}: {status_label}",
            "message": f"Officer {reviewer_name} reviewed your task '{task.get('title')}'. Feedback: {payload.feedback_note[:100]}",
            "notification_type": "TASK",
            "is_read": False,
            "link": "/employee/tasks",
            "created_at": now,
            "metadata": {
                "task_id": str(task["_id"]),
                "task_number": task.get("task_number"),
                "status": new_status,
            },
        })

        updated = await self.get_task_by_id(task_id)
        return await self.serialize_task(updated)

    async def verify_chat_access(self, task: Dict[str, Any], current_user: Dict[str, Any]) -> str:
        """
        Ensures user is an authorized participant:
        - Employee who created the task -> role 'EMPLOYEE'
        - Reporting Officer assigned -> role 'REPORTING_OFFICER'
        - Super Admin / HR -> role 'SUPER_ADMIN'
        """
        role = current_user.get("role")
        user_id = str(current_user["_id"])
        email = current_user.get("email")

        if role == "SUPER_ADMIN":
            return "SUPER_ADMIN"

        if str(task.get("reporting_officer_id")) == user_id or task.get("reporting_officer_email") == email:
            return "REPORTING_OFFICER"

        if str(task.get("created_by_id")) == user_id or task.get("created_by_email") == email:
            return "EMPLOYEE"

        if role in ["ADMIN", "HR"]:
            return "SUPER_ADMIN"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the task employee, assigned reporting officer, and super admin can participate in this task chat.",
        )

    async def list_task_messages(self, task_id: str, current_user: Dict[str, Any]) -> List[TaskMessageResponse]:
        task = await self.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        await self.verify_chat_access(task, current_user)

        cursor = self.messages_col.find({"task_id": str(task["_id"])}).sort("created_at", 1)
        items = await cursor.to_list(length=300)

        return [
            TaskMessageResponse(
                id=str(m["_id"]),
                task_id=m["task_id"],
                sender_id=m["sender_id"],
                sender_name=m["sender_name"],
                sender_email=m["sender_email"],
                sender_role=m["sender_role"],
                message=m["message"],
                created_at=m.get("created_at", datetime.now(timezone.utc)),
            )
            for m in items
        ]

    async def send_task_message(
        self,
        task_id: str,
        message_str: str,
        current_user: Dict[str, Any],
    ) -> TaskMessageResponse:
        task = await self.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        participant_role = await self.verify_chat_access(task, current_user)
        now = datetime.now(timezone.utc)

        sender_name = current_user.get("full_name") or current_user.get("email")

        msg_doc = {
            "task_id": str(task["_id"]),
            "sender_id": str(current_user["_id"]),
            "sender_name": sender_name,
            "sender_email": current_user["email"],
            "sender_role": participant_role,
            "message": message_str.strip(),
            "created_at": now,
        }

        res = await self.messages_col.insert_one(msg_doc)
        msg_doc["_id"] = res.inserted_id

        # Update task timestamp
        await self.tasks_col.update_one({"_id": task["_id"]}, {"$set": {"updated_at": now}})

        # Notify the other participant(s)
        creator_id = str(task.get("created_by_id"))
        officer_id = str(task.get("reporting_officer_id"))
        sender_id = str(current_user["_id"])

        recipients = set()
        if creator_id != sender_id:
            recipients.add(creator_id)
        if officer_id and officer_id != sender_id:
            recipients.add(officer_id)

        for rec_id in recipients:
            await self.notifications_col.insert_one({
                "user_id": rec_id,
                "title": f"New Message on Task {task.get('task_number')}",
                "message": f"{sender_name} ({participant_role.replace('_', ' ').title()}): {message_str.strip()[:80]}",
                "notification_type": "CHAT",
                "is_read": False,
                "link": "/employee/tasks",
                "created_at": now,
                "metadata": {
                    "task_id": str(task["_id"]),
                    "task_number": task.get("task_number"),
                },
            })

        return TaskMessageResponse(
            id=str(msg_doc["_id"]),
            task_id=msg_doc["task_id"],
            sender_id=msg_doc["sender_id"],
            sender_name=msg_doc["sender_name"],
            sender_email=msg_doc["sender_email"],
            sender_role=msg_doc["sender_role"],
            message=msg_doc["message"],
            created_at=now,
        )
