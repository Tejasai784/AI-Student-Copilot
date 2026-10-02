import React, { useState, useEffect } from 'react';
import {
  HelpCircle,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  RotateCcw,
  Award,
  History,
  AlertCircle,
} from 'lucide-react';
import { api } from '../../lib/api';
import { QuizAttempt, QuizQuestion, Subject } from '../../types';

export const QuizzesView: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [history, setHistory] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(false);

  // Generator form
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(undefined);
  const [topicName, setTopicName] = useState('');
  const [difficulty, setDifficulty] = useState('medium');
  const [numQuestions, setNumQuestions] = useState(5);

  // Active quiz session
  const [activeAttempt, setActiveAttempt] = useState<QuizAttempt | null>(null);
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submittedResult, setSubmittedResult] = useState<QuizAttempt | null>(null);

  useEffect(() => {
    api.getSubjects().then((subs) => {
      setSubjects(subs);
      if (subs.length > 0) setSelectedSubjectId(subs[0].id);
    }).catch(console.error);

    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const hist = await api.getQuizHistory();
      setHistory(hist);
    } catch (err) {
      console.error('Failed to load quiz history:', err);
    }
  };

  const handleStartQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const attempt = await api.generateQuiz({
        subject_id: selectedSubjectId,
        topic_name: topicName.trim() || undefined,
        num_questions: numQuestions,
        difficulty,
        exam_kind: 'PRACTICE_QUIZ',
      });
      // Fetch full details with questions
      const full = await api.getQuizAttempt(attempt.id);
      setActiveAttempt(full);
      setCurrentQIndex(0);
      setUserAnswers({});
      setSubmittedResult(null);
    } catch (err: any) {
      alert(`Quiz generation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAnswer = (qId: number, answer: string) => {
    setUserAnswers((prev) => ({ ...prev, [qId]: answer }));
    if (activeAttempt) {
      api.recordQuizAnswer(activeAttempt.id, qId, answer).catch(console.error);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!activeAttempt) return;
    if (!window.confirm('Are you ready to submit your quiz for evaluation?')) return;

    try {
      setSubmitting(true);
      const res = await api.submitQuiz(activeAttempt.id, userAnswers);
      const full = await api.getQuizAttempt(res.id);
      setSubmittedResult(full);
      setActiveAttempt(null);
      await loadHistory();
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReviewAttempt = async (attemptId: number) => {
    try {
      setLoading(true);
      const full = await api.getQuizAttempt(attemptId);
      setSubmittedResult(full);
      setActiveAttempt(null);
    } catch (err: any) {
      alert(`Could not load attempt: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Practice Quizzes & Evaluation
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Test your conceptual grasp with automated AI questions and detailed rationale explanations.
          </p>
        </div>
      </div>

      {/* When NO active quiz & NO submitted result -> Show Generator + Past History */}
      {!activeAttempt && !submittedResult && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Generator Form */}
          <div className="lg:col-span-1 bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-5 h-fit">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-focus/10 text-focus flex items-center justify-center">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="font-heading font-bold text-base text-ink">Generate New Quiz</h2>
                <p className="text-xs text-ink-muted">AI-crafted questions targeted to your syllabus</p>
              </div>
            </div>

            <form onSubmit={handleStartQuiz} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-ink mb-1.5">Subject *</label>
                <select
                  value={selectedSubjectId ?? ''}
                  onChange={(e) => setSelectedSubjectId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-ink mb-1.5">Topic Focus (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Graph Algorithms, Normalization"
                  value={topicName}
                  onChange={(e) => setTopicName(e.target.value)}
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink mb-1.5">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-ink mb-1.5">Questions Count</label>
                  <select
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
                  >
                    <option value={3}>3 Questions</option>
                    <option value={5}>5 Questions</option>
                    <option value={10}>10 Questions</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <span>Generating Questions...</span>
                ) : (
                  <>
                    <Play size={14} />
                    <span>Start Practice Quiz</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Past Quiz History */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-ink px-1">
              <History size={16} className="text-ink-muted" />
              <span>Past Quiz Attempts ({history.length})</span>
            </div>

            {history.length === 0 ? (
              <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted">
                No quizzes attempted yet. Generate your first quiz on the left!
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((att) => {
                  const subj = subjects.find((s) => s.id === att.subject_id);
                  const isPass = att.percentage >= 60;
                  return (
                    <div
                      key={att.id}
                      className="bg-surface border border-border rounded-xl p-4 flex items-center justify-between shadow-xs hover:border-focus/40 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-heading font-semibold text-xs text-ink">
                            {subj ? subj.name : 'General Quiz'}
                          </span>
                          {att.topic_name && (
                            <span className="text-[11px] text-ink-muted bg-surface-muted px-2 py-0.5 rounded">
                              {att.topic_name}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-ink-muted font-mono">
                          {att.questions_count} questions • {new Date(att.created_at).toLocaleDateString()}
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <span
                            className={`font-mono font-bold text-sm ${
                              isPass ? 'text-good-leaf' : 'text-weak-rose'
                            }`}
                          >
                            {att.percentage.toFixed(0)}%
                          </span>
                          <span className="text-[10px] text-ink-muted block">
                            {att.user_marks} / {att.total_marks} marks
                          </span>
                        </div>
                        <button
                          onClick={() => handleReviewAttempt(att.id)}
                          className="px-3 py-1.5 rounded-lg border border-border bg-surface-muted hover:bg-border text-xs font-semibold text-ink transition-colors"
                        >
                          Review
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ACTIVE QUIZ SESSION */}
      {activeAttempt && activeAttempt.questions && activeAttempt.questions.length > 0 && (
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Quiz Stepper Header */}
          <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-xs text-ink-muted font-medium">
                Question {currentQIndex + 1} of {activeAttempt.questions.length}
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className="font-heading font-bold text-sm text-ink">
                  {activeAttempt.questions[currentQIndex].topic_name || 'Practice Question'}
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-surface-muted text-ink-muted">
                  {activeAttempt.questions[currentQIndex].difficulty}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-semibold text-focus">
                {Object.keys(userAnswers).length} / {activeAttempt.questions.length} Answered
              </span>
            </div>
          </div>

          {/* Question Card */}
          {(() => {
            const currentQ = activeAttempt.questions[currentQIndex];
            const currentAns = userAnswers[currentQ.id] || '';
            const opts = currentQ.options || [];

            return (
              <div className="bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-sm space-y-6">
                <h3 className="font-heading font-semibold text-base md:text-lg text-ink leading-relaxed">
                  {currentQ.question_text}
                </h3>

                {/* Options List */}
                {opts.length > 0 ? (
                  <div className="space-y-3">
                    {opts.map((opt, oIdx) => {
                      const isSelected = currentAns === opt;
                      return (
                        <button
                          key={oIdx}
                          type="button"
                          onClick={() => handleSelectAnswer(currentQ.id, opt)}
                          className={`w-full text-left p-4 rounded-xl border text-xs font-medium transition-all flex items-center gap-3 ${
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
                  <div>
                    <label className="block text-xs font-medium text-ink-muted mb-2">
                      Enter your written answer / code:
                    </label>
                    <textarea
                      rows={4}
                      value={currentAns}
                      onChange={(e) => handleSelectAnswer(currentQ.id, e.target.value)}
                      placeholder="Type your explanation or solution here..."
                      className="w-full p-3 rounded-xl border border-border bg-canvas text-xs text-ink font-mono focus:outline-none focus:border-focus"
                    />
                  </div>
                )}

                {/* Navigation Stepper Buttons */}
                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <button
                    type="button"
                    disabled={currentQIndex === 0}
                    onClick={() => setCurrentQIndex((prev) => prev - 1)}
                    className="px-3.5 py-2 rounded-xl border border-border bg-surface hover:bg-surface-muted text-xs font-semibold text-ink flex items-center gap-1.5 disabled:opacity-40"
                  >
                    <ChevronLeft size={16} />
                    <span>Previous</span>
                  </button>

                  {currentQIndex < activeAttempt.questions.length - 1 ? (
                    <button
                      type="button"
                      onClick={() => setCurrentQIndex((prev) => prev + 1)}
                      className="px-4 py-2 rounded-xl bg-surface border border-border hover:bg-surface-muted text-xs font-semibold text-ink flex items-center gap-1.5"
                    >
                      <span>Next</span>
                      <ChevronRight size={16} />
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={handleSubmitQuiz}
                      className="px-5 py-2 rounded-xl bg-good-leaf text-white text-xs font-semibold hover:bg-good-leaf/90 shadow-sm flex items-center gap-1.5"
                    >
                      <CheckCircle size={16} />
                      <span>{submitting ? 'Submitting...' : 'Submit & Evaluate'}</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* SUBMITTED EVALUATION REVIEW */}
      {submittedResult && (
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Score Hero */}
          <div className="bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-sm text-center space-y-4">
            <div className="inline-flex h-16 w-16 rounded-2xl bg-focus/10 text-focus items-center justify-center">
              <Award size={32} />
            </div>
            <div>
              <span className="text-xs text-ink-muted uppercase font-semibold tracking-wider">Evaluation Completed</span>
              <h2 className="font-heading font-bold text-3xl text-ink mt-1">
                Score: {submittedResult.percentage.toFixed(0)}%
              </h2>
              <p className="text-xs text-ink-muted mt-1 font-mono">
                {submittedResult.user_marks} of {submittedResult.total_marks} Marks Earned
              </p>
            </div>

            <div className="pt-2 flex justify-center gap-3">
              <button
                onClick={() => {
                  setSubmittedResult(null);
                  setActiveAttempt(null);
                }}
                className="px-4 py-2 rounded-xl bg-focus text-white text-xs font-semibold hover:bg-focus-hover shadow-sm transition-colors flex items-center gap-2"
              >
                <RotateCcw size={14} />
                <span>Practice Another Quiz</span>
              </button>
            </div>
          </div>

          {/* Questions Review List */}
          <div className="space-y-4">
            <h3 className="font-heading font-bold text-sm text-ink px-1">Detailed Explanations & Rationale</h3>

            {submittedResult.questions?.map((q, idx) => {
              const ans = submittedResult.answers?.find((a) => a.question_id === q.id);
              const isCorrect = ans ? ans.is_correct : false;

              return (
                <div
                  key={q.id}
                  className={`bg-surface border rounded-2xl p-5 md:p-6 space-y-3 ${
                    isCorrect ? 'border-good-leaf/30' : 'border-weak-rose/30'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      {isCorrect ? (
                        <CheckCircle size={20} className="text-good-leaf flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle size={20} className="text-weak-rose flex-shrink-0 mt-0.5" />
                      )}
                      <div>
                        <span className="font-mono text-xs font-bold text-ink">Q{idx + 1}: </span>
                        <span className="text-xs text-ink font-medium">{q.question_text}</span>
                      </div>
                    </div>
                    <span
                      className={`text-xs font-mono font-bold ${
                        isCorrect ? 'text-good-leaf' : 'text-weak-rose'
                      }`}
                    >
                      {ans?.score || 0} / {q.max_marks} pts
                    </span>
                  </div>

                  <div className="text-xs space-y-1.5 bg-canvas/70 p-3.5 rounded-xl border border-border/60">
                    <div className="flex items-center gap-2">
                      <span className="text-ink-muted font-medium">Your Answer:</span>
                      <span className={`font-semibold ${isCorrect ? 'text-good-leaf' : 'text-weak-rose'}`}>
                        {ans?.user_answer || '(No answer provided)'}
                      </span>
                    </div>

                    {q.correct_answer && (
                      <div className="flex items-center gap-2">
                        <span className="text-ink-muted font-medium">Correct Answer:</span>
                        <span className="font-semibold text-ink">{q.correct_answer}</span>
                      </div>
                    )}

                    {(q.explanation || ans?.explanation) && (
                      <div className="pt-2 border-t border-border/40 text-ink/90 leading-relaxed">
                        <strong className="text-ink font-medium">Explanation: </strong>
                        {q.explanation || ans?.explanation}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
