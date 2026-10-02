export interface StudentProfile {
  id?: number;
  name: string;
  course: string;
  branch: string;
  year: string;
  semester: string;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  semester: string;
  description?: string;
  color?: string;
  topics_count?: number;
  completed_topics?: number;
  progress_percentage?: number;
}

export interface Task {
  id: number;
  goal_id?: number;
  title: string;
  description?: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED';
  scheduled_date?: string;
  priority?: number;
  effort_minutes?: number;
  subject_id?: number;
  agent_assigned?: string;
}

export interface Goal {
  id: number;
  title: string;
  objective: string;
  status: string;
  progress_percentage: number;
  deadline?: string;
  tasks_count: number;
  completed_tasks_count: number;
  tasks?: Task[];
}

export interface CitationItem {
  document_name: string;
  page_number: number;
  excerpt: string;
  chunk_id?: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent_name?: string;
  tool_calls_json?: string;
  citations_json?: string;
  created_at: string;
  citations?: CitationItem[];
}

export interface Conversation {
  id: number;
  title: string;
  subject_id?: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardSummary {
  student_name: string;
  course: string;
  year: string;
  semester: string;
  branch: string;
  total_subjects: number;
  total_topics: number;
  completed_topics: number;
  study_progress: number;
  total_materials: number;
  upcoming_exams: number;
  quiz_accuracy: number;
  weak_topics: Array<{ topic_name: string; failure_rate?: number; priority?: string }>;
  pending_tasks_today: number;
  total_attempts: number;
}

export interface AgentStepTrace {
  step_id: number;
  agent_name: string;
  action_description: string;
  stage: string;
  tool_used?: string;
  duration_ms?: number;
  details?: Record<string, any>;
  timestamp: string;
}

export interface ProviderTelemetry {
  gemini: {
    configured: boolean;
    model: string;
    connection: string;
    detail: string;
  };
  openai: {
    configured: boolean;
    model: string;
    connection: string;
  };
  active_provider: string;
}
