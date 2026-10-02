import {
  StudentProfile,
  Subject,
  Goal,
  Task,
  Conversation,
  Message,
  DashboardSummary,
  ProviderTelemetry,
  CitationItem,
} from '../types';

const API_BASE = '/api/v1';

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

  // 2. Subjects
  async getSubjects(): Promise<Subject[]> {
    const res = await fetch(`${API_BASE}/subjects/`);
    return handleResponse<Subject[]>(res);
  },

  // 3. Goals & Tasks
  async getGoals(): Promise<Goal[]> {
    const res = await fetch(`${API_BASE}/goals/`);
    return handleResponse<Goal[]>(res);
  },

  async updateTaskStatus(taskId: number, status: string): Promise<Task> {
    const res = await fetch(`${API_BASE}/study-plan/tasks/${taskId}/status?status=${encodeURIComponent(status)}`, {
      method: 'PATCH',
    });
    return handleResponse<Task>(res);
  },

  // 4. Conversations & Messages
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

  // 5. Providers & Telemetry
  async getProvidersTelemetry(): Promise<ProviderTelemetry> {
    const res = await fetch(`${API_BASE}/providers/telemetry`);
    return handleResponse<ProviderTelemetry>(res);
  },
};
