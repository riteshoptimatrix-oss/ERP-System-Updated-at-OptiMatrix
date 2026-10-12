export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export type TaskStatus =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'SUBMITTED_FOR_REVIEW'
  | 'COMPLETED'
  | 'REVISIONS_REQUIRED';

export interface ReportingOfficerOption {
  id: string;
  user_id?: string;
  name: string;
  email: string;
  designation: string;
  department: string;
  role: string;
}

export interface TaskItem {
  id: string;
  task_number: string;
  title: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  due_date?: string | null;

  reporting_officer_id?: string | null;
  reporting_officer_name?: string | null;
  reporting_officer_email?: string | null;

  created_by_id: string;
  created_by_code?: string | null;
  created_by_name: string;
  created_by_email: string;

  created_at: string;
  updated_at?: string | null;

  submitted_at?: string | null;
  submitted_by?: string | null;
  completion_note?: string | null;
  completion_evidence?: string | null;

  reviewed_at?: string | null;
  reviewed_by?: string | null;
  review_feedback?: string | null;

  attachments: string[];
  source_module: string;
  unit_id: string;
  message_count: number;
}

export interface TaskCreatePayload {
  title: string;
  description: string;
  due_date?: string;
  priority: TaskPriority;
  reporting_officer_id: string;
  attachments?: string[];
  unit_id?: string;
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  due_date?: string;
  priority?: TaskPriority;
  reporting_officer_id?: string;
  status?: TaskStatus;
  notes?: string;
  attachments?: string[];
}

export interface TaskSubmitPayload {
  completion_note: string;
  completion_evidence?: string;
  attachments?: string[];
}

export interface TaskReviewPayload {
  decision: 'APPROVED' | 'REVISIONS_REQUIRED';
  feedback_note: string;
}

export interface TaskMessage {
  id: string;
  task_id: string;
  sender_id: string;
  sender_name: string;
  sender_email: string;
  sender_role: 'EMPLOYEE' | 'REPORTING_OFFICER' | 'SUPER_ADMIN' | string;
  message: string;
  created_at: string;
}
