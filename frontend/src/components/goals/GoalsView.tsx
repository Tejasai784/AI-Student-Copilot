import React, { useState, useEffect } from 'react';
import {
  CheckSquare,
  Sparkles,
  Plus,
  CheckCircle2,
  Circle,
  Calendar,
  AlertCircle,
  Target,
  ChevronRight,
} from 'lucide-react';
import { api } from '../../lib/api';
import { Goal, Subject, Task } from '../../types';

export const GoalsView: React.FC = () => {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  // Goal decomposition prompt
  const [goalPrompt, setGoalPrompt] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(undefined);
  const [decomposing, setDecomposing] = useState(false);

  // Inspected Goal details
  const [activeGoal, setActiveGoal] = useState<any | null>(null);
  const [loadingGoalDetails, setLoadingGoalDetails] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [gList, sList] = await Promise.all([api.getGoals(), api.getSubjects()]);
      setGoals(gList);
      setSubjects(sList);
    } catch (err) {
      console.error('Failed to load goals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDecomposeGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalPrompt.trim()) return;

    try {
      setDecomposing(true);
      const newGoal = await api.createGoalFromPrompt(goalPrompt.trim(), selectedSubjectId);
      setGoalPrompt('');
      await loadData();
      await handleInspectGoal(newGoal.id);
    } catch (err: any) {
      alert(`Goal decomposition failed: ${err.message}`);
    } finally {
      setDecomposing(false);
    }
  };

  const handleInspectGoal = async (goalId: number) => {
    try {
      setLoadingGoalDetails(true);
      const details = await api.getGoal(goalId);
      setActiveGoal(details);
    } catch (err: any) {
      alert(`Failed to load goal: ${err.message}`);
    } finally {
      setLoadingGoalDetails(false);
    }
  };

  const handleToggleTask = async (taskId: number) => {
    try {
      await api.toggleGoalTask(taskId);
      if (activeGoal) {
        await handleInspectGoal(activeGoal.id);
      }
      await loadData();
    } catch (err: any) {
      alert(`Task toggle failed: ${err.message}`);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Academic Goals & Autonomous Decomposition
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            State your high-level objective in natural language. The autonomous planner breaks it down into actionable milestones.
          </p>
        </div>
      </div>

      {/* Decomposition Input Card */}
      <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4 max-w-4xl mx-auto">
        <div className="flex items-center gap-2 text-ink">
          <Sparkles size={18} className="text-focus" />
          <h2 className="font-heading font-bold text-sm">Decompose a New Learning Goal</h2>
        </div>

        <form onSubmit={handleDecomposeGoal} className="space-y-3 text-xs">
          <textarea
            rows={2}
            value={goalPrompt}
            onChange={(e) => setGoalPrompt(e.target.value)}
            placeholder="e.g., 'Master Dynamic Programming and Graph Algorithms before next Tuesday's exam', 'Finish Unit 3 Operating Systems notes and solve 10 practice questions'..."
            className="w-full p-3 rounded-xl border border-border bg-canvas text-ink placeholder:text-ink-muted focus:outline-none focus:border-focus leading-relaxed"
          />

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs font-semibold text-ink-muted">Subject (Optional):</span>
              <select
                value={selectedSubjectId ?? ''}
                onChange={(e) => setSelectedSubjectId(e.target.value ? Number(e.target.value) : undefined)}
                className="rounded-lg border border-border bg-canvas px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-focus"
              >
                <option value="">Auto-Detect Subject</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={decomposing || !goalPrompt.trim()}
              className="w-full sm:w-auto px-5 py-2 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {decomposing ? (
                <span>Decomposing Milestones...</span>
              ) : (
                <>
                  <Target size={14} />
                  <span>Decompose & Track</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
        {/* Goals List */}
        <div className="lg:col-span-1 space-y-3">
          <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider block px-1">
            Active Goals ({goals.length})
          </span>

          {goals.length === 0 ? (
            <div className="bg-surface border border-border rounded-xl p-8 text-center text-xs text-ink-muted">
              No academic goals created yet. Enter a prompt above to generate your first goal!
            </div>
          ) : (
            goals.map((g) => {
              const isSelected = activeGoal?.id === g.id;
              return (
                <div
                  key={g.id}
                  onClick={() => handleInspectGoal(g.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-focus bg-surface shadow-sm ring-1 ring-focus/30'
                      : 'border-border bg-surface/70 hover:bg-surface text-ink'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-heading font-bold text-xs text-ink truncate max-w-[200px]">
                      {g.title}
                    </span>
                    <span className="text-[11px] font-mono font-bold text-focus">
                      {g.progress_percentage ?? 0}%
                    </span>
                  </div>

                  <p className="text-[11px] text-ink-muted mt-1 line-clamp-2">{g.objective}</p>

                  <div className="w-full h-1.5 rounded-full bg-border mt-3 overflow-hidden">
                    <div
                      className="h-full bg-focus transition-all duration-300"
                      style={{ width: `${g.progress_percentage ?? 0}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-ink-muted mt-2 font-mono">
                    <span>{g.completed_tasks_count || 0} / {g.tasks_count || 0} subtasks</span>
                    <span>{g.status}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Goal Detail & Subtask Milestones */}
        <div className="lg:col-span-2">
          {activeGoal ? (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-6">
              <div className="border-b border-border pb-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-focus">
                    Goal #{activeGoal.id} • {activeGoal.status}
                  </span>
                  {activeGoal.deadline && (
                    <span className="text-xs font-mono text-ink-muted flex items-center gap-1">
                      <Calendar size={12} />
                      <span>{new Date(activeGoal.deadline).toLocaleDateString()}</span>
                    </span>
                  )}
                </div>
                <h2 className="font-heading font-bold text-lg text-ink">{activeGoal.title}</h2>
                <p className="text-xs text-ink-muted leading-relaxed">{activeGoal.objective}</p>
              </div>

              {/* Subtasks Checklist */}
              <div className="space-y-3">
                <span className="text-xs font-semibold text-ink uppercase tracking-wider block">
                  Actionable Milestones ({activeGoal.tasks?.length || 0})
                </span>

                {activeGoal.tasks && activeGoal.tasks.length > 0 ? (
                  <div className="space-y-2">
                    {activeGoal.tasks.map((task: any) => {
                      const isDone = task.status === 'COMPLETED';
                      return (
                        <div
                          key={task.id}
                          onClick={() => handleToggleTask(task.id)}
                          className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-colors ${
                            isDone
                              ? 'bg-good-leaf/5 border-good-leaf/20 text-ink-muted'
                              : 'bg-canvas hover:bg-surface-muted border-border text-ink'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            {isDone ? (
                              <CheckCircle2 size={18} className="text-good-leaf flex-shrink-0" />
                            ) : (
                              <Circle size={18} className="text-ink-muted flex-shrink-0" />
                            )}
                            <div>
                              <span className={`text-xs font-semibold block ${isDone ? 'line-through' : ''}`}>
                                {task.title}
                              </span>
                              {task.description && (
                                <span className="text-[11px] text-ink-muted line-clamp-1">
                                  {task.description}
                                </span>
                              )}
                            </div>
                          </div>

                          {task.effort_minutes && (
                            <span className="text-[11px] font-mono text-ink-muted">
                              ~{task.effort_minutes}m
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-ink-muted">
                    No subtasks attached to this goal.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted">
              Select a goal on the left to review and check off its milestones.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
