import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Sparkles,
  Terminal,
  Clock,
  CheckCircle,
  AlertCircle,
  Play,
  RotateCcw,
  Cpu,
  ChevronRight,
} from 'lucide-react';
import { api } from '../../lib/api';
import { AgentRunItem } from '../../types';

export const AgentsView: React.FC = () => {
  const [runs, setRuns] = useState<AgentRunItem[]>([]);
  const [selectedRun, setSelectedRun] = useState<AgentRunItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Live test orchestrator
  const [orchestratorQuery, setOrchestratorQuery] = useState('');
  const [runningOrchestration, setRunningOrchestration] = useState(false);
  const [orchestrationResult, setOrchestrationResult] = useState<any | null>(null);

  const loadRuns = async () => {
    try {
      setLoading(true);
      const data = await api.getAgentRuns(30);
      setRuns(data);
      if (data.length > 0 && !selectedRun) {
        handleInspectRun(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load agent runs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleInspectRun = async (id: number) => {
    try {
      setLoadingDetails(true);
      const details = await api.getAgentRun(id);
      setSelectedRun(details);
    } catch (err: any) {
      alert(`Could not load run: ${err.message}`);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleRunOrchestration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orchestratorQuery.trim()) return;

    try {
      setRunningOrchestration(true);
      const res = await api.orchestrateQuery(orchestratorQuery.trim());
      setOrchestrationResult(res);
      await loadRuns();
      if (res.agent_run_id) {
        await handleInspectRun(res.agent_run_id);
      }
    } catch (err: any) {
      alert(`Orchestration failed: ${err.message}`);
    } finally {
      setRunningOrchestration(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Multi-Agent Orchestrator & Execution Traces
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Observe autonomous specialist agent state transitions, tool invocations, and self-evaluation scorecards.
          </p>
        </div>
      </div>

      {/* Query Orchestrator Bar */}
      <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4 max-w-5xl mx-auto">
        <div className="flex items-center gap-2 text-ink">
          <Cpu size={18} className="text-focus" />
          <h2 className="font-heading font-bold text-sm">Execute Live Agent Orchestration</h2>
        </div>

        <form onSubmit={handleRunOrchestration} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={orchestratorQuery}
            onChange={(e) => setOrchestratorQuery(e.target.value)}
            placeholder="e.g. 'Plan my preparation for Distributed Systems Unit 2 and test me with a hard question'..."
            className="flex-1 px-4 py-2.5 rounded-xl border border-border bg-canvas text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:border-focus"
          />

          <button
            type="submit"
            disabled={runningOrchestration || !orchestratorQuery.trim()}
            className="px-5 py-2.5 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {runningOrchestration ? (
              <span>Orchestrating...</span>
            ) : (
              <>
                <Play size={14} />
                <span>Dispatch Agents</span>
              </>
            )}
          </button>
        </form>

        {orchestrationResult?.evaluation && (
          <div className="p-3 rounded-xl bg-canvas border border-border text-xs flex items-center justify-between">
            <span className="text-ink-muted font-medium">
              Self-Evaluation Score: {(orchestrationResult.evaluation.overall_score * 100).toFixed(0)}%
            </span>
            <span className="text-good-leaf font-semibold">
              Feedback: {orchestrationResult.evaluation.feedback}
            </span>
          </div>
        )}
      </div>

      {/* Two Column Layout: Past Runs vs Inspected Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {/* Left: Past Runs */}
        <div className="lg:col-span-1 space-y-3">
          <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider block px-1">
            Execution Logs ({runs.length})
          </span>

          {loading ? (
            <div className="py-12 text-center text-xs text-ink-muted">Loading agent runs...</div>
          ) : runs.length === 0 ? (
            <div className="bg-surface border border-border rounded-xl p-8 text-center text-xs text-ink-muted">
              No agent runs logged yet. Execute a query above to initiate a run!
            </div>
          ) : (
            <div className="space-y-2.5">
              {runs.map((r) => {
                const isSelected = selectedRun?.id === r.id;
                return (
                  <button
                    key={r.id}
                    onClick={() => handleInspectRun(r.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      isSelected
                        ? 'border-focus bg-surface shadow-sm ring-1 ring-focus/30'
                        : 'border-border bg-surface/60 hover:bg-surface text-ink'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="font-bold text-focus uppercase">{r.agent_name}</span>
                      <span className="text-good-leaf font-semibold">{r.status}</span>
                    </div>

                    <p className="text-xs text-ink font-medium mt-1 truncate">{r.input_query}</p>

                    <div className="flex items-center justify-between text-[10px] text-ink-muted mt-2 font-mono">
                      <span>{r.tool_calls_count || 0} tool calls</span>
                      <span>{r.started_at ? new Date(r.started_at).toLocaleTimeString() : ''}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Trace Timeline & Tool Calls */}
        <div className="lg:col-span-2 space-y-6">
          {selectedRun ? (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-6">
              <div className="border-b border-border pb-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-focus">
                    RUN #{selectedRun.id} • {selectedRun.agent_name}
                  </span>
                  <span className="text-xs font-mono text-good-leaf bg-good-leaf/10 px-2.5 py-0.5 rounded-full font-bold">
                    {selectedRun.status}
                  </span>
                </div>
                <h3 className="font-heading font-semibold text-sm text-ink">{selectedRun.input_query}</h3>
              </div>

              {/* Tool Calls Log */}
              <div className="space-y-3">
                <span className="text-xs font-semibold text-ink uppercase tracking-wider block">
                  Tool Invocations ({selectedRun.tool_calls?.length || 0})
                </span>

                {selectedRun.tool_calls && selectedRun.tool_calls.length > 0 ? (
                  <div className="space-y-3">
                    {selectedRun.tool_calls.map((tc) => (
                      <div
                        key={tc.id}
                        className="p-3.5 rounded-xl border border-border bg-canvas text-xs space-y-2 font-mono"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-focus">{tc.tool_name}</span>
                          <span className="text-ink-muted">{tc.execution_time_ms}ms</span>
                        </div>

                        {tc.tool_input && (
                          <div className="text-[11px] text-ink-muted bg-surface p-2 rounded border border-border/50 overflow-x-auto">
                            <strong>Input: </strong>
                            {tc.tool_input}
                          </div>
                        )}

                        {tc.tool_output && (
                          <div className="text-[11px] text-ink bg-surface p-2 rounded border border-border/50 overflow-x-auto">
                            <strong>Output: </strong>
                            {tc.tool_output}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-ink-muted">No external tools invoked for this run.</p>
                )}
              </div>

              {/* Final Synthesis Output Result */}
              {selectedRun.output_result && (
                <div className="space-y-2 pt-2 border-t border-border">
                  <span className="text-xs font-semibold text-ink uppercase tracking-wider block">
                    Synthesized Result
                  </span>
                  <div className="p-4 rounded-xl bg-canvas border border-border text-xs text-ink leading-relaxed whitespace-pre-wrap font-sans">
                    {selectedRun.output_result}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted">
              Select an execution run from the left panel to inspect its execution trace.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
