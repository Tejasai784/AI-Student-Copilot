import { CitationItem, AgentStepTrace } from '../types';

export interface StreamCallbacks {
  onStatus?: (stage: string, message: string, provider?: string, model?: string) => void;
  onToken?: (text: string) => void;
  onSources?: (sources: CitationItem[]) => void;
  onAgentStep?: (step: { agent: string; action: string }) => void;
  onProviderSwitch?: (fromProvider: string, toProvider: string, reason: string) => void;
  onDone?: (info: { conversationId: number; messageId: number; modelUsed: string }) => void;
  onError?: (err: Error) => void;
}

const API_BASE = ((import.meta as any).env?.VITE_API_URL || '').replace(/\/$/, '') + '/api/v1';

export function streamChat(
  params: {
    question: string;
    subjectId?: number;
    style?: string;
    conversationId?: number;
  },
  callbacks: StreamCallbacks,
  abortSignal?: AbortSignal
): Promise<void> {
  return new Promise(async (resolve, reject) => {
    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          question: params.question,
          subject_id: params.subjectId,
          style: params.style || 'Simple explanation',
          conversation_id: params.conversationId,
        }),
        signal: abortSignal,
      });

      if (!response.ok) {
        throw new Error(`Streaming failed with status: ${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported by browser.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // retain incomplete last line

        let currentEvent = 'message';
        let currentData = '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            // End of an SSE event chunk
            if (currentData) {
              try {
                const parsed = JSON.parse(currentData);
                handleEvent(currentEvent, parsed, callbacks);
              } catch {
                // non-json payload or keepalive
              }
            }
            currentEvent = 'message';
            currentData = '';
            continue;
          }

          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.replace('event:', '').trim();
          } else if (trimmed.startsWith('data:')) {
            currentData += trimmed.replace('data:', '').trim();
          }
        }
      }

      resolve();
    } catch (err: any) {
      if (err.name === 'AbortError') {
        resolve();
      } else {
        callbacks.onError?.(err);
        reject(err);
      }
    }
  });
}

function handleEvent(event: string, data: any, callbacks: StreamCallbacks) {
  switch (event) {
    case 'status':
      callbacks.onStatus?.(data.stage, data.message || '', data.provider, data.model);
      break;
    case 'token':
      if (data.text) {
        callbacks.onToken?.(data.text);
      }
      break;
    case 'source':
      if (data.sources) {
        callbacks.onSources?.(data.sources);
      }
      break;
    case 'agent_step':
      callbacks.onAgentStep?.(data);
      break;
    case 'provider_switch':
      callbacks.onProviderSwitch?.(
        data.from_provider || 'Gemini',
        data.to_provider || 'Offline',
        data.reason || 'Fallback'
      );
      break;
    case 'done':
      callbacks.onDone?.({
        conversationId: data.conversation_id,
        messageId: data.message_id,
        modelUsed: data.model_used,
      });
      break;
    case 'error':
      callbacks.onError?.(new Error(data.message || 'Stream error occurred.'));
      break;
  }
}
