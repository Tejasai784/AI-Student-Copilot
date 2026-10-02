export interface StudentProfile {
  id?: number;
  name: string;
  course: string;
  branch: string;
  year: string;
  semester: string;
}

export interface StudentSettingsData {
  preferred_provider?: string;
  default_answer_style?: string;
  default_difficulty?: string;
  preferred_session_minutes?: number;
  weekly_study_hours?: number;
  theme?: string;
}

export interface SyllabusTopic {
  id: number;
  subject_id?: number;
  unit_number: number;
  topic_name: string;
  is_completed: boolean;
  difficulty?: string;
  estimated_hours?: number;
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
  topics?: SyllabusTopic[];
  documents_count?: number;
}

export interface DocumentItem {
  id: number;
  filename: string;
  original_filename?: string;
  file_size?: number;
  size_kb?: number;
  file_type?: string;
  document_type?: string;
  status: 'UPLOADING' | 'PROCESSING' | 'INDEXING' | 'READY' | 'FAILED';
  total_pages: number;
  total_chunks: number;
  pages?: number;
  chunks?: number;
  subject_id: number;
  error_message?: string;
  created_at: string;
}

export interface DocumentChunkItem {
  id: number;
  document_id: number;
  chunk_index: number;
  page_number: number;
  content: string;
  token_count?: number;
  metadata_json?: string;
}

export interface DocumentSearchResult {
  query: string;
  total_results: number;
  chunks: Array<{
    id: number;
    document_id: number;
    document_name: string;
    page_number: number;
    content: string;
    similarity_score: number;
  }>;
  citations: Array<{
    document_name: string;
    page_number: number;
    excerpt: string;
    chunk_id?: string;
  }>;
  user_id?: number;
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
  created_at?: string;
}

export interface CitationItem {
  document_name: string;
  page_number: number;
  excerpt: string;
  chunk_id?: string;
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

export interface QuizQuestion {
  id: number;
  order_index: number;
  question_type: string;
  question_text: string;
  options?: string[];
  max_marks: number;
  difficulty: string;
  topic_name?: string;
  explanation?: string | null;
  correct_answer?: string | null;
}

export interface QuizAnswer {
  question_id: number;
  user_answer: string;
  is_correct: boolean;
  score: number;
  max_marks: number;
  explanation?: string;
  model_answer?: string;
  improvement_suggestions?: string;
}

export interface QuizAttempt {
  id: number;
  subject_id?: number;
  unit_number?: number;
  topic_name?: string;
  exam_kind: string;
  status: string;
  total_marks: number;
  user_marks: number;
  percentage: number;
  questions_count: number;
  time_spent_seconds?: number;
  time_limit_minutes?: number;
  created_at: string;
  questions?: QuizQuestion[];
  answers?: QuizAnswer[];
}

export interface StudyTaskItem {
  id: number;
  plan_id?: number;
  subject_id?: number;
  topic_name: string;
  task_type: string;
  title: string;
  scheduled_date: string;
  duration_minutes: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
  priority: number;
}

export interface StudyPlanItem {
  id: number;
  title: string;
  horizon: string;
  status: string;
  exam_focus?: string;
  notes?: string;
  tasks: StudyTaskItem[];
  created_at: string;
}

export interface PerformanceData {
  total_exams: number;
  average_percentage: number;
  total_questions_answered: number;
  accuracy_rate: number;
  subject_breakdown?: Array<{
    subject_id: number;
    subject_name: string;
    attempts: number;
    avg_score: number;
  }>;
  daily_trend?: Array<{
    date: string;
    score: number;
    exams_count: number;
  }>;
}

export interface WeakTopic {
  topic_name: string;
  subject_name?: string;
  subject_id?: number;
  failure_rate: number;
  attempts_count: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_action?: string;
}

export interface KnowledgeMapData {
  nodes?: Array<{ id: string; name: string; type: string; mastery: number }>;
  links?: Array<{ source: string; target: string; relationship: string }>;
  mastery_percentage?: number;
  subjects?: Array<{
    id: number;
    name: string;
    mastery: number;
    topics: Array<{ name: string; mastery: number }>;
  }>;
}

export interface ReadinessReport {
  student_name: string;
  subject_name: string;
  overall_readiness_score: number;
  strengths?: string[];
  weaknesses?: string[];
  recommendations?: string[];
  markdown_report: string;
  html_report?: string;
  generated_at?: string;
}

export interface MemoryItem {
  id: number;
  key: string;
  value: string;
  memory_type: string;
  confidence: number;
  importance: number;
  created_at: string;
}

export interface ToolCallItem {
  id: number;
  tool_name: string;
  status: string;
  execution_time_ms: number;
  tool_input?: string;
  tool_output?: string;
  created_at?: string;
}

export interface AgentRunItem {
  id: number;
  agent_name: string;
  input_query: string;
  status: string;
  output_preview?: string;
  output_result?: string;
  tool_calls_count?: number;
  started_at?: string;
  finished_at?: string;
  plan_json?: string;
  execution_trace_json?: string;
  error_message?: string;
  tool_calls?: ToolCallItem[];
}

export interface SystemDiagnosticsData {
  documents_count: number;
  subjects_count: number;
  document_chunks_count: number;
  vector_store_count: number;
  upload_storage_bytes: number;
  upload_storage_mb: number;
  database_url_masked: string;
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
