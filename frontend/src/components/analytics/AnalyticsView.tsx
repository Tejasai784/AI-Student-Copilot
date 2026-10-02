import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Award,
  BookOpen,
  CheckCircle,
  Clock,
  Calendar,
  BarChart3,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../lib/api';
import { PerformanceData } from '../../types';

export const AnalyticsView: React.FC = () => {
  const [perf, setPerf] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const data = await api.getPerformance();
      setPerf(data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Progress & Performance Analytics
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Quantitative telemetry monitoring study velocity, accuracy trajectories, and mastery across academic domains.
          </p>
        </div>
        <button
          onClick={loadAnalytics}
          className="self-start sm:self-auto p-2 rounded-lg border border-border bg-surface hover:bg-surface-muted text-ink transition-colors flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {loading ? (
        <div className="py-20 text-center text-xs text-ink-muted">Aggregating academic telemetry...</div>
      ) : !perf ? (
        <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted">
          No performance data recorded yet. Complete quizzes and study sessions to populate metrics.
        </div>
      ) : (
        <div className="space-y-8 max-w-5xl mx-auto">
          {/* Key Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-1">
              <span className="text-xs text-ink-muted font-medium block">Total Exam Attempts</span>
              <span className="font-heading font-bold text-2xl text-ink">
                {perf.total_exams}
              </span>
            </div>

            <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-1">
              <span className="text-xs text-ink-muted font-medium block">Average Exam Score</span>
              <span className="font-heading font-bold text-2xl text-focus">
                {perf.average_percentage.toFixed(1)}%
              </span>
            </div>

            <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-1">
              <span className="text-xs text-ink-muted font-medium block">Questions Solved</span>
              <span className="font-heading font-bold text-2xl text-ink">
                {perf.total_questions_answered}
              </span>
            </div>

            <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-1">
              <span className="text-xs text-ink-muted font-medium block">Overall Accuracy</span>
              <span className="font-heading font-bold text-2xl text-good-leaf">
                {(perf.accuracy_rate * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Subject Breakdown Bars */}
          {perf.subject_breakdown && perf.subject_breakdown.length > 0 && (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 size={18} className="text-focus" />
                  <h3 className="font-heading font-bold text-sm text-ink">Subject Mastery Comparison</h3>
                </div>
                <span className="text-xs text-ink-muted">Average score across attempts</span>
              </div>

              <div className="space-y-4">
                {perf.subject_breakdown.map((sb) => (
                  <div key={sb.subject_id} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-ink">{sb.subject_name}</span>
                      <div className="flex items-center gap-3 font-mono">
                        <span className="text-ink-muted text-[11px]">{sb.attempts} attempts</span>
                        <span className="font-bold text-focus">{sb.avg_score.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="w-full h-2 rounded-full bg-border overflow-hidden">
                      <div
                        className="h-full bg-focus transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(0, sb.avg_score))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Study Consistency & Daily Trend */}
          {perf.daily_trend && perf.daily_trend.length > 0 && (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-border pb-3">
                <Calendar size={18} className="text-focus" />
                <h3 className="font-heading font-bold text-sm text-ink">Daily Performance Trend</h3>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
                {perf.daily_trend.slice(-14).map((d, idx) => (
                  <div key={idx} className="p-3 rounded-xl border border-border bg-canvas text-center space-y-1">
                    <span className="text-[10px] text-ink-muted block font-mono">{d.date}</span>
                    <span className="font-mono font-bold text-sm text-ink block">{d.score}%</span>
                    <span className="text-[10px] text-focus font-medium block">{d.exams_count} tests</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
