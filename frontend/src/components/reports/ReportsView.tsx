import React, { useState, useEffect } from 'react';
import {
  FileCheck,
  Download,
  Award,
  CheckCircle,
  AlertTriangle,
  FileText,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { api } from '../../lib/api';
import { ReadinessReport, Subject } from '../../types';

export const ReportsView: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(undefined);
  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSubjects().then(setSubjects).catch(console.error);
  }, []);

  const loadReport = async () => {
    try {
      setLoading(true);
      const rep = await api.getExamReadiness(selectedSubjectId);
      setReport(rep);
    } catch (err) {
      console.error('Failed to generate report:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, [selectedSubjectId]);

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Exam Readiness Reports
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Formal academic readiness diagnosis evaluating syllabus completeness, quiz retention, and confidence intervals.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedSubjectId ?? ''}
            onChange={(e) => setSelectedSubjectId(e.target.value ? Number(e.target.value) : undefined)}
            className="rounded-xl border border-border bg-surface px-3 py-2 text-xs text-ink focus:outline-none focus:border-focus"
          >
            <option value="">All Subjects (Comprehensive)</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <button
            onClick={loadReport}
            className="p-2 rounded-lg border border-border bg-surface hover:bg-surface-muted text-ink transition-colors flex items-center gap-1.5 text-xs font-semibold"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Generate</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-xs text-ink-muted">Synthesizing academic readiness evaluation...</div>
      ) : !report ? (
        <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted">
          Could not generate readiness report. Ensure subjects and profile are set.
        </div>
      ) : (
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Readiness Score Banner */}
          <div className="bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-2 text-center md:text-left">
              <span className="text-xs font-mono font-semibold text-focus uppercase tracking-wider">
                Readiness Assessment • {report.subject_name}
              </span>
              <h2 className="font-heading font-bold text-2xl text-ink">
                Student: {report.student_name}
              </h2>
              <p className="text-xs text-ink-muted">
                Calculated based on completed syllabus topics, quiz accuracy scores, and retrieval coverage.
              </p>
            </div>

            <div className="flex items-center gap-6 flex-shrink-0">
              <div className="text-center">
                <span className="text-[11px] text-ink-muted block uppercase font-medium">Readiness Index</span>
                <span
                  className={`font-heading font-bold text-4xl font-mono ${
                    report.overall_readiness_score >= 75
                      ? 'text-good-leaf'
                      : report.overall_readiness_score >= 50
                      ? 'text-spark-amber'
                      : 'text-weak-rose'
                  }`}
                >
                  {report.overall_readiness_score.toFixed(0)}%
                </span>
              </div>

              {/* Download Buttons */}
              <div className="flex flex-col gap-2">
                <a
                  href={api.getReportDownloadUrl(selectedSubjectId, 'markdown')}
                  download="readiness_report.md"
                  className="px-3.5 py-1.5 rounded-lg border border-border bg-surface-muted hover:bg-border text-ink text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  <Download size={13} />
                  <span>Download .MD</span>
                </a>
                <a
                  href={api.getReportDownloadUrl(selectedSubjectId, 'html')}
                  download="readiness_report.html"
                  className="px-3.5 py-1.5 rounded-lg bg-focus text-white hover:bg-focus-hover text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  <Download size={13} />
                  <span>Download .HTML</span>
                </a>
              </div>
            </div>
          </div>

          {/* Strengths & Weaknesses Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Strengths */}
            <div className="bg-surface border border-good-leaf/30 rounded-2xl p-6 shadow-sm space-y-3">
              <div className="flex items-center gap-2 text-good-leaf">
                <CheckCircle size={18} />
                <h3 className="font-heading font-bold text-sm text-ink">Demonstrated Strengths</h3>
              </div>
              {report.strengths && report.strengths.length > 0 ? (
                <ul className="space-y-2 text-xs text-ink/90">
                  {report.strengths.map((str, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-good-leaf font-bold">•</span>
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-ink-muted">Complete more quizzes to surface strengths.</p>
              )}
            </div>

            {/* Critical Gaps */}
            <div className="bg-surface border border-weak-rose/30 rounded-2xl p-6 shadow-sm space-y-3">
              <div className="flex items-center gap-2 text-weak-rose">
                <AlertTriangle size={18} />
                <h3 className="font-heading font-bold text-sm text-ink">Knowledge Gaps</h3>
              </div>
              {report.weaknesses && report.weaknesses.length > 0 ? (
                <ul className="space-y-2 text-xs text-ink/90">
                  {report.weaknesses.map((w, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-weak-rose font-bold">•</span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-ink-muted">No high-risk knowledge gaps identified.</p>
              )}
            </div>
          </div>

          {/* Markdown Content Preview */}
          {report.markdown_report && (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-border pb-3">
                <FileText size={18} className="text-focus" />
                <h3 className="font-heading font-bold text-sm text-ink">Executive Report Preview</h3>
              </div>
              <div className="p-4 rounded-xl bg-canvas border border-border/80 text-xs text-ink leading-relaxed font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
                {report.markdown_report}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
