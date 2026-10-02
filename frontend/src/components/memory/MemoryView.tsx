import React, { useState, useEffect } from 'react';
import {
  Brain,
  Plus,
  Trash2,
  ShieldCheck,
  Sparkles,
  Tag,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../lib/api';
import { MemoryItem } from '../../types';

export const MemoryView: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('');

  // Add memory modal/form
  const [showAddModal, setShowAddModal] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newType, setNewType] = useState('LEARNING_STYLE');
  const [newImportance, setNewImportance] = useState(3);
  const [saving, setSaving] = useState(false);

  const loadMemories = async () => {
    try {
      setLoading(true);
      const data = await api.getMemories(filterType || undefined);
      setMemories(data);
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [filterType]);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;

    try {
      setSaving(true);
      await api.addMemory({
        key: newKey.trim(),
        value: newValue.trim(),
        memory_type: newType,
        importance: newImportance,
        confidence: 1.0,
      });
      setShowAddModal(false);
      setNewKey('');
      setNewValue('');
      await loadMemories();
    } catch (err: any) {
      alert(`Failed to save memory: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMemory = async (id: number) => {
    if (!window.confirm('Delete this personalization memory fact?')) return;
    try {
      await api.deleteMemory(id);
      await loadMemories();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Personalization & Long-Term Memory
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Persisted learning style tendencies, strengths, and pedagogical preferences guiding the AI Tutor.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center gap-1.5"
          >
            <Plus size={14} />
            <span>Add Memory Fact</span>
          </button>
        </div>
      </div>

      {/* Privacy Callout Banner */}
      <div className="bg-surface border border-good-leaf/30 rounded-2xl p-4 shadow-xs flex items-center justify-between gap-4 max-w-4xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-good-leaf/10 text-good-leaf flex items-center justify-center flex-shrink-0">
            <ShieldCheck size={20} />
          </div>
          <div>
            <span className="font-semibold text-xs text-ink block">Privacy & Secret Filter Active</span>
            <span className="text-[11px] text-ink-muted">
              Credentials, API keys, and sensitive tokens are automatically masked and never persisted into long-term memory.
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Content */}
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-ink-muted">Type:</span>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-focus"
            >
              <option value="">All Memory Types ({memories.length})</option>
              <option value="LEARNING_STYLE">Learning Style</option>
              <option value="PREFERENCE">Preference</option>
              <option value="ACADEMIC_GOAL">Academic Goal</option>
              <option value="WEAK_TOPIC">Weak Topic</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-20 text-center text-xs text-ink-muted">Loading memory items...</div>
        ) : memories.length === 0 ? (
          <div className="bg-surface border border-border rounded-2xl p-12 text-center text-xs text-ink-muted space-y-2">
            <Brain size={32} className="mx-auto text-ink-muted" />
            <p>No memory items found. Add explicit preferences or chat with the tutor to form memories.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((mem) => (
              <div
                key={mem.id}
                className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-3 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-focus/10 text-focus">
                      {mem.memory_type}
                    </span>
                    <button
                      onClick={() => handleDeleteMemory(mem.id)}
                      className="text-ink-muted hover:text-weak-rose p-1 rounded transition-colors"
                      title="Delete memory fact"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <h3 className="font-heading font-semibold text-xs text-ink">{mem.key}</h3>
                  <p className="text-xs text-ink-muted leading-relaxed bg-canvas p-3 rounded-xl border border-border/60">
                    {mem.value}
                  </p>
                </div>

                <div className="flex items-center justify-between text-[10px] font-mono text-ink-muted pt-2 border-t border-border/40">
                  <span>Confidence: {(mem.confidence * 100).toFixed(0)}%</span>
                  <span>Importance: {mem.importance || 1} / 5</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Memory Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-xl max-w-md w-full space-y-4">
            <h3 className="font-heading font-bold text-base text-ink">Add Custom Memory Fact</h3>
            <form onSubmit={handleAddMemory} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-ink mb-1">Concept / Attribute Key *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Preferred explanation style, Math background"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>

              <div>
                <label className="block font-medium text-ink mb-1">Memory Value / Fact *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Prefers real-world analogy and step-by-step mathematical proofs before code implementations."
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink mb-1">Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                  >
                    <option value="LEARNING_STYLE">Learning Style</option>
                    <option value="PREFERENCE">Preference</option>
                    <option value="ACADEMIC_GOAL">Academic Goal</option>
                    <option value="WEAK_TOPIC">Weak Topic</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-ink mb-1">Importance (1-5)</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={newImportance}
                    onChange={(e) => setNewImportance(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-border text-ink hover:bg-surface-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-1.5 rounded-lg bg-focus text-white font-semibold hover:bg-focus-hover disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Memory'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
