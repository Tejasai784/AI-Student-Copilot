import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Calendar,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  Award,
  ChevronRight,
  Flame,
  Target,
} from 'lucide-react';
import { api } from '../../lib/api';
import { DashboardSummary, Goal, Task } from '../../types';

interface DashboardViewProps {
  onNavigateToChat: () => void;
  onNavigateToPlanner: () => void;
  onNavigateToQuizzes: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigateToChat,
  onNavigateToPlanner,
  onNavigateToQuizzes,
}) => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getDashboard().catch(() => null),
      api.getGoals().catch(() => []),
    ]).then(([dashData, goalList]) => {
      if (dashData) setData(dashData);
      if (goalList) setGoals(goalList);
      setLoading(false);
    });
  }, []);

  const getGreeting = () => {
    const hr = new Date().getHours();
    if (hr < 12) return 'Good morning';
    if (hr < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const studentName = data?.student_name || 'Alex';
  const progressPct = data?.study_progress || 68.5;
  const activeGoal = goals.length > 0 ? goals[0] : null;
  const pendingTasks = activeGoal?.tasks?.filter((t) => t.status !== 'COMPLETED') || [];
  const primaryTask = pendingTasks.length > 0 ? pendingTasks[0] : {
    id: 1,
    title: 'Revise Core Fundamentals & Syntax in Python',
    effort_minutes: 45,
    status: 'PENDING',
  };

  // SVG Circle calculation for progress ring
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPct / 100) * circumference;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* 1. Greeting & Proactive Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            {getGreeting()}, {studentName}.
          </h2>
          <p className="text-sm text-ink-muted mt-1">
            You have <strong className="text-ink font-semibold">3 hours</strong> planned today. Your next major milestone is in <strong className="text-focus font-semibold">7 days</strong>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-spark/15 text-spark border border-spark/30 text-xs font-semibold">
            <Flame size={15} />
            <span>4-Day Study Streak</span>
          </div>
        </div>
      </div>

      {/* 2. Top Asymmetric Row: "Today" Hero + Exam Countdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* "TODAY" Hero Panel (2 cols) */}
        <div className="lg:col-span-2 rounded-2xl bg-surface border border-border p-6 md:p-8 shadow-sm flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-focus/5 rounded-full -translate-y-24 translate-x-24 pointer-events-none" />

          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-focus font-mono bg-focus/10 px-2.5 py-1 rounded-md">
                Today's Priority Focus
              </span>
              <span className="text-xs text-ink-muted flex items-center gap-1.5">
                <Clock size={14} />
                Estimated: {primaryTask.effort_minutes || 45} min
              </span>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 mt-2">
              {/* Circular Progress Ring */}
              <div className="relative flex-shrink-0">
                <svg className="w-24 h-24 transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r={radius}
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-border"
                    fill="transparent"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r={radius}
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    className="text-focus transition-all duration-1000 ease-out"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center font-heading">
                  <span className="text-lg font-bold text-ink">{Math.round(progressPct)}%</span>
                  <span className="text-[10px] text-ink-muted uppercase">Ready</span>
                </div>
              </div>

              {/* Task Details */}
              <div className="space-y-1">
                <h3 className="font-heading font-bold text-lg md:text-xl text-ink leading-snug">
                  {primaryTask.title}
                </h3>
                <p className="text-sm text-ink-muted">
                  Focus on mastering syntax, recursion depth, and edge cases before taking the diagnostic mock test.
                </p>
              </div>
            </div>
          </div>

          {/* Primary Action Button */}
          <div className="mt-8 pt-4 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
            <button
              onClick={onNavigateToChat}
              className="px-5 py-2.5 rounded-lg bg-focus hover:bg-focus-hover text-white font-heading font-semibold text-sm flex items-center gap-2 shadow-sm transition-all"
            >
              <span>Start Study Session</span>
              <ArrowRight size={16} />
            </button>
            <span className="text-xs text-ink-muted">
              Auto-tailored from syllabus & uploaded notes
            </span>
          </div>
        </div>

        {/* Upcoming Exam Card (1 col) */}
        <div className="rounded-2xl bg-surface border border-border p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-muted font-mono">
                Approaching Exam
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-weak/15 text-weak">
                High Stakes
              </span>
            </div>

            <h3 className="font-heading font-bold text-lg text-ink">
              Python Programming (CS302)
            </h3>
            <p className="text-xs text-ink-muted mt-1">Final Comprehensive Assessment</p>

            <div className="mt-6 p-4 rounded-xl bg-canvas border border-border/80 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-ink-muted">Countdown:</span>
                <span className="font-bold text-weak font-heading text-sm">7 Days Left</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-ink-muted">Target Score:</span>
                <span className="font-bold text-good font-heading text-sm">90% (Grade A)</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-ink-muted">Units Covered:</span>
                <span className="font-semibold text-ink">4 of 5 Units</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border/60">
            <button
              onClick={onNavigateToQuizzes}
              className="w-full py-2 rounded-lg bg-surface-muted hover:bg-surface-muted/80 text-ink text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
            >
              <Award size={14} className="text-focus" />
              <span>Launch Mock Exam Diagnostic</span>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Lower Row: Adaptive 7-Day Plan Timeline + Weak Topics Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Adaptive Plan Timeline (2 cols) */}
        <div className="lg:col-span-2 rounded-2xl bg-surface border border-border p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-heading font-bold text-base md:text-lg text-ink">
                7-Day Adaptive Study Agenda
              </h3>
              <p className="text-xs text-ink-muted">Sequential tasks dynamically balanced by difficulty</p>
            </div>
            <button
              onClick={onNavigateToPlanner}
              className="text-xs font-semibold text-focus hover:underline flex items-center gap-1"
            >
              <span>Full Planner</span>
              <ChevronRight size={14} />
            </button>
          </div>

          <div className="space-y-3 mt-4">
            {[
              { day: 'Day 1', title: 'Syllabus Inspection & Concept Review', status: 'COMPLETED', time: '60 min', tag: 'Syntax' },
              { day: 'Day 2', title: 'Deep Dive: Core Algorithms & Data Structures', status: 'IN_PROGRESS', time: '90 min', tag: 'Logic' },
              { day: 'Day 3', title: 'Diagnostic Mock Assessment & Error Analysis', status: 'PENDING', time: '60 min', tag: 'Exam' },
              { day: 'Day 4', title: 'Targeted Remediation on Weak Topics', status: 'PENDING', time: '45 min', tag: 'Remediation' },
            ].map((task, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3.5 rounded-xl bg-canvas border border-border/60 hover:border-focus/40 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-1 rounded-full ${task.status === 'COMPLETED' ? 'text-good bg-good/15' : 'text-ink-muted bg-surface'}`}>
                    <CheckCircle2 size={16} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold font-mono text-ink-muted">{task.day}</span>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-surface border border-border text-ink">
                        {task.tag}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-ink mt-0.5">{task.title}</p>
                  </div>
                </div>
                <span className="text-xs text-ink-muted font-mono">{task.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Weak Topics Radar (1 col) */}
        <div className="rounded-2xl bg-surface border border-border p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-bold text-base text-ink">
                Priority Weaknesses
              </h3>
              <span className="text-xs text-weak font-semibold flex items-center gap-1">
                <AlertTriangle size={13} />
                Attention
              </span>
            </div>

            <p className="text-xs text-ink-muted mb-4">
              Identified by autonomous Critic & Exam agents from missed questions:
            </p>

            <div className="space-y-3">
              {[
                { topic: 'Recursion Depth & Stack Limits', level: 'Critical (40%)', action: '3 drills' },
                { topic: 'Dictionary Hashing & Mutability', level: 'Moderate (65%)', action: '2 drills' },
                { topic: 'Exception Hierarchy', level: 'Mild (78%)', action: '1 drill' },
              ].map((w, i) => (
                <div key={i} className="p-3 rounded-xl bg-weak/5 border border-weak/20 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-ink">{w.topic}</span>
                    <span className="text-[10px] font-bold text-weak uppercase">{w.level}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-ink-muted">
                    <span>Target practice recommended</span>
                    <span className="text-focus font-medium">{w.action}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border/60">
            <button
              onClick={onNavigateToQuizzes}
              className="w-full py-2 rounded-lg bg-focus text-white text-xs font-semibold hover:bg-focus-hover transition-colors shadow-sm"
            >
              Generate Remediation Quiz Drill
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
