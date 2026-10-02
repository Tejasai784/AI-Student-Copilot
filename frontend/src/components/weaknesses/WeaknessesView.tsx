import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Sparkles,
  ArrowRight,
  TrendingDown,
  CheckCircle,
  HelpCircle,
  RefreshCw,
  Target,
} from 'lucide-react';
import { api } from '../../lib/api';
import { WeakTopic } from '../../types';

interface WeaknessesViewProps {
  onPracticeTopic?: (topicName: string) => void;
  onAskTutor?: (topicName: string) => void;
}

export const WeaknessesView: React.FC<WeaknessesViewProps> = ({ onPracticeTopic, onAskTutor }) => {
  const [weakTopics, setWeakTopics] = useState<WeakTopic[]>([]);
  const [loading, setLoading] = useState(true);

  const loadWeaknesses = async () => {
    try {
      setLoading(true);
      const data = await api.getWeakTopics();
      setWeakTopics(data);
    } catch (err) {
      console.error('Failed to load weak topics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWeaknesses();
  }, []);

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-weak-rose/10 text-weak-rose">
            High Priority
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-spark-amber/10 text-spark-amber">
            Medium Priority
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-focus/10 text-focus">
            Low Priority
          </span>
        );
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Weak Topics & Targeted Remediation
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Algorithmic error pattern analysis identifying curriculum areas requiring immediate reinforcement.
          </p>
        </div>
        <button
          onClick={loadWeaknesses}
          className="self-start sm:self-auto p-2 rounded-lg border border-border bg-surface hover:bg-surface-muted text-ink transition-colors flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Analysis</span>
        </button>
      </div>

      {loading ? (
        <div className="py-20 text-center text-xs text-ink-muted">Analyzing quiz responses and error rates...</div>
      ) : weakTopics.length === 0 ? (
        <div className="bg-surface border border-border rounded-2xl p-12 text-center max-w-lg mx-auto space-y-4">
          <div className="h-14 w-14 rounded-2xl bg-good-leaf/10 text-good-leaf flex items-center justify-center mx-auto">
            <CheckCircle size={30} />
          </div>
          <h3 className="font-heading font-bold text-base text-ink">No Critical Weaknesses Detected!</h3>
          <p className="text-xs text-ink-muted leading-relaxed">
            Your quiz accuracy across syllabus topics is currently strong. Keep practicing or explore new course units to stay sharp.
          </p>
        </div>
      ) : (
        <div className="space-y-4 max-w-4xl mx-auto">
          <div className="flex items-center justify-between text-xs text-ink-muted px-1">
            <span>
              Found <strong className="text-ink">{weakTopics.length} topics</strong> needing reinforcement
            </span>
            <span className="font-mono text-[11px]">Ranked by failure frequency</span>
          </div>

          <div className="space-y-4">
            {weakTopics.map((item, idx) => (
              <div
                key={idx}
                className="bg-surface border border-border hover:border-weak-rose/40 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2.5">
                    {getPriorityBadge(item.priority)}
                    {item.subject_name && (
                      <span className="text-xs text-ink-muted font-medium bg-surface-muted px-2 py-0.5 rounded">
                        {item.subject_name}
                      </span>
                    )}
                  </div>

                  <h3 className="font-heading font-bold text-base text-ink">
                    {item.topic_name}
                  </h3>

                  <div className="flex items-center gap-4 text-xs font-mono text-ink-muted">
                    <span>
                      Failure Rate:{' '}
                      <strong className="text-weak-rose font-bold">
                        {(item.failure_rate * 100).toFixed(0)}%
                      </strong>
                    </span>
                    <span>•</span>
                    <span>{item.attempts_count || 1} attempts logged</span>
                  </div>

                  {item.recommended_action && (
                    <p className="text-xs text-ink-muted bg-canvas p-3 rounded-xl border border-border/60">
                      💡 <strong>Recommendation:</strong> {item.recommended_action}
                    </p>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row items-stretch md:items-center gap-2.5 flex-shrink-0">
                  <button
                    onClick={() => {
                      if (onPracticeTopic) onPracticeTopic(item.topic_name);
                      else alert(`Starting targeted quiz for ${item.topic_name}`);
                    }}
                    className="px-4 py-2 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-1.5"
                  >
                    <HelpCircle size={14} />
                    <span>Practice Quiz</span>
                  </button>

                  <button
                    onClick={() => {
                      if (onAskTutor) onAskTutor(item.topic_name);
                      else alert(`Opening AI Tutor session on ${item.topic_name}`);
                    }}
                    className="px-4 py-2 rounded-xl bg-surface border border-border hover:bg-surface-muted text-ink font-semibold text-xs transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Sparkles size={14} className="text-spark-amber" />
                    <span>Explain Concept</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
