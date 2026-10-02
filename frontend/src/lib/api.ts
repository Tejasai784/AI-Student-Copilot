import {
  StudentProfile,
  StudentSettingsData,
  Subject,
  SyllabusTopic,
  DocumentItem,
  DocumentChunkItem,
  DocumentSearchResult,
  Goal,
  Task,
  Conversation,
  Message,
  DashboardSummary,
  ProviderTelemetry,
  CitationItem,
  QuizAttempt,
  StudyPlanItem,
  StudyTaskItem,
  PerformanceData,
  WeakTopic,
  KnowledgeMapData,
  ReadinessReport,
  MemoryItem,
  AgentRunItem,
  SystemDiagnosticsData,
} from '../types';

const API_BASE = ((import.meta as any).env?.VITE_API_URL || '').replace(/\/$/, '') + '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errJson.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(errMsg);
  }
  const json = await res.json();
  return json.data !== undefined ? json.data : json;
}

export const api = {
  // 1. Dashboard & Profile
  async getDashboard(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE}/students/dashboard`);
    return handleResponse<DashboardSummary>(res);
  },

  async getProfile(): Promise<StudentProfile> {
    const res = await fetch(`${API_BASE}/students/profile`);
    return handleResponse<StudentProfile>(res);
  },

  async updateProfile(profile: Partial<StudentProfile>): Promise<StudentProfile> {
    const res = await fetch(`${API_BASE}/students/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    return handleResponse<StudentProfile>(res);
  },

  async getSettings(): Promise<StudentSettingsData> {
    const res = await fetch(`${API_BASE}/students/settings`);
    return handleResponse<StudentSettingsData>(res);
  },

  async updateSettings(settings: Partial<StudentSettingsData>): Promise<StudentSettingsData> {
    const res = await fetch(`${API_BASE}/students/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    return handleResponse<StudentSettingsData>(res);
  },

  // 2. Subjects & Topics
  async getSubjects(): Promise<Subject[]> {
    const res = await fetch(`${API_BASE}/subjects`);
    return handleResponse<Subject[]>(res);
  },

  async getSubject(id: number): Promise<Subject> {
    const res = await fetch(`${API_BASE}/subjects/${id}`);
    return handleResponse<Subject>(res);
  },

  async createSubject(data: { name: string; code: string; semester: string; description?: string }): Promise<Subject> {
    const res = await fetch(`${API_BASE}/subjects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<Subject>(res);
  },

  async addTopic(subjectId: number, data: { unit_number: number; topic_name: string }): Promise<SyllabusTopic> {
    const res = await fetch(`${API_BASE}/subjects/${subjectId}/topics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<SyllabusTopic>(res);
  },

  async toggleTopic(subjectId: number, topicId: number): Promise<SyllabusTopic> {
    const res = await fetch(`${API_BASE}/subjects/${subjectId}/topics/${topicId}/toggle`, {
      method: 'PATCH',
    });
    return handleResponse<SyllabusTopic>(res);
  },

  // 3. Documents & Knowledge Retrieval
  async getDocuments(subjectId?: number): Promise<DocumentItem[]> {
    const url = subjectId ? `${API_BASE}/documents?subject_id=${subjectId}` : `${API_BASE}/documents`;
    const res = await fetch(url);
    return handleResponse<DocumentItem[]>(res);
  },

  async getDocument(id: number): Promise<DocumentItem> {
    const res = await fetch(`${API_BASE}/documents/${id}`);
    return handleResponse<DocumentItem>(res);
  },

  async getDocumentChunks(id: number): Promise<DocumentChunkItem[]> {
    const res = await fetch(`${API_BASE}/documents/${id}/chunks`);
    return handleResponse<DocumentChunkItem[]>(res);
  },

  async uploadDocument(formData: FormData): Promise<DocumentItem> {
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DocumentItem>(res);
  },

  async deleteDocument(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/documents/${id}`, {
      method: 'DELETE',
    });
    await handleResponse<null>(res);
  },

  async searchDocuments(query: string, subjectId?: number): Promise<DocumentSearchResult> {
    let url = `${API_BASE}/documents/search?query=${encodeURIComponent(query)}&top_k=6`;
    if (subjectId) url += `&subject_id=${subjectId}`;
    const res = await fetch(url);
    return handleResponse<DocumentSearchResult>(res);
  },

  // 4. Goals & Tasks
  async getGoals(): Promise<Goal[]> {
    const res = await fetch(`${API_BASE}/goals`);
    return handleResponse<Goal[]>(res);
  },

  async getGoal(id: number): Promise<Goal> {
    const res = await fetch(`${API_BASE}/goals/${id}`);
    return handleResponse<Goal>(res);
  },

  async createGoalFromPrompt(prompt: string, subjectId?: number): Promise<Goal> {
    const res = await fetch(`${API_BASE}/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, subject_id: subjectId }),
    });
    return handleResponse<Goal>(res);
  },

  async toggleGoalTask(taskId: number): Promise<Task> {
    const res = await fetch(`${API_BASE}/goals/tasks/${taskId}/toggle`, {
      method: 'PATCH',
    });
    return handleResponse<Task>(res);
  },

  // 5. Adaptive Study Planner
  async getCurrentStudyPlan(): Promise<StudyPlanItem | null> {
    const res = await fetch(`${API_BASE}/study-plan`);
    return handleResponse<StudyPlanItem | null>(res);
  },

  async generateStudyPlan(data: { horizon?: string; exam_focus?: string; daily_minutes?: number }): Promise<StudyPlanItem> {
    const res = await fetch(`${API_BASE}/study-plan/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<StudyPlanItem>(res);
  },

  async toggleStudyTask(taskId: number): Promise<StudyTaskItem> {
    const res = await fetch(`${API_BASE}/study-plan/tasks/${taskId}/toggle`, {
      method: 'PATCH',
    });
    return handleResponse<StudyTaskItem>(res);
  },

  // 6. Quizzes & Mock Exams
  async generateQuiz(data: {
    subject_id?: number;
    unit_number?: number;
    topic_name?: string;
    num_questions: number;
    difficulty: string;
    time_limit_seconds?: number;
    exam_kind: string;
  }): Promise<QuizAttempt> {
    const res = await fetch(`${API_BASE}/quizzes/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<QuizAttempt>(res);
  },

  async getQuizAttempt(attemptId: number): Promise<QuizAttempt> {
    const res = await fetch(`${API_BASE}/quizzes/${attemptId}`);
    return handleResponse<QuizAttempt>(res);
  },

  async recordQuizAnswer(attemptId: number, questionId: number, userAnswer: string): Promise<void> {
    const res = await fetch(`${API_BASE}/quizzes/${attemptId}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: questionId, user_answer: userAnswer }),
    });
    await handleResponse<null>(res);
  },

  async submitQuiz(attemptId: number, answers?: Record<string, string>): Promise<QuizAttempt> {
    const res = await fetch(`${API_BASE}/quizzes/${attemptId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers: answers || {} }),
    });
    return handleResponse<QuizAttempt>(res);
  },

  async getQuizHistory(subjectId?: number): Promise<QuizAttempt[]> {
    const url = subjectId ? `${API_BASE}/quizzes/history/list?subject_id=${subjectId}` : `${API_BASE}/quizzes/history/list`;
    const res = await fetch(url);
    return handleResponse<QuizAttempt[]>(res);
  },

  // 7. Analytics & Weak Topics
  async getPerformance(): Promise<PerformanceData> {
    const res = await fetch(`${API_BASE}/analytics/performance`);
    return handleResponse<PerformanceData>(res);
  },

  async getWeakTopics(): Promise<WeakTopic[]> {
    const res = await fetch(`${API_BASE}/analytics/weak-topics`);
    return handleResponse<WeakTopic[]>(res);
  },

  async getKnowledgeMap(): Promise<KnowledgeMapData> {
    const res = await fetch(`${API_BASE}/analytics/knowledge-map`);
    return handleResponse<KnowledgeMapData>(res);
  },

  // 8. Readiness Reports
  async getExamReadiness(subjectId?: number): Promise<ReadinessReport> {
    const url = subjectId ? `${API_BASE}/reports/exam-readiness?subject_id=${subjectId}` : `${API_BASE}/reports/exam-readiness`;
    const res = await fetch(url);
    return handleResponse<ReadinessReport>(res);
  },

  getReportDownloadUrl(subjectId?: number, format: 'markdown' | 'html' = 'markdown'): string {
    const base = `${API_BASE}/reports/download?format=${format}`;
    return subjectId ? `${base}&subject_id=${subjectId}` : base;
  },

  // 9. Long-term Personalization & Memory
  async getMemories(type?: string): Promise<MemoryItem[]> {
    const url = type ? `${API_BASE}/memory?memory_type=${encodeURIComponent(type)}` : `${API_BASE}/memory`;
    const res = await fetch(url);
    return handleResponse<MemoryItem[]>(res);
  },

  async addMemory(data: { key: string; value: string; memory_type: string; confidence?: number; importance?: number }): Promise<MemoryItem> {
    const res = await fetch(`${API_BASE}/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<MemoryItem>(res);
  },

  async deleteMemory(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/memory/${id}`, {
      method: 'DELETE',
    });
    await handleResponse<null>(res);
  },

  // 10. Multi-Agent Orchestration & Traces
  async getAgentRuns(limit: number = 20): Promise<AgentRunItem[]> {
    const res = await fetch(`${API_BASE}/agents/runs?limit=${limit}`);
    return handleResponse<AgentRunItem[]>(res);
  },

  async getAgentRun(id: number): Promise<AgentRunItem> {
    const res = await fetch(`${API_BASE}/agents/runs/${id}`);
    return handleResponse<AgentRunItem>(res);
  },

  async orchestrateQuery(query: string, subjectId?: number): Promise<any> {
    const res = await fetch(`${API_BASE}/agents/orchestrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, subject_id: subjectId }),
    });
    return handleResponse<any>(res);
  },

  async runAutonomousPrep(goalPrompt: string, subjectId?: number): Promise<any> {
    const res = await fetch(`${API_BASE}/agents/autonomous/prepare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal_prompt: goalPrompt, subject_id: subjectId }),
    });
    return handleResponse<any>(res);
  },

  // 11. Diagnostics & Health
  async getSystemDiagnostics(): Promise<SystemDiagnosticsData> {
    const res = await fetch(`${API_BASE}/diagnostics/system`);
    return handleResponse<SystemDiagnosticsData>(res);
  },

  async getHealthDiagnostics(): Promise<{ status: string; app_name: string; version: string; database_connected: boolean; vector_store_indexed_chunks: number }> {
    const res = await fetch(`${API_BASE}/diagnostics/health`);
    return handleResponse<any>(res);
  },

  async getProvidersTelemetry(): Promise<ProviderTelemetry> {
    const res = await fetch(`${API_BASE}/providers/telemetry`);
    return handleResponse<ProviderTelemetry>(res);
  },

  // 12. Conversations & Messages
  async getConversations(): Promise<Conversation[]> {
    const res = await fetch(`${API_BASE}/chat/conversations`);
    return handleResponse<Conversation[]>(res);
  },

  async createConversation(title?: string, subjectId?: number): Promise<Conversation> {
    const res = await fetch(`${API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title || 'New Conversation', subject_id: subjectId }),
    });
    return handleResponse<Conversation>(res);
  },

  async updateConversationTitle(convId: number, title: string): Promise<Conversation> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    return handleResponse<Conversation>(res);
  },

  async deleteConversation(convId: number): Promise<{ deleted: boolean }> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
      method: 'DELETE',
    });
    return handleResponse<{ deleted: boolean }>(res);
  },

  async getMessages(convId: number): Promise<Message[]> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}/messages`);
    const msgs = await handleResponse<Message[]>(res);
    return msgs.map((m) => {
      let citations: CitationItem[] = [];
      if (m.citations_json) {
        try {
          citations = JSON.parse(m.citations_json);
        } catch {
          // ignore
        }
      }
      return { ...m, citations };
    });
  },

  async askQuestion(data: {
    question: string;
    conversation_id?: number;
    subject_id?: number;
    style?: string;
  }): Promise<{
    answer: string;
    citations: CitationItem[];
    confidence_score: number;
    provider_used: string;
    model_used: string;
    is_fallback: boolean;
    conversation_id: number;
  }> {
    const res = await fetch(`${API_BASE}/chat/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
};
