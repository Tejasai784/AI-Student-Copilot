import React, { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  CheckCircle2,
  Circle,
  BookOpen,
  Layers,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  FolderPlus,
} from 'lucide-react';
import { api } from '../../lib/api';
import { Subject, SyllabusTopic } from '../../types';

export const SyllabusView: React.FC = () => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);
  const [subjectDetails, setSubjectDetails] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Modals & forms
  const [showAddSubject, setShowAddSubject] = useState(false);
  const [newSubjName, setNewSubjName] = useState('');
  const [newSubjCode, setNewSubjCode] = useState('');
  const [newSubjSemester, setNewSubjSemester] = useState('6th Semester');
  const [newSubjDesc, setNewSubjDesc] = useState('');

  const [showAddTopic, setShowAddTopic] = useState(false);
  const [newTopicUnit, setNewTopicUnit] = useState<number>(1);
  const [newTopicName, setNewTopicName] = useState('');

  const loadSubjects = async () => {
    try {
      setLoading(true);
      const subs = await api.getSubjects();
      setSubjects(subs);
      if (subs.length > 0 && selectedSubjectId === null) {
        setSelectedSubjectId(subs[0].id);
      }
    } catch (err) {
      console.error('Failed to load subjects:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubjects();
  }, []);

  useEffect(() => {
    if (selectedSubjectId) {
      loadSubjectDetails(selectedSubjectId);
    }
  }, [selectedSubjectId]);

  const loadSubjectDetails = async (id: number) => {
    try {
      setLoadingDetails(true);
      const details = await api.getSubject(id);
      setSubjectDetails(details);
    } catch (err) {
      console.error('Failed to load subject details:', err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleToggleTopic = async (topicId: number) => {
    if (!selectedSubjectId) return;
    try {
      await api.toggleTopic(selectedSubjectId, topicId);
      await loadSubjectDetails(selectedSubjectId);
      await loadSubjects();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSubjName.trim() || !newSubjCode.trim()) return;
    try {
      const created = await api.createSubject({
        name: newSubjName.trim(),
        code: newSubjCode.trim(),
        semester: newSubjSemester,
        description: newSubjDesc.trim() || undefined,
      });
      setShowAddSubject(false);
      setNewSubjName('');
      setNewSubjCode('');
      setNewSubjDesc('');
      await loadSubjects();
      setSelectedSubjectId(created.id);
    } catch (err: any) {
      alert(`Failed to add subject: ${err.message}`);
    }
  };

  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSubjectId || !newTopicName.trim()) return;
    try {
      await api.addTopic(selectedSubjectId, {
        unit_number: Number(newTopicUnit),
        topic_name: newTopicName.trim(),
      });
      setShowAddTopic(false);
      setNewTopicName('');
      await loadSubjectDetails(selectedSubjectId);
      await loadSubjects();
    } catch (err: any) {
      alert(`Failed to add topic: ${err.message}`);
    }
  };

  // Group topics by unit
  const topicsByUnit: Record<number, any[]> = {};
  if (subjectDetails?.topics) {
    subjectDetails.topics.forEach((t: any) => {
      const u = t.unit_number || 1;
      if (!topicsByUnit[u]) topicsByUnit[u] = [];
      topicsByUnit[u].push(t);
    });
  }

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Syllabus & Course Structure
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Browse units, track mastery completion, and align AI tutoring with your curriculum.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddSubject(true)}
            className="px-3.5 py-2 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center gap-1.5"
          >
            <FolderPlus size={15} />
            <span>Add Subject</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left: Subjects List */}
        <div className="lg:col-span-1 space-y-3">
          <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider block px-1">
            Registered Subjects ({subjects.length})
          </span>

          {subjects.map((s) => {
            const isSelected = s.id === selectedSubjectId;
            return (
              <button
                key={s.id}
                onClick={() => setSelectedSubjectId(s.id)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-focus bg-surface shadow-sm ring-1 ring-focus/30'
                    : 'border-border bg-surface/60 hover:bg-surface text-ink'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-heading font-bold text-xs text-ink">{s.code}</span>
                  <span className="text-[11px] font-mono font-medium text-focus">
                    {s.progress_percentage ?? 0}%
                  </span>
                </div>
                <div className="text-xs font-medium text-ink mt-1 truncate">{s.name}</div>
                <div className="text-[11px] text-ink-muted mt-2 flex items-center justify-between">
                  <span>{s.topics_count ?? 0} topics</span>
                  <span>{s.completed_topics ?? 0} completed</span>
                </div>
                {/* Progress bar */}
                <div className="w-full h-1.5 rounded-full bg-border mt-2 overflow-hidden">
                  <div
                    className="h-full bg-focus transition-all duration-300"
                    style={{ width: `${s.progress_percentage ?? 0}%` }}
                  />
                </div>
              </button>
            );
          })}
        </div>

        {/* Right: Subject Detail & Topics Tree */}
        <div className="lg:col-span-3 space-y-6">
          {subjectDetails ? (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-md bg-focus/10 text-focus font-mono font-bold text-xs">
                      {subjectDetails.code}
                    </span>
                    <h2 className="font-heading font-bold text-lg text-ink">{subjectDetails.name}</h2>
                  </div>
                  {subjectDetails.description && (
                    <p className="text-xs text-ink-muted mt-1 max-w-xl">{subjectDetails.description}</p>
                  )}
                </div>

                <button
                  onClick={() => setShowAddTopic(true)}
                  className="px-3 py-1.5 rounded-lg border border-border bg-surface-muted hover:bg-border text-xs font-semibold text-ink flex items-center gap-1.5 transition-colors self-start sm:self-auto"
                >
                  <Plus size={14} />
                  <span>Add Topic</span>
                </button>
              </div>

              {loadingDetails ? (
                <div className="py-12 text-center text-xs text-ink-muted">Loading topics...</div>
              ) : Object.keys(topicsByUnit).length === 0 ? (
                <div className="py-12 text-center text-xs text-ink-muted space-y-3">
                  <Layers size={32} className="mx-auto text-ink-muted" />
                  <p>No syllabus topics defined yet for this subject.</p>
                  <button
                    onClick={() => setShowAddTopic(true)}
                    className="px-3.5 py-1.5 rounded-lg bg-focus text-white text-xs font-semibold hover:bg-focus-hover transition-colors inline-block"
                  >
                    Add First Topic
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(topicsByUnit).map(([unit, topics]) => (
                    <div key={unit} className="border border-border/80 rounded-xl overflow-hidden bg-canvas/40">
                      <div className="bg-surface-muted/60 px-4 py-2.5 border-b border-border flex items-center justify-between">
                        <span className="font-heading font-semibold text-xs text-ink">
                          Unit {unit}
                        </span>
                        <span className="text-[11px] text-ink-muted font-mono">
                          {topics.filter((t) => t.is_completed).length} / {topics.length} done
                        </span>
                      </div>

                      <div className="divide-y divide-border/60">
                        {topics.map((t) => (
                          <div
                            key={t.id}
                            onClick={() => handleToggleTopic(t.id)}
                            className="px-4 py-3 flex items-center justify-between hover:bg-surface/80 cursor-pointer transition-colors group"
                          >
                            <div className="flex items-center gap-3">
                              {t.is_completed ? (
                                <CheckCircle2 size={18} className="text-good-leaf flex-shrink-0" />
                              ) : (
                                <Circle size={18} className="text-ink-muted/50 group-hover:text-focus flex-shrink-0" />
                              )}
                              <span
                                className={`text-xs font-medium ${
                                  t.is_completed ? 'line-through text-ink-muted' : 'text-ink'
                                }`}
                              >
                                {t.topic_name}
                              </span>
                            </div>

                            <span className="text-[11px] text-ink-muted opacity-0 group-hover:opacity-100 transition-opacity">
                              Click to toggle
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted">
              Select a subject from the left panel to inspect its topics and units.
            </div>
          )}
        </div>
      </div>

      {/* Add Subject Modal */}
      {showAddSubject && (
        <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-xl max-w-md w-full space-y-4">
            <h3 className="font-heading font-bold text-base text-ink">Register New Subject</h3>
            <form onSubmit={handleCreateSubject} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-ink mb-1">Subject Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Distributed Operating Systems"
                  value={newSubjName}
                  onChange={(e) => setNewSubjName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink mb-1">Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CS601"
                    value={newSubjCode}
                    onChange={(e) => setNewSubjCode(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                  />
                </div>
                <div>
                  <label className="block font-medium text-ink mb-1">Semester</label>
                  <input
                    type="text"
                    value={newSubjSemester}
                    onChange={(e) => setNewSubjSemester(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                  />
                </div>
              </div>
              <div>
                <label className="block font-medium text-ink mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Course overview or prerequisites..."
                  value={newSubjDesc}
                  onChange={(e) => setNewSubjDesc(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddSubject(false)}
                  className="px-3 py-1.5 rounded-lg border border-border text-ink hover:bg-surface-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-focus text-white font-semibold hover:bg-focus-hover"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Topic Modal */}
      {showAddTopic && (
        <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-xl max-w-md w-full space-y-4">
            <h3 className="font-heading font-bold text-base text-ink">Add Syllabus Topic</h3>
            <form onSubmit={handleCreateTopic} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-ink mb-1">Unit Number</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  required
                  value={newTopicUnit}
                  onChange={(e) => setNewTopicUnit(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>
              <div>
                <label className="block font-medium text-ink mb-1">Topic Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Paxos Consensus Algorithm"
                  value={newTopicName}
                  onChange={(e) => setNewTopicName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddTopic(false)}
                  className="px-3 py-1.5 rounded-lg border border-border text-ink hover:bg-surface-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-focus text-white font-semibold hover:bg-focus-hover"
                >
                  Add Topic
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
