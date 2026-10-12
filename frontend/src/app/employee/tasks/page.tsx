'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { taskClient } from '@/services/task-client';
import {
  TaskItem,
  TaskPriority,
  TaskStatus,
  TaskMessage,
  ReportingOfficerOption,
} from '@/types/tasks';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Plus,
  RefreshCw,
  MessageSquare,
  CheckCircle2,
  AlertCircle,
  Clock,
  Calendar,
  UserCheck,
  Send,
  FileCheck2,
  FileText,
  AlertTriangle,
  RotateCcw,
  Check,
  ChevronRight,
  Shield,
  Search,
  Filter,
  Lock,
} from 'lucide-react';
import { formatISTDate } from '@/lib/date';

export default function EmployeeTasksPage() {
  const { user, activeUnit, isLoading: isAuthLoading } = useAuth();
  const router = useRouter();

  // Primary State
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [activeTab, setActiveTab] = useState<'my' | 'review' | 'all'>('my');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  // Officers list for dropdown
  const [officers, setOfficers] = useState<ReportingOfficerOption[]>([]);

  // Modals State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState<boolean>(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);

  // Chat / Detail Drawer State
  const [activeChatTask, setActiveChatTask] = useState<TaskItem | null>(null);
  const [chatMessages, setChatMessages] = useState<TaskMessage[]>([]);
  const [newMessageText, setNewMessageText] = useState<string>('');
  const [isSendingMessage, setIsSendingMessage] = useState<boolean>(false);
  const [detailTab, setDetailTab] = useState<'details' | 'chat'>('details');
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Create Task Form State
  const [createTitle, setCreateTitle] = useState<string>('');
  const [createDescription, setCreateDescription] = useState<string>('');
  const [createDueDate, setCreateDueDate] = useState<string>('');
  const [createPriority, setCreatePriority] = useState<TaskPriority>('MEDIUM');
  const [createOfficerId, setCreateOfficerId] = useState<string>('');
  const [createAttachments, setCreateAttachments] = useState<string>('');
  const [isCreating, setIsCreating] = useState<boolean>(false);

  // Submit Completion Form State
  const [completionNote, setCompletionNote] = useState<string>('');
  const [completionEvidence, setCompletionEvidence] = useState<string>('');
  const [isSubmittingWork, setIsSubmittingWork] = useState<boolean>(false);

  // Review Form State
  const [reviewDecision, setReviewDecision] = useState<'APPROVED' | 'REVISIONS_REQUIRED'>('APPROVED');
  const [reviewFeedback, setReviewFeedback] = useState<string>('');
  const [isReviewing, setIsReviewing] = useState<boolean>(false);

  const isManagementOrAdmin =
    user?.role === 'SUPER_ADMIN' ||
    user?.role === 'ADMIN' ||
    user?.role === 'HR' ||
    user?.job_role?.toLowerCase().includes('manager') ||
    user?.job_role?.toLowerCase().includes('lead');

  // Load Reporting Officers list
  const loadOfficers = useCallback(async () => {
    if (!user) return;
    try {
      const data = await taskClient.listReportingOfficers();
      setOfficers(data);
      if (data.length > 0 && !createOfficerId) {
        setCreateOfficerId(data[0].id);
      }
    } catch (err) {
      console.warn('Could not load reporting officers:', err);
    }
  }, [user, createOfficerId]);

  // Load Tasks based on tab
  const loadTasks = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    setErrorMessage('');
    try {
      let data: TaskItem[] = [];
      if (activeTab === 'my') {
        data = await taskClient.listMyTasks();
      } else if (activeTab === 'review') {
        data = await taskClient.listReviewQueue();
      } else if (activeTab === 'all') {
        data = await taskClient.listAllTasks();
      }
      setTasks(data);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setIsLoading(false);
    }
  }, [user, activeTab]);

  useEffect(() => {
    if (user) {
      loadOfficers();
    }
  }, [user, loadOfficers]);

  useEffect(() => {
    if (user) {
      loadTasks();
    }
  }, [user, loadTasks]);

  // Load Chat Messages for Active Task
  const loadChatMessages = useCallback(async (taskId: string) => {
    try {
      const msgs = await taskClient.listMessages(taskId);
      setChatMessages(msgs);
    } catch (err) {
      console.error('Failed to load chat messages:', err);
    }
  }, []);

  // Poll chat messages every 3.5s when chat drawer is open
  useEffect(() => {
    if (!activeChatTask) return;
    loadChatMessages(activeChatTask.id);

    const interval = setInterval(() => {
      loadChatMessages(activeChatTask.id);
    }, 3500);

    return () => clearInterval(interval);
  }, [activeChatTask, loadChatMessages]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (detailTab === 'chat' && chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, detailTab]);

  // Handle Create Task
  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createTitle.trim()) {
      setErrorMessage('Task title is required.');
      return;
    }
    if (!createOfficerId) {
      setErrorMessage('Please assign a reporting officer.');
      return;
    }

    setIsCreating(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const attachmentsList = createAttachments
        .split(',')
        .map((a) => a.trim())
        .filter((a) => a.length > 0);

      const created = await taskClient.createTask({
        title: createTitle.trim(),
        description: createDescription.trim(),
        due_date: createDueDate || undefined,
        priority: createPriority,
        reporting_officer_id: createOfficerId,
        attachments: attachmentsList,
        unit_id: activeUnit || 'Unit_1',
      });

      setSuccessMessage(`Task "${created.title}" created successfully and assigned to ${created.reporting_officer_name}.`);
      setIsCreateModalOpen(false);
      setCreateTitle('');
      setCreateDescription('');
      setCreateDueDate('');
      setCreateAttachments('');
      await loadTasks();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setIsCreating(false);
    }
  };

  // Handle Submit for Review
  const handleOpenSubmit = (task: TaskItem) => {
    setSelectedTask(task);
    setCompletionNote('');
    setCompletionEvidence('');
    setIsSubmitModalOpen(true);
  };

  const handleSubmitForReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    if (!completionNote.trim()) {
      setErrorMessage('Please enter a completion note describing what was accomplished.');
      return;
    }

    setIsSubmittingWork(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const updated = await taskClient.submitForReview(selectedTask.id, {
        completion_note: completionNote.trim(),
        completion_evidence: completionEvidence.trim() || undefined,
      });

      setSuccessMessage(`Task "${updated.title}" submitted for formal review to ${updated.reporting_officer_name}.`);
      setIsSubmitModalOpen(false);
      setSelectedTask(null);
      await loadTasks();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to submit task for review');
    } finally {
      setIsSubmittingWork(false);
    }
  };

  // Handle Review
  const handleOpenReview = (task: TaskItem) => {
    setSelectedTask(task);
    setReviewDecision('APPROVED');
    setReviewFeedback('');
    setIsReviewModalOpen(true);
  };

  const handleReviewDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    if (reviewDecision === 'REVISIONS_REQUIRED' && !reviewFeedback.trim()) {
      setErrorMessage('A feedback note is required when requesting revisions.');
      return;
    }

    setIsReviewing(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const updated = await taskClient.reviewTask(selectedTask.id, {
        decision: reviewDecision,
        feedback_note: reviewFeedback.trim() || (reviewDecision === 'APPROVED' ? 'Approved and verified.' : 'Revisions requested.'),
      });

      const outcome = reviewDecision === 'APPROVED' ? 'approved as Completed' : 'marked for Revisions';
      setSuccessMessage(`Task "${updated.title}" ${outcome}. Employee notified.`);
      setIsReviewModalOpen(false);
      setSelectedTask(null);
      await loadTasks();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to review task');
    } finally {
      setIsReviewing(false);
    }
  };

  // Handle Send Chat Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeChatTask || !newMessageText.trim() || isSendingMessage) return;

    const text = newMessageText.trim();
    setNewMessageText('');
    setIsSendingMessage(true);

    try {
      const msg = await taskClient.sendMessage(activeChatTask.id, text);
      setChatMessages((prev) => [...prev, msg]);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsSendingMessage(false);
    }
  };

  // Filter Tasks
  const filteredTasks = tasks.filter((t) => {
    if (statusFilter !== 'ALL' && t.status !== statusFilter) return false;
    if (priorityFilter !== 'ALL' && t.priority !== priorityFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = t.title.toLowerCase().includes(q);
      const matchDesc = t.description?.toLowerCase().includes(q);
      const matchNum = t.task_number.toLowerCase().includes(q);
      const matchOfficer = t.reporting_officer_name?.toLowerCase().includes(q);
      const matchCreator = t.created_by_name?.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchNum && !matchOfficer && !matchCreator) return false;
    }
    return true;
  });

  const getStatusBadge = (status: TaskStatus) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="neutral">Pending</Badge>;
      case 'IN_PROGRESS':
        return <Badge variant="warning" className="bg-sky-50 text-sky-700 border-sky-200">In Progress</Badge>;
      case 'SUBMITTED_FOR_REVIEW':
        return <Badge variant="warning" className="bg-amber-100 text-amber-800 border-amber-300 font-semibold">Submitted for Review</Badge>;
      case 'REVISIONS_REQUIRED':
        return <Badge variant="error" className="bg-rose-100 text-rose-800 border-rose-300 font-semibold">Revisions Required</Badge>;
      case 'COMPLETED':
        return <Badge variant="success" className="bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold">Completed</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const getPriorityBadge = (priority: TaskPriority) => {
    switch (priority) {
      case 'URGENT':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white uppercase">Urgent</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500 text-white uppercase">High</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-100 text-sky-800 border border-sky-200 uppercase">Medium</span>;
      case 'LOW':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200 uppercase">Low</span>;
    }
  };

  if (isAuthLoading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-[#315C45]" />
          <p className="text-xs text-slate-500 font-medium">Verifying employee access...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white rounded-2xl shadow-sm border border-slate-200 space-y-4">
        <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto">
          <Lock className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Session Required</h2>
        <p className="text-xs text-slate-500">
          Your session has expired or you are not currently logged in. Please log in to view and manage your assigned tasks.
        </p>
        <Button onClick={() => router.push('/login')} className="w-full bg-[#315C45] hover:bg-[#254936] text-white text-xs">
          Go to Corporate Login
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#315C45]" />
        <div className="space-y-1 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#315C45] font-mono">
              Operations & Employee Task Management
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Task Management & Workflow System
          </h1>
          <p className="text-xs text-slate-500">
            Create tasks, submit completed work to your reporting officer, track feedback, and collaborate in real-time.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            onClick={() => setIsCreateModalOpen(true)}
            className="text-xs flex items-center gap-1.5 bg-[#315C45] hover:bg-[#254936] text-white"
          >
            <Plus className="h-4 w-4" />
            Create Task
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={loadTasks}
            disabled={isLoading}
            className="text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage('')} className="ml-auto text-rose-500 hover:text-rose-800 text-sm font-bold">&times;</button>
        </div>
      )}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
          <button onClick={() => setSuccessMessage('')} className="ml-auto text-emerald-500 hover:text-emerald-800 text-sm font-bold">&times;</button>
        </div>
      )}

      {/* Tab Navigation: My Tasks / Review Queue / All */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('my')}
            className={`px-4 py-2 font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'my'
                ? 'bg-[#315C45] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
          >
            <span>My Tasks</span>
            {activeTab === 'my' && <span className="bg-white/20 text-white text-[10px] px-1.5 py-0.2 rounded-full">{tasks.length}</span>}
          </button>

          {isManagementOrAdmin && (
            <button
              type="button"
              onClick={() => setActiveTab('review')}
              className={`px-4 py-2 font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'review'
                  ? 'bg-[#315C45] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
            >
              <span>Review Queue</span>
              {activeTab === 'review' && <span className="bg-white/20 text-white text-[10px] px-1.5 py-0.2 rounded-full">{tasks.length}</span>}
            </button>
          )}

          {(user?.role === 'SUPER_ADMIN' || user?.role === 'ADMIN' || user?.role === 'HR') && (
            <button
              type="button"
              onClick={() => setActiveTab('all')}
              className={`px-4 py-2 font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'all'
                  ? 'bg-[#315C45] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
            >
              <span>All Tasks (Governance)</span>
              {activeTab === 'all' && <span className="bg-white/20 text-white text-[10px] px-1.5 py-0.2 rounded-full">{tasks.length}</span>}
            </button>
          )}
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-2">
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by title, number, officer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
            />
          </div>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
          >
            <option value="ALL">All Priorities</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Status Filter Pills */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs pb-1">
        {[
          { label: 'All Statuses', value: 'ALL' },
          { label: 'Pending', value: 'PENDING' },
          { label: 'In Progress', value: 'IN_PROGRESS' },
          { label: 'Submitted for Review', value: 'SUBMITTED_FOR_REVIEW' },
          { label: 'Revisions Required', value: 'REVISIONS_REQUIRED' },
          { label: 'Completed', value: 'COMPLETED' },
        ].map((pill) => (
          <button
            key={pill.value}
            type="button"
            onClick={() => setStatusFilter(pill.value)}
            className={`px-3 py-1 rounded-full text-[11px] font-medium transition-colors ${statusFilter === pill.value
                ? 'bg-slate-900 text-white font-semibold'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
          >
            {pill.label}
          </button>
        ))}
      </div>

      {/* Task Cards Grid */}
      {isLoading ? (
        <Card className="p-16 text-center text-xs text-slate-500">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-[#315C45]" />
          Loading tasks from database...
        </Card>
      ) : filteredTasks.length === 0 ? (
        <Card className="p-16 text-center space-y-3 border-dashed">
          <FileText className="w-10 h-10 mx-auto text-slate-300" />
          <h3 className="text-sm font-bold text-slate-700">No tasks found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {activeTab === 'my'
              ? 'You have not created any tasks yet, or no tasks match your filters. Click "Create Task" above to get started.'
              : 'There are currently no tasks awaiting review in this view.'}
          </p>
          {activeTab === 'my' && (
            <Button
              onClick={() => setIsCreateModalOpen(true)}
              size="sm"
              className="bg-[#315C45] text-white hover:bg-[#254936] text-xs mt-2"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              Create First Task
            </Button>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTasks.map((task) => {
            const isCreator =
              user?.id === task.created_by_id ||
              user?.email === task.created_by_email;
            const isOfficer =
              user?.id === task.reporting_officer_id ||
              user?.email === task.reporting_officer_email;
            const isAdmin = user?.role === 'SUPER_ADMIN';

            return (
              <Card
                key={task.id}
                className="p-5 flex flex-col justify-between hover:border-slate-300 transition-all hover:shadow-md relative bg-white"
              >
                <div>
                  {/* Card Top: Task Number, Priority, Status */}
                  <div className="flex items-start justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-bold border border-slate-200">
                        {task.task_number}
                      </span>
                      {getPriorityBadge(task.priority)}
                    </div>
                    {getStatusBadge(task.status)}
                  </div>

                  {/* Title & Description */}
                  <h3 className="text-sm font-bold text-slate-900 mb-1 line-clamp-2">
                    {task.title}
                  </h3>
                  <p className="text-xs text-slate-600 line-clamp-3 mb-3">
                    {task.description || 'No detailed instructions provided.'}
                  </p>

                  {/* Reporting Officer & Creator Metadata */}
                  <div className="space-y-1.5 py-2.5 my-2 border-y border-slate-100 text-[11px]">
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="text-slate-400 flex items-center gap-1">
                        <UserCheck className="w-3.5 h-3.5 text-[#315C45]" />
                        Officer:
                      </span>
                      <span className="font-semibold text-slate-800">
                        {task.reporting_officer_name || 'Assigned Officer'}
                      </span>
                    </div>

                    {activeTab !== 'my' && (
                      <div className="flex items-center justify-between text-slate-600">
                        <span className="text-slate-400">Created By:</span>
                        <span className="font-medium text-slate-700">
                          {task.created_by_name} ({task.created_by_code || 'EMP'})
                        </span>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-slate-600">
                      <span className="text-slate-400 flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        Due Date:
                      </span>
                      <span className="font-medium text-slate-700">
                        {task.due_date ? formatISTDate(task.due_date) : 'End of Month'}
                      </span>
                    </div>
                  </div>

                  {/* Callout if Submitted for Review */}
                  {task.status === 'SUBMITTED_FOR_REVIEW' && task.completion_note && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 mb-3 text-[11px] text-amber-900">
                      <div className="font-semibold flex items-center gap-1 mb-0.5">
                        <FileCheck2 className="w-3.5 h-3.5 text-amber-700" />
                        Submitted Work:
                      </div>
                      <p className="line-clamp-2 text-amber-800">{task.completion_note}</p>
                    </div>
                  )}

                  {/* Callout if Revisions Required */}
                  {task.status === 'REVISIONS_REQUIRED' && task.review_feedback && (
                    <div className="bg-rose-50 border border-rose-200 rounded-lg p-2.5 mb-3 text-[11px] text-rose-900">
                      <div className="font-semibold flex items-center gap-1 mb-0.5 text-rose-800">
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                        Revision Feedback:
                      </div>
                      <p className="line-clamp-2 text-rose-800">{task.review_feedback}</p>
                    </div>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div className="pt-3 border-t border-slate-100 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    {/* Discussion / Chat button */}
                    <button
                      type="button"
                      onClick={() => {
                        setActiveChatTask(task);
                        setDetailTab('chat');
                      }}
                      className="inline-flex items-center gap-1.5 text-xs text-slate-700 hover:text-[#315C45] font-semibold py-1 px-2 rounded-lg hover:bg-slate-50 transition-colors"
                    >
                      <MessageSquare className="w-3.5 h-3.5 text-[#315C45]" />
                      <span>Chat</span>
                      {task.message_count > 0 && (
                        <span className="bg-[#EAF0E9] text-[#254936] text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                          {task.message_count}
                        </span>
                      )}
                    </button>

                    {/* View Details */}
                    <button
                      type="button"
                      onClick={() => {
                        setActiveChatTask(task);
                        setDetailTab('details');
                      }}
                      className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-0.5"
                    >
                      Details <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Workflow Action Buttons */}
                  <div className="flex items-center gap-2">
                    {/* Employee Submit for Review */}
                    {(isCreator || isAdmin) &&
                      (task.status === 'PENDING' ||
                        task.status === 'IN_PROGRESS' ||
                        task.status === 'REVISIONS_REQUIRED') && (
                        <Button
                          size="sm"
                          onClick={() => handleOpenSubmit(task)}
                          className="w-full text-xs py-1.5 bg-amber-600 hover:bg-amber-700 text-white flex items-center justify-center gap-1.5"
                        >
                          <FileCheck2 className="w-3.5 h-3.5" />
                          {task.status === 'REVISIONS_REQUIRED' ? 'Resubmit Work' : 'Submit as Done'}
                        </Button>
                      )}

                    {/* Officer Review Action */}
                    {(isOfficer || isAdmin) && task.status === 'SUBMITTED_FOR_REVIEW' && (
                      <Button
                        size="sm"
                        onClick={() => handleOpenReview(task)}
                        className="w-full text-xs py-1.5 bg-[#315C45] hover:bg-[#254936] text-white flex items-center justify-center gap-1.5"
                      >
                        <Shield className="w-3.5 h-3.5" />
                        Review Submission
                      </Button>
                    )}

                    {/* Completed checkmark */}
                    {task.status === 'COMPLETED' && (
                      <div className="w-full py-1 text-center text-[11px] font-semibold text-emerald-700 bg-emerald-50 rounded-lg flex items-center justify-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Approved & Completed
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 1: Create New Task */}
      {/* ------------------------------------------------------------- */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-xl w-full p-6 animate-in fade-in-50 zoom-in-95 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div>
                <h3 className="text-base font-bold text-slate-900">Create New Employee Task</h3>
                <p className="text-xs text-slate-500">
                  Assign work deliverables and designate your reporting officer for formal review.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold px-2"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-4 mt-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Task Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Calibrate CNC Lathe #2 & Complete Batch #4010"
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Detailed Description *
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="Provide complete instructions, required tolerances, output quantities, and safety protocols..."
                  value={createDescription}
                  onChange={(e) => setCreateDescription(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Designated Reporting Officer *
                  </label>
                  <select
                    required
                    value={createOfficerId}
                    onChange={(e) => setCreateOfficerId(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                  >
                    {officers.map((off) => (
                      <option key={off.id} value={off.id}>
                        {off.name} ({off.designation || off.role})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Priority Level *
                  </label>
                  <select
                    value={createPriority}
                    onChange={(e) => setCreatePriority(e.target.value as TaskPriority)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Due Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={createDueDate}
                    onChange={(e) => setCreateDueDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Attachments / Reference Codes
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Drawing-R2, PO-991, JobSheet-A"
                    value={createAttachments}
                    onChange={(e) => setCreateAttachments(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-200">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isCreating}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isCreating}
                  className="bg-[#315C45] hover:bg-[#254936] text-white"
                >
                  {isCreating ? 'Creating Task...' : 'Create & Assign Task'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 2: "When Done" Submit for Review Workflow */}
      {/* ------------------------------------------------------------- */}
      {isSubmitModalOpen && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 animate-in fade-in-50 zoom-in-95 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Submit Work for Reporting Officer Review
                </h3>
                <span className="text-xs text-slate-500 font-mono">
                  {selectedTask.task_number} — {selectedTask.title}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsSubmitModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold px-2"
              >
                &times;
              </button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 my-3 text-xs text-amber-900 flex items-start gap-2">
              <Clock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Formal Verification Notice</p>
                <p className="text-[11px] text-amber-800 mt-0.5">
                  Submitting this task changes its status to{' '}
                  <span className="font-bold underline">Submitted for Review</span>. Your reporting officer (
                  <span className="font-semibold">{selectedTask.reporting_officer_name}</span>) will be notified to review and officially approve your work.
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmitForReview} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Completion Note & Accomplishments *
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="Detail the work accomplished, machine readings, inspection results, or items completed..."
                  value={completionNote}
                  onChange={(e) => setCompletionNote(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Supporting Evidence / Document Reference
                </label>
                <input
                  type="text"
                  placeholder="e.g. Batch Inspection Slip #781, Signed QC Certificate, Link to record"
                  value={completionEvidence}
                  onChange={(e) => setCompletionEvidence(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-200">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsSubmitModalOpen(false)}
                  disabled={isSubmittingWork}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmittingWork}
                  className="bg-amber-600 hover:bg-amber-700 text-white flex items-center gap-1.5"
                >
                  <FileCheck2 className="w-3.5 h-3.5" />
                  {isSubmittingWork ? 'Submitting...' : 'Submit to Officer for Review'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL 3: Reporting Officer Review Modal */}
      {/* ------------------------------------------------------------- */}
      {isReviewModalOpen && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 animate-in fade-in-50 zoom-in-95 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Reporting Officer Work Review
                </h3>
                <span className="text-xs text-slate-500 font-mono">
                  {selectedTask.task_number} — {selectedTask.title}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsReviewModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold px-2"
              >
                &times;
              </button>
            </div>

            {/* Submission Summary Preview */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 my-3 text-xs space-y-2">
              <div className="flex items-center justify-between text-slate-600">
                <span className="text-slate-400">Employee:</span>
                <span className="font-semibold text-slate-800">{selectedTask.created_by_name}</span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5">Completion Note:</span>
                <div className="bg-white p-2 rounded border border-slate-200 text-slate-800 font-medium">
                  {selectedTask.completion_note || 'No completion note recorded.'}
                </div>
              </div>
              {selectedTask.completion_evidence && (
                <div>
                  <span className="text-slate-400 block mb-0.5">Evidence Reference:</span>
                  <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 font-mono text-[11px]">
                    {selectedTask.completion_evidence}
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={handleReviewDecision} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-2">
                  Review Decision *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label
                    className={`flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${reviewDecision === 'APPROVED'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-900 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="APPROVED"
                      checked={reviewDecision === 'APPROVED'}
                      onChange={() => setReviewDecision('APPROVED')}
                      className="text-emerald-600 focus:ring-emerald-500"
                    />
                    <div>
                      <div className="font-bold flex items-center gap-1">
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        Approve Task
                      </div>
                      <span className="text-[10px] text-slate-500">Mark as Completed</span>
                    </div>
                  </label>

                  <label
                    className={`flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${reviewDecision === 'REVISIONS_REQUIRED'
                        ? 'border-rose-500 bg-rose-50 text-rose-900 ring-2 ring-rose-500/20'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="REVISIONS_REQUIRED"
                      checked={reviewDecision === 'REVISIONS_REQUIRED'}
                      onChange={() => setReviewDecision('REVISIONS_REQUIRED')}
                      className="text-rose-600 focus:ring-rose-500"
                    />
                    <div>
                      <div className="font-bold flex items-center gap-1">
                        <RotateCcw className="w-3.5 h-3.5 text-rose-600" />
                        Request Revisions
                      </div>
                      <span className="text-[10px] text-slate-500">Employee must update</span>
                    </div>
                  </label>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Officer Feedback Note {reviewDecision === 'REVISIONS_REQUIRED' && '*'}
                </label>
                <textarea
                  rows={3}
                  required={reviewDecision === 'REVISIONS_REQUIRED'}
                  placeholder={
                    reviewDecision === 'REVISIONS_REQUIRED'
                      ? 'Specify exactly what needs to be reworked or adjusted...'
                      : 'Optional approval remarks or commendation...'
                  }
                  value={reviewFeedback}
                  onChange={(e) => setReviewFeedback(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-200">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsReviewModalOpen(false)}
                  disabled={isReviewing}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isReviewing}
                  className={`text-white ${reviewDecision === 'APPROVED'
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : 'bg-rose-600 hover:bg-rose-700'
                    }`}
                >
                  {isReviewing
                    ? 'Saving...'
                    : reviewDecision === 'APPROVED'
                      ? 'Confirm Approval'
                      : 'Send Revision Request'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* DRAWER / MODAL: Task Details & Dedicated In-Task Discussion Chat */}
      {/* ------------------------------------------------------------- */}
      {activeChatTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full h-[85vh] flex flex-col animate-in fade-in-50 zoom-in-95 my-auto overflow-hidden">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-800">
                  {activeChatTask.task_number}
                </span>
                <h3 className="text-sm font-bold text-slate-900 line-clamp-1">
                  {activeChatTask.title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setActiveChatTask(null)}
                className="text-slate-400 hover:text-slate-700 text-xl font-bold px-2"
              >
                &times;
              </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center border-b border-slate-200 px-4 bg-white text-xs">
              <button
                type="button"
                onClick={() => setDetailTab('details')}
                className={`py-2.5 px-3 font-semibold border-b-2 transition-all ${detailTab === 'details'
                    ? 'border-[#315C45] text-[#315C45]'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
              >
                Task Details & Audit
              </button>
              <button
                type="button"
                onClick={() => setDetailTab('chat')}
                className={`py-2.5 px-3 font-semibold border-b-2 transition-all flex items-center gap-1.5 ${detailTab === 'chat'
                    ? 'border-[#315C45] text-[#315C45]'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Discussion Chat</span>
                {chatMessages.length > 0 && (
                  <span className="bg-[#EAF0E9] text-[#254936] text-[10px] px-1.5 py-0.2 rounded-full font-bold">
                    {chatMessages.length}
                  </span>
                )}
              </button>
            </div>

            {/* Tab 1: Task Details Content */}
            {detailTab === 'details' && (
              <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs text-slate-700">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="space-y-0.5">
                    <span className="text-[11px] text-slate-400">Current Status</span>
                    <div>{getStatusBadge(activeChatTask.status)}</div>
                  </div>
                  <div className="space-y-0.5 text-right">
                    <span className="text-[11px] text-slate-400">Priority</span>
                    <div>{getPriorityBadge(activeChatTask.priority)}</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-bold text-slate-900 mb-1">Description & Scope</h4>
                  <p className="bg-slate-50 p-3 rounded-lg border border-slate-200 whitespace-pre-wrap leading-relaxed">
                    {activeChatTask.description || 'No detailed instructions provided.'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <div>
                    <span className="text-[11px] text-slate-400 block">Created By</span>
                    <span className="font-semibold text-slate-800">{activeChatTask.created_by_name}</span>
                    <span className="text-[10px] text-slate-500 block">{activeChatTask.created_by_email}</span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400 block">Assigned Reporting Officer</span>
                    <span className="font-semibold text-slate-800">{activeChatTask.reporting_officer_name}</span>
                    <span className="text-[10px] text-slate-500 block">{activeChatTask.reporting_officer_email}</span>
                  </div>
                </div>

                {/* Submission Details */}
                {activeChatTask.completion_note && (
                  <div className="border border-amber-200 bg-amber-50 rounded-xl p-3 space-y-1">
                    <div className="font-bold text-amber-900 flex items-center justify-between">
                      <span className="flex items-center gap-1">
                        <FileCheck2 className="w-3.5 h-3.5 text-amber-700" />
                        Completion Submission
                      </span>
                      {activeChatTask.submitted_at && (
                        <span className="text-[10px] font-normal text-amber-700">
                          {formatISTDate(activeChatTask.submitted_at)}
                        </span>
                      )}
                    </div>
                    <p className="text-amber-800 mt-1 whitespace-pre-wrap">
                      {activeChatTask.completion_note}
                    </p>
                    {activeChatTask.completion_evidence && (
                      <p className="text-[11px] text-amber-700 font-mono mt-2 pt-1 border-t border-amber-200/60">
                        Evidence: {activeChatTask.completion_evidence}
                      </p>
                    )}
                  </div>
                )}

                {/* Review History */}
                {activeChatTask.review_feedback && (
                  <div className="border border-slate-200 bg-slate-50 rounded-xl p-3 space-y-1">
                    <div className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Reporting Officer Feedback</span>
                      {activeChatTask.reviewed_at && (
                        <span className="text-[10px] font-normal text-slate-500">
                          {formatISTDate(activeChatTask.reviewed_at)}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-700 mt-1 whitespace-pre-wrap">
                      {activeChatTask.review_feedback}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      Reviewed by: {activeChatTask.reviewed_by}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Dedicated Task Chat Content */}
            {detailTab === 'chat' && (
              <div className="flex-1 flex flex-col min-h-0 bg-slate-50/50">
                {/* Chat Participants Header Banner */}
                <div className="px-4 py-2 bg-slate-100 border-b border-slate-200 text-[11px] text-slate-600 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Shield className="w-3 h-3 text-[#315C45]" />
                    <span>
                      Private Channel: <strong className="text-slate-800">{activeChatTask.created_by_name}</strong> (Employee) &harr;{' '}
                      <strong className="text-slate-800">{activeChatTask.reporting_officer_name}</strong> (Officer) &amp; Super Admin
                    </span>
                  </div>
                  <span className="text-[10px] text-emerald-600 font-medium">Live sync active</span>
                </div>

                {/* Messages Thread Container */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {chatMessages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400 space-y-2">
                      <MessageSquare className="w-8 h-8 text-slate-300" />
                      <p className="text-xs font-semibold text-slate-600">No messages in this task conversation yet.</p>
                      <p className="text-[11px] text-slate-400 max-w-xs">
                        Use this dedicated channel to ask questions, share updates, or provide feedback directly with your reporting officer.
                      </p>
                    </div>
                  ) : (
                    chatMessages.map((msg) => {
                      const isMe = msg.sender_id === user?.id || msg.sender_email === user?.email;
                      const isSuperAdmin = msg.sender_role === 'SUPER_ADMIN';
                      const isOfficer = msg.sender_role === 'REPORTING_OFFICER';

                      return (
                        <div
                          key={msg.id}
                          className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                        >
                          <div className="flex items-center gap-1.5 mb-1 text-[10px] text-slate-400">
                            <span className="font-semibold text-slate-700">
                              {msg.sender_name}
                            </span>
                            {isSuperAdmin && (
                              <span className="px-1.5 py-0.2 rounded bg-purple-100 text-purple-800 font-bold text-[9px]">
                                Super Admin
                              </span>
                            )}
                            {isOfficer && (
                              <span className="px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-800 font-bold text-[9px]">
                                Reporting Officer
                              </span>
                            )}
                            {!isSuperAdmin && !isOfficer && (
                              <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 font-bold text-[9px]">
                                Employee
                              </span>
                            )}
                            <span>{formatISTDate(msg.created_at)}</span>
                          </div>

                          <div
                            className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs shadow-xs break-words whitespace-pre-wrap ${isMe
                                ? 'bg-[#315C45] text-white rounded-tr-xs'
                                : 'bg-white text-slate-800 border border-slate-200 rounded-tl-xs'
                              }`}
                          >
                            {msg.message}
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={chatBottomRef} />
                </div>

                {/* Message Input Composer */}
                <form
                  onSubmit={handleSendMessage}
                  className="p-3 bg-white border-t border-slate-200 flex items-center gap-2"
                >
                  <input
                    type="text"
                    placeholder="Type message to reporting officer and admin... (Enter to send)"
                    value={newMessageText}
                    onChange={(e) => setNewMessageText(e.target.value)}
                    disabled={isSendingMessage}
                    className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                  />
                  <Button
                    type="submit"
                    disabled={isSendingMessage || !newMessageText.trim()}
                    className="bg-[#315C45] hover:bg-[#254936] text-white px-4 h-9 flex items-center gap-1 text-xs"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Send
                  </Button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
