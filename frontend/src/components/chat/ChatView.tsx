import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Square,
  Plus,
  Trash2,
  Edit2,
  FileText,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  BookOpen,
  Check,
  AlertCircle,
  Clock,
  Activity,
  Layers,
} from 'lucide-react';
import { api } from '../../lib/api';
import { streamChat } from '../../lib/streaming';
import { Conversation, Message, CitationItem, Subject } from '../../types';

export const ChatView: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [style, setStyle] = useState('Simple explanation');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(undefined);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStage, setStreamStage] = useState<string>('');
  const [streamTokens, setStreamTokens] = useState<string>('');
  const [streamSources, setStreamSources] = useState<CitationItem[]>([]);
  const [streamProviderNotice, setStreamProviderNotice] = useState<string | null>(null);
  const [expandedTraceId, setExpandedTraceId] = useState<number | null>(null);

  // Citations Drawer
  const [selectedCitations, setSelectedCitations] = useState<CitationItem[] | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations and subjects on mount
  useEffect(() => {
    loadConversations();
    api.getSubjects().then(setSubjects).catch(() => []);
  }, []);

  const loadConversations = async () => {
    try {
      const list = await api.getConversations();
      setConversations(list);
      if (list.length > 0 && !activeConvId) {
        selectConversation(list[0].id);
      }
    } catch {
      // ignore
    }
  };

  const selectConversation = async (id: number) => {
    setActiveConvId(id);
    try {
      const history = await api.getMessages(id);
      setMessages(history);
      setStreamTokens('');
      setStreamSources([]);
      setStreamProviderNotice(null);
    } catch {
      setMessages([]);
    }
  };

  const createNewChat = async () => {
    try {
      const newConv = await api.createConversation('New Academic Chat', selectedSubjectId);
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setStreamTokens('');
    } catch (err) {
      console.error('Could not create conversation:', err);
    }
  };

  const deleteCurrentChat = async (id: number) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (remaining.length > 0) {
        selectConversation(remaining[0].id);
      } else {
        setActiveConvId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to delete chat:', err);
    }
  };

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamTokens]);

  const handleSend = async () => {
    const q = inputQuestion.trim();
    if (!q || isStreaming) return;

    setInputQuestion('');
    setIsStreaming(true);
    setStreamTokens('');
    setStreamSources([]);
    setStreamStage('Initializing tutor...');
    setStreamProviderNotice(null);

    // Create optimistic user message
    const tempUserMsg: Message = {
      id: Date.now(),
      conversation_id: activeConvId || 0,
      role: 'user',
      content: q,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;

    let accumulatedTokens = '';
    let accumulatedSources: CitationItem[] = [];

    try {
      await streamChat(
        {
          question: q,
          subjectId: selectedSubjectId,
          style: style,
          conversationId: activeConvId || undefined,
        },
        {
          onStatus: (stage, msg, provider, model) => {
            setStreamStage(msg || `Stage: ${stage}`);
          },
          onSources: (sources) => {
            accumulatedSources = sources;
            setStreamSources(sources);
          },
          onToken: (text) => {
            accumulatedTokens += text;
            setStreamTokens(accumulatedTokens);
          },
          onProviderSwitch: (fromP, toP, reason) => {
            setStreamProviderNotice(`Model adjusted: switched from ${fromP} to ${toP} (${reason})`);
            accumulatedTokens = ''; // Reset partial text per Amendment 4
            setStreamTokens('');
          },
          onDone: (info) => {
            if (!activeConvId) {
              setActiveConvId(info.conversationId);
              loadConversations();
            }
            // Add permanent assistant message
            const assistantMsg: Message = {
              id: info.messageId || Date.now(),
              conversation_id: info.conversationId,
              role: 'assistant',
              content: accumulatedTokens,
              agent_name: info.modelUsed,
              created_at: new Date().toISOString(),
              citations: accumulatedSources,
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamTokens('');
          },
          onError: async (err) => {
            console.error('Stream error, attempting direct chat API fallback:', err);
            try {
              setStreamStage('Contacting academic tutor directly...');
              const directResp = await api.askQuestion({
                question: q,
                subject_id: selectedSubjectId,
                style: style,
                conversation_id: activeConvId || undefined,
              });
              if (!activeConvId) {
                setActiveConvId(directResp.conversation_id);
                loadConversations();
              }
              const assistantMsg: Message = {
                id: Date.now(),
                conversation_id: directResp.conversation_id,
                role: 'assistant',
                content: directResp.answer,
                agent_name: directResp.model_used,
                created_at: new Date().toISOString(),
                citations: directResp.citations || [],
              };
              setMessages((prev) => [...prev, assistantMsg]);
              setStreamTokens('');
            } catch (fallbackErr: any) {
              console.error('Direct chat API also failed:', fallbackErr);
            }
          },
        },
        abortCtrl.signal
      );
    } catch {
      // handled in callbacks
    } finally {
      setIsStreaming(false);
      setStreamStage('');
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setStreamStage('');
    }
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-canvas">
      {/* 1. Conversations Sidebar Drawer (Desktop) */}
      <div className="hidden lg:flex flex-col w-64 border-r border-border bg-surface p-3 space-y-3">
        <button
          onClick={createNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-all"
        >
          <Plus size={15} />
          <span>New Study Chat</span>
        </button>

        <div className="text-[11px] font-semibold tracking-wider text-ink-muted/80 uppercase px-2 pt-2">
          Recent Discussions
        </div>

        <div className="flex-1 overflow-y-auto space-y-1">
          {conversations.map((c) => (
            <div
              key={c.id}
              onClick={() => selectConversation(c.id)}
              className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-colors ${
                activeConvId === c.id
                  ? 'bg-focus/15 text-focus font-semibold'
                  : 'text-ink-muted hover:bg-surface-muted hover:text-ink'
              }`}
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <FileText size={14} className="flex-shrink-0" />
                <span className="truncate">{c.title || 'Conversation'}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteCurrentChat(c.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-weak transition-opacity"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-xs text-ink-muted text-center py-6">No saved chats yet.</p>
          )}
        </div>
      </div>

      {/* 2. Main Chat Reading Column (~720px) */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Control Bar */}
        <div className="h-12 border-b border-border bg-surface px-4 flex items-center justify-between gap-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-ink-muted">Subject:</span>
            <select
              value={selectedSubjectId || ''}
              onChange={(e) => setSelectedSubjectId(e.target.value ? Number(e.target.value) : undefined)}
              className="text-xs rounded-md bg-canvas border border-border px-2.5 py-1 text-ink focus:outline-none focus:border-focus"
            >
              <option value="">All Subjects (Cross-Disciplinary)</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-ink-muted">Mode:</span>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="text-xs rounded-md bg-canvas border border-border px-2.5 py-1 text-ink focus:outline-none focus:border-focus"
            >
              <option value="Simple explanation">Simple explanation</option>
              <option value="Detailed explanation">Detailed explanation</option>
              <option value="2-mark answer">2-Mark Exam Answer</option>
              <option value="5-mark answer">5-Mark Exam Answer</option>
              <option value="10-mark answer">10-Mark Exam Answer</option>
              <option value="With examples">With Examples</option>
            </select>
          </div>
        </div>

        {/* Messages Stream Column (centered 720px) */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="max-w-reading mx-auto space-y-6">
            {messages.length === 0 && !isStreaming && (
              <div className="text-center py-16 space-y-4">
                <div className="h-12 w-12 rounded-2xl bg-focus/10 text-focus flex items-center justify-center mx-auto shadow-sm">
                  <Sparkles size={24} />
                </div>
                <h3 className="font-heading font-bold text-xl text-ink">
                  Ask your AI Academic Tutor
                </h3>
                <p className="text-xs md:text-sm text-ink-muted max-w-md mx-auto">
                  Ask conceptual questions, request exam answers with 5-mark structure, or clarify difficult textbook algorithms. All answers are grounded in your uploaded study material.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                  {[
                    'Explain PN junction diode for 5 marks',
                    'How does Quicksort compare to Mergesort?',
                    'Explain BCNF vs 3NF with an example',
                  ].map((preset, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInputQuestion(preset)}
                      className="px-3 py-1.5 rounded-full bg-surface border border-border hover:border-focus/40 text-xs text-ink-muted hover:text-ink transition-colors"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => {
              const isUser = m.role === 'user';
              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  {isUser ? (
                    /* Student Question Bubble */
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-focus/10 text-ink border border-focus/20 px-4 py-3 text-sm leading-relaxed shadow-sm">
                      {m.content}
                    </div>
                  ) : (
                    /* AI Assistant Response — Full-width Prose per §7A */
                    <div className="w-full space-y-3 pt-2">
                      <div className="flex items-center gap-2 text-xs text-ink-muted font-medium pb-1 border-b border-border/40">
                        <span className="font-heading font-semibold text-focus">AI Tutor</span>
                        <span>·</span>
                        <span className="font-mono text-[11px]">{m.agent_name || 'Gemini 2.0 Flash'}</span>
                        {m.citations && m.citations.length > 0 && (
                          <button
                            onClick={() => setSelectedCitations(m.citations || [])}
                            className="ml-auto text-xs text-focus hover:underline flex items-center gap-1 font-semibold"
                          >
                            <BookOpen size={13} />
                            <span>{m.citations.length} Grounded Sources</span>
                          </button>
                        )}
                      </div>

                      {/* Main Prose Content */}
                      <div className="prose dark:prose-invert max-w-none text-ink text-sm leading-relaxed space-y-2 whitespace-pre-wrap font-sans">
                        {m.content}
                      </div>

                      {/* Citation Pill Chips */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-2">
                          <span className="text-[11px] font-semibold text-ink-muted mr-1">Cited:</span>
                          {m.citations.map((c, i) => (
                            <button
                              key={i}
                              onClick={() => setSelectedCitations([c])}
                              className="px-2 py-0.5 rounded-full bg-surface-muted border border-border text-[11px] font-mono text-ink-muted hover:text-focus hover:border-focus/40 flex items-center gap-1 transition-colors"
                            >
                              <span>[{i + 1}]</span>
                              <span className="truncate max-w-[120px]">{c.document_name}</span>
                              <span className="text-[10px] text-ink-muted/80">p.{c.page_number}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Live Streaming Response Block */}
            {isStreaming && (
              <div className="w-full space-y-3 pt-2">
                <div className="flex items-center gap-2 text-xs text-ink-muted font-medium pb-1 border-b border-border/40">
                  <span className="h-2 w-2 rounded-full bg-focus animate-pulse" />
                  <span className="font-heading font-semibold text-focus">AI Tutor Streaming</span>
                  {streamStage && (
                    <span className="text-[11px] text-ink-muted italic">· {streamStage}</span>
                  )}
                </div>

                {streamProviderNotice && (
                  <div className="p-2.5 rounded-lg bg-spark/10 border border-spark/30 text-xs text-spark flex items-center gap-2">
                    <AlertCircle size={15} className="flex-shrink-0" />
                    <span>{streamProviderNotice}</span>
                  </div>
                )}

                <div className="prose dark:prose-invert max-w-none text-ink text-sm leading-relaxed space-y-2 whitespace-pre-wrap font-sans">
                  {streamTokens || 'Synthesizing response from retrieved materials...'}
                </div>

                {streamSources.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-2">
                    <span className="text-[11px] font-semibold text-ink-muted mr-1">Retrieved Sources:</span>
                    {streamSources.map((s, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-full bg-surface-muted border border-border text-[11px] font-mono text-ink-muted"
                      >
                        [{idx + 1}] {s.document_name} (p.{s.page_number})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 3. Floating Bottom Composer */}
        <div className="border-t border-border bg-surface p-3 md:p-4">
          <div className="max-w-reading mx-auto">
            <div className="relative flex items-center rounded-xl bg-canvas border border-border focus-within:border-focus focus-within:ring-1 focus-within:ring-focus transition-all shadow-sm">
              <textarea
                value={inputQuestion}
                onChange={(e) => setInputQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={1}
                placeholder="Ask a study question, request an exam answer, or cite material..."
                className="w-full py-3 pl-4 pr-24 bg-transparent text-sm text-ink placeholder:text-ink-muted/70 focus:outline-none resize-none font-sans"
              />

              <div className="absolute right-2 flex items-center gap-1.5">
                {isStreaming ? (
                  <button
                    onClick={handleStop}
                    className="p-2 rounded-lg bg-weak hover:bg-weak/90 text-white transition-colors"
                    title="Stop generation"
                  >
                    <Square size={16} />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!inputQuestion.trim()}
                    className="p-2 rounded-lg bg-focus hover:bg-focus-hover disabled:opacity-40 disabled:hover:bg-focus text-white transition-colors"
                    title="Send message"
                  >
                    <Send size={16} />
                  </button>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between text-[11px] text-ink-muted mt-2 px-1">
              <span>Press <kbd className="font-mono bg-surface border px-1 rounded">Enter</kbd> to send, <kbd className="font-mono bg-surface border px-1 rounded">Shift+Enter</kbd> for new line</span>
              <span>Grounded on course documents</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Slide-out Sources Drawer (when citation chip clicked) */}
      {selectedCitations && (
        <div className="fixed inset-y-0 right-0 w-80 md:w-96 bg-surface border-l border-border shadow-2xl z-50 p-6 flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <BookOpen size={18} className="text-focus" />
              <h3 className="font-heading font-bold text-base text-ink">Grounded Sources</h3>
            </div>
            <button
              onClick={() => setSelectedCitations(null)}
              className="p-1 rounded text-ink-muted hover:text-ink"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-4 space-y-4">
            {selectedCitations.map((c, i) => (
              <div key={i} className="p-3.5 rounded-xl bg-canvas border border-border space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-ink truncate max-w-[180px]">{c.document_name}</span>
                  <span className="font-mono text-focus font-bold">Page {c.page_number}</span>
                </div>
                <blockquote className="text-xs text-ink-muted italic border-l-2 border-focus/40 pl-2 leading-relaxed">
                  "{c.excerpt}"
                </blockquote>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
