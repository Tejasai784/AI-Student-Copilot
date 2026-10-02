import React, { useState, useEffect } from 'react';
import {
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  Sparkles,
  RefreshCw,
  Plus,
  BookOpen,
  AlertCircle,
} from 'lucide-react';
import { api } from '../../lib/api';
import { StudyPlanItem, StudyTaskItem } from '../../types';

export const PlannerView: React.FC = () => {
  const [plan, setPlan] = useState<StudyPlanItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [horizon, setHorizon] = useState('weekly');
  const [examFocus, setExamFocus] = useState('Midterms');
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [generating, setGenerating] = useState(false);

  const loadPlan = async () => {
    try {
      setLoading(true);
      const res = await api.getCurrentStudyPlan();
      setPlan(res);
    } catch (err) {
      console.error('Failed to load study plan:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlan();
  }, []);

  const handleToggleTask = async (taskId: number) => {
    try {
      await api.toggleStudyTask(taskId);
      await loadPlan();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  const handleGeneratePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setGenerating(true);
      const newPlan = await api.generateStudyPlan({
        horizon,
        exam_focus: examFocus,
        daily_minutes: dailyMinutes,
      });
      setPlan(newPlan);
      setShowGenerateModal(false);
    } catch (err: any) {
      alert(`Plan generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const totalTasks = plan?.tasks.length || 0;
  const completedTasks = plan?.tasks.filter((t) => t.status === 'COMPLETED').length || 0;
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // Group tasks by scheduled date
  const tasksByDate: Record<string, StudyTaskItem[]> = {};
  if (plan?.tasks) {
    plan.tasks.forEach((t) => {
      const d = t.scheduled_date || 'Today';
      if (!tasksByDate[d]) tasksByDate[d] = [];
      tasksByDate[d].push(t);
    });
  }

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Adaptive Study Planner
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Dynamic calendar balancing syllabus coverage, weak topics, and active learning intervals.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowGenerateModal(true)}
            className="px-4 py-2 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center gap-2"
          >
            <Sparkles size={14} />
            <span>Generate New Plan</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-xs text-ink-muted">Loading your schedule...</div>
      ) : !plan ? (
        <div className="bg-surface border border-border rounded-2xl p-12 text-center max-w-lg mx-auto space-y-4">
          <Calendar size={36} className="mx-auto text-focus" />
          <h3 className="font-heading font-bold text-base text-ink">No Active Study Plan</h3>
          <p className="text-xs text-ink-muted">
            Let the platform analyze your registered subjects, upcoming exams, and weak areas to produce a tailored daily study plan.
          </p>
          <button
            onClick={() => setShowGenerateModal(true)}
            className="px-4 py-2 rounded-xl bg-focus text-white text-xs font-semibold hover:bg-focus-hover transition-colors"
          >
            Generate Study Schedule
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Plan Summary Card */}
          <div className="lg:col-span-1 bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-6 h-fit">
            <div>
              <span className="text-[11px] font-mono text-focus font-semibold uppercase tracking-wider">
                {plan.horizon} Plan • {plan.status}
              </span>
              <h2 className="font-heading font-bold text-lg text-ink mt-1">{plan.title}</h2>
              {plan.notes && <p className="text-xs text-ink-muted mt-1.5">{plan.notes}</p>}
            </div>

            {/* Circular Progress Meter */}
            <div className="flex items-center gap-4 bg-canvas p-4 rounded-xl border border-border">
              <div className="relative h-14 w-14 flex items-center justify-center flex-shrink-0">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-border"
                    strokeWidth="3.5"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className="text-focus transition-all duration-500 ease-out"
                    strokeDasharray={`${progressPercent}, 100`}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <span className="absolute font-heading font-bold text-xs text-ink">
                  {progressPercent}%
                </span>
              </div>
              <div className="text-xs">
                <span className="font-semibold text-ink block">
                  {completedTasks} of {totalTasks} Tasks Done
                </span>
                <span className="text-[11px] text-ink-muted">
                  Focus: {plan.exam_focus || 'Curriculum mastery'}
                </span>
              </div>
            </div>
          </div>

          {/* Timeline Schedule */}
          <div className="lg:col-span-2 space-y-6">
            {Object.entries(tasksByDate).map(([dateStr, tasks]) => (
              <div key={dateStr} className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <Calendar size={16} className="text-focus" />
                    <h3 className="font-heading font-bold text-sm text-ink">{dateStr}</h3>
                  </div>
                  <span className="text-[11px] text-ink-muted font-mono">
                    {tasks.filter((t) => t.status === 'COMPLETED').length} / {tasks.length} completed
                  </span>
                </div>

                <div className="space-y-2.5">
                  {tasks.map((task) => {
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
                            <span className="text-[11px] text-ink-muted">
                              {task.topic_name} • {task.task_type}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 text-[11px] font-mono text-ink-muted">
                          <Clock size={12} />
                          <span>{task.duration_minutes}m</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-xl max-w-md w-full space-y-4">
            <h3 className="font-heading font-bold text-base text-ink">Generate Adaptive Schedule</h3>
            <form onSubmit={handleGeneratePlan} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-ink mb-1">Schedule Horizon</label>
                <select
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                >
                  <option value="daily">Daily Schedule</option>
                  <option value="weekly">7-Day Weekly Schedule</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-ink mb-1">Exam / Target Focus</label>
                <input
                  type="text"
                  value={examFocus}
                  onChange={(e) => setExamFocus(e.target.value)}
                  placeholder="e.g. Midterms, End-Semester Finals"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>

              <div>
                <label className="block font-medium text-ink mb-1">Daily Study Time (Minutes)</label>
                <input
                  type="number"
                  min="15"
                  max="480"
                  step="15"
                  value={dailyMinutes}
                  onChange={(e) => setDailyMinutes(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-border text-ink hover:bg-surface-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generating}
                  className="px-4 py-1.5 rounded-lg bg-focus text-white font-semibold hover:bg-focus-hover disabled:opacity-50"
                >
                  {generating ? 'Synthesizing Plan...' : 'Generate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
