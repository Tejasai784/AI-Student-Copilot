import React, { useState, useEffect, useRef } from 'react';
import {
  Award,
  Clock,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { api } from '../../lib/api';
import { QuizAttempt, Subject } from '../../types';

export const MockExamsView: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(undefined);
  const [examDuration, setExamDuration] = useState<number>(30); // minutes
  const [numQuestions, setNumQuestions] = useState<number>(10);
  const [loading, setLoading] = useState(false);

  // Active exam state
  const [activeExam, setActiveExam] = useState<QuizAttempt | null>(null);
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [timeLeftSeconds, setTimeLeftSeconds] = useState<number>(0);
  const [submitting, setSubmitting] = useState(false);
  const [examResult, setExamResult] = useState<QuizAttempt | null>(null);

  const timerRef = useRef<any>(null);

  useEffect(() => {
    api.getSubjects().then((subs) => {
      setSubjects(subs);
      if (subs.length > 0) setSelectedSubjectId(subs[0].id);
    }).catch(console.error);
  }, []);

  // Timer effect
  useEffect(() => {
    if (activeExam && timeLeftSeconds > 0) {
      timerRef.current = setInterval(() => {
        setTimeLeftSeconds((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            handleAutoSubmit();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [activeExam]);

  const handleStartExam = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const attempt = await api.generateQuiz({
        subject_id: selectedSubjectId,
        num_questions: numQuestions,
        difficulty: 'hard',
        time_limit_seconds: examDuration * 60,
        exam_kind: 'MOCK_EXAM',
      });
      const full = await api.getQuizAttempt(attempt.id);
      setActiveExam(full);
      setTimeLeftSeconds(examDuration * 60);
      setCurrentQIndex(0);
      setUserAnswers({});
      setExamResult(null);
    } catch (err: any) {
      alert(`Failed to launch mock exam: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAnswer = (qId: number, ans: string) => {
    setUserAnswers((prev) => ({ ...prev, [qId]: ans }));
    if (activeExam) {
      api.recordQuizAnswer(activeExam.id, qId, ans).catch(console.error);
    }
  };

  const handleAutoSubmit = async () => {
    if (!activeExam) return;
    try {
      setSubmitting(true);
      const res = await api.submitQuiz(activeExam.id, userAnswers);
      const full = await api.getQuizAttempt(res.id);
      setExamResult(full);
      setActiveExam(null);
    } catch (err: any) {
      console.error('Auto submit error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleManualSubmit = async () => {
    if (!activeExam) return;
    if (!window.confirm('Are you sure you want to finish and submit your Mock Exam?')) return;
    if (timerRef.current) clearInterval(timerRef.current);
    await handleAutoSubmit();
  };

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Timed Mock Examinations
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Simulate real exam pressure with strict time limits, comprehensive curriculum coverage, and automated grading.
          </p>
        </div>
      </div>

      {!activeExam && !examResult && (
        <div className="max-w-2xl mx-auto bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-3 border-b border-border pb-4">
            <div className="h-10 w-10 rounded-xl bg-spark-amber/10 text-spark-amber flex items-center justify-center">
              <Award size={22} />
            </div>
            <div>
              <h2 className="font-heading font-bold text-base text-ink">Configure Mock Exam</h2>
              <p className="text-xs text-ink-muted">Full-length timed evaluation session</p>
            </div>
          </div>

          <form onSubmit={handleStartExam} className="space-y-5 text-xs">
            <div>
              <label className="block font-medium text-ink mb-1.5">Subject *</label>
              <select
                value={selectedSubjectId ?? ''}
                onChange={(e) => setSelectedSubjectId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2.5 text-xs text-ink focus:outline-none focus:border-focus"
              >
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-ink mb-1.5">Duration</label>
                <select
                  value={examDuration}
                  onChange={(e) => setExamDuration(Number(e.target.value))}
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2.5 text-xs text-ink focus:outline-none focus:border-focus"
                >
                  <option value={15}>15 Minutes</option>
                  <option value={30}>30 Minutes</option>
                  <option value={45}>45 Minutes</option>
                  <option value={60}>60 Minutes</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-ink mb-1.5">Number of Questions</label>
                <select
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2.5 text-xs text-ink focus:outline-none focus:border-focus"
                >
                  <option value={5}>5 Questions</option>
                  <option value={10}>10 Questions</option>
                  <option value={15}>15 Questions</option>
                </select>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-canvas border border-border/80 space-y-2 text-ink-muted">
              <div className="flex items-center gap-2 font-medium text-ink">
                <AlertTriangle size={14} className="text-spark-amber" />
                <span>Exam Conditions Notice</span>
              </div>
              <ul className="list-disc pl-4 space-y-1 text-[11px]">
                <li>The countdown starts immediately upon clicking launch.</li>
                <li>Your answers auto-save on selection.</li>
                <li>When the timer expires, unsubmitted answers will automatically submit.</li>
              </ul>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span>Assembling Mock Exam...</span>
              ) : (
                <>
                  <Play size={16} />
                  <span>Begin Timed Mock Exam</span>
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* ACTIVE TIMED EXAM */}
      {activeExam && activeExam.questions && (
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Top Bar with Timer */}
          <div className="bg-surface border border-border rounded-2xl p-4 md:p-5 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="font-heading font-bold text-sm text-ink">
                Question {currentQIndex + 1} of {activeExam.questions.length}
              </span>
              <span className="text-[11px] font-mono text-ink-muted bg-surface-muted px-2 py-0.5 rounded">
                {Object.keys(userAnswers).length} Answered
              </span>
            </div>

            {/* Countdown Badge */}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border font-mono font-bold text-sm ${
                timeLeftSeconds < 180
                  ? 'border-weak-rose bg-weak-rose/10 text-weak-rose animate-pulse'
                  : 'border-border bg-canvas text-ink'
              }`}
            >
              <Clock size={16} />
              <span>{formatTimer(timeLeftSeconds)}</span>
            </div>

            <button
              onClick={handleManualSubmit}
              disabled={submitting}
              className="px-4 py-1.5 rounded-xl bg-good-leaf text-white font-semibold text-xs hover:bg-good-leaf/90 transition-colors"
            >
              Submit Exam
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Question Card */}
            <div className="md:col-span-3 bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-sm space-y-6">
              {(() => {
                const q = activeExam.questions[currentQIndex];
                const currentAns = userAnswers[q.id] || '';
                const opts = q.options || [];

                return (
                  <>
                    <div className="space-y-2">
                      <span className="text-[11px] font-mono font-medium text-focus uppercase tracking-wider">
                        {q.topic_name || 'Question Focus'} • {q.max_marks} marks
                      </span>
                      <h3 className="font-heading font-semibold text-base text-ink leading-relaxed">
                        {q.question_text}
                      </h3>
                    </div>

                    {opts.length > 0 ? (
                      <div className="space-y-3">
                        {opts.map((opt, oIdx) => {
                          const isSelected = currentAns === opt;
                          return (
                            <button
                              key={oIdx}
                              onClick={() => handleSelectAnswer(q.id, opt)}
                              className={`w-full text-left p-3.5 rounded-xl border text-xs font-medium transition-all flex items-center gap-3 ${
                                isSelected
                                  ? 'border-focus bg-focus/10 text-focus ring-1 ring-focus/40'
                                  : 'border-border bg-canvas/60 hover:bg-canvas text-ink'
                              }`}
                            >
                              <span
                                className={`h-6 w-6 rounded-full flex items-center justify-center font-mono text-[11px] font-bold ${
                                  isSelected ? 'bg-focus text-white' : 'bg-surface-muted text-ink-muted'
                                }`}
                              >
                                {String.fromCharCode(65 + oIdx)}
                              </span>
                              <span className="flex-1">{opt}</span>
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <textarea
                        rows={5}
                        value={currentAns}
                        onChange={(e) => handleSelectAnswer(q.id, e.target.value)}
                        placeholder="Write your detailed solution / code..."
                        className="w-full p-3 rounded-xl border border-border bg-canvas text-xs text-ink font-mono focus:outline-none focus:border-focus"
                      />
                    )}

                    <div className="flex items-center justify-between pt-4 border-t border-border">
                      <button
                        disabled={currentQIndex === 0}
                        onClick={() => setCurrentQIndex((prev) => prev - 1)}
                        className="px-3.5 py-2 rounded-xl border border-border bg-surface hover:bg-surface-muted text-xs font-semibold text-ink flex items-center gap-1.5 disabled:opacity-40"
                      >
                        <ChevronLeft size={16} />
                        <span>Previous</span>
                      </button>

                      <button
                        disabled={currentQIndex >= activeExam.questions.length - 1}
                        onClick={() => setCurrentQIndex((prev) => prev + 1)}
                        className="px-4 py-2 rounded-xl bg-surface border border-border hover:bg-surface-muted text-xs font-semibold text-ink flex items-center gap-1.5 disabled:opacity-40"
                      >
                        <span>Next</span>
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </>
                );
              })()}
            </div>

            {/* Jump Navigation Grid */}
            <div className="md:col-span-1 bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-3 h-fit">
              <span className="text-xs font-semibold text-ink-muted block uppercase tracking-wider">
                Question Map
              </span>
              <div className="grid grid-cols-4 gap-2">
                {activeExam.questions.map((q, idx) => {
                  const isAnswered = !!userAnswers[q.id];
                  const isCurrent = idx === currentQIndex;
                  return (
                    <button
                      key={q.id}
                      onClick={() => setCurrentQIndex(idx)}
                      className={`h-9 rounded-lg font-mono text-xs font-bold transition-all ${
                        isCurrent
                          ? 'ring-2 ring-focus bg-focus text-white'
                          : isAnswered
                          ? 'bg-good-leaf/20 text-good-leaf border border-good-leaf/40'
                          : 'bg-canvas border border-border text-ink-muted hover:text-ink'
                      }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* EXAM RESULTS BREAKDOWN */}
      {examResult && (
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-sm text-center space-y-4">
            <div className="inline-flex h-16 w-16 rounded-2xl bg-focus/10 text-focus items-center justify-center">
              <Award size={32} />
            </div>
            <div>
              <span className="text-xs text-ink-muted uppercase font-semibold tracking-wider">
                Mock Exam Results
              </span>
              <h2 className="font-heading font-bold text-3xl text-ink mt-1">
                {examResult.percentage.toFixed(0)}% Score
              </h2>
              <p className="text-xs text-ink-muted mt-1 font-mono">
                {examResult.user_marks} of {examResult.total_marks} Marks Total
              </p>
            </div>

            <button
              onClick={() => {
                setExamResult(null);
                setActiveExam(null);
              }}
              className="px-4 py-2 rounded-xl bg-focus text-white text-xs font-semibold hover:bg-focus-hover shadow-sm transition-colors inline-flex items-center gap-2"
            >
              <RotateCcw size={14} />
              <span>Back to Mock Exams</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
