import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Search,
  Network,
  Sparkles,
  FileText,
  Layers,
  ArrowRight,
  ExternalLink,
  CheckCircle,
} from 'lucide-react';
import { api } from '../../lib/api';
import { DocumentSearchResult, KnowledgeMapData, Subject } from '../../types';

export const KnowledgeView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'search' | 'map'>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<number | undefined>(undefined);
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<DocumentSearchResult | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Knowledge map state
  const [knowledgeMap, setKnowledgeMap] = useState<KnowledgeMapData | null>(null);
  const [loadingMap, setLoadingMap] = useState(false);

  useEffect(() => {
    api.getSubjects().then(setSubjects).catch(console.error);
    loadKnowledgeMap();
  }, []);

  const loadKnowledgeMap = async () => {
    try {
      setLoadingMap(true);
      const data = await api.getKnowledgeMap();
      setKnowledgeMap(data);
    } catch (err) {
      console.error('Failed to load knowledge map:', err);
    } finally {
      setLoadingMap(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setSearching(true);
      setSearchError(null);
      const res = await api.searchDocuments(searchQuery.trim(), selectedSubject);
      setSearchResult(res);
    } catch (err: any) {
      setSearchError(err.message || 'Semantic search failed.');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Academic Knowledge Base
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Query dense vector embeddings across all your uploaded course materials with grounded chunk citations.
          </p>
        </div>

        {/* Sub-tab toggle */}
        <div className="flex items-center p-1 rounded-xl bg-surface border border-border">
          <button
            onClick={() => setActiveSubTab('search')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              activeSubTab === 'search'
                ? 'bg-focus text-white shadow-sm'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            <Search size={14} />
            <span>Semantic Search</span>
          </button>
          <button
            onClick={() => setActiveSubTab('map')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              activeSubTab === 'map'
                ? 'bg-focus text-white shadow-sm'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            <Network size={14} />
            <span>Knowledge Map</span>
          </button>
        </div>
      </div>

      {activeSubTab === 'search' && (
        <div className="space-y-6 max-w-4xl mx-auto">
          {/* Search Bar Bar */}
          <form onSubmit={handleSearch} className="bg-surface border border-border rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-muted" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Ask a technical concept (e.g., 'What is Bellman-Ford algorithm complexity?', 'ACID properties')..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-canvas text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:border-focus"
                />
              </div>

              <select
                value={selectedSubject ?? ''}
                onChange={(e) => setSelectedSubject(e.target.value ? Number(e.target.value) : undefined)}
                className="rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink focus:outline-none focus:border-focus sm:w-48"
              >
                <option value="">All Subjects</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>

              <button
                type="submit"
                disabled={searching || !searchQuery.trim()}
                className="py-2.5 px-5 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                {searching ? (
                  <span>Searching...</span>
                ) : (
                  <>
                    <Sparkles size={14} />
                    <span>Retrieve</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {searchError && (
            <div className="p-4 rounded-xl bg-weak-rose/10 border border-weak-rose/20 text-weak-rose text-xs">
              {searchError}
            </div>
          )}

          {/* Results Display */}
          {searchResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-ink-muted px-1">
                <span>
                  Retrieved <strong className="text-ink">{searchResult.total_results} chunks</strong> for "{searchResult.query}"
                </span>
                <span className="font-mono text-[11px]">User Scope #{searchResult.user_id || 1}</span>
              </div>

              {searchResult.chunks.length === 0 ? (
                <div className="bg-surface border border-border rounded-2xl p-8 text-center text-xs text-ink-muted">
                  No matching vector chunks found. Try broader keywords or ensure course materials are indexed.
                </div>
              ) : (
                <div className="space-y-3">
                  {searchResult.chunks.map((chk, idx) => (
                    <div
                      key={chk.id || idx}
                      className="bg-surface border border-border hover:border-focus/50 rounded-2xl p-5 shadow-sm space-y-3 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText size={16} className="text-focus" />
                          <span className="font-semibold text-xs text-ink">{chk.document_name}</span>
                          <span className="text-[11px] text-ink-muted font-mono bg-surface-muted px-2 py-0.5 rounded">
                            Page {chk.page_number}
                          </span>
                        </div>
                        {chk.similarity_score !== undefined && (
                          <div className="flex items-center gap-1.5 text-[11px] font-mono">
                            <span className="text-ink-muted">Score:</span>
                            <span className="font-bold text-focus">
                              {(chk.similarity_score * 100).toFixed(1)}%
                            </span>
                          </div>
                        )}
                      </div>

                      <p className="text-xs leading-relaxed text-ink/90 whitespace-pre-wrap font-sans bg-canvas/70 p-3 rounded-xl border border-border/40">
                        {chk.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'map' && (
        <div className="space-y-6 max-w-4xl mx-auto">
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <h2 className="font-heading font-bold text-base text-ink">Topic Mastery Graph</h2>
                <p className="text-xs text-ink-muted">Curriculum hierarchy and current conceptual mastery level</p>
              </div>
              {knowledgeMap?.mastery_percentage !== undefined && (
                <div className="text-right">
                  <span className="text-xs text-ink-muted block">Overall Mastery</span>
                  <span className="font-mono font-bold text-lg text-good-leaf">
                    {knowledgeMap.mastery_percentage.toFixed(0)}%
                  </span>
                </div>
              )}
            </div>

            {loadingMap ? (
              <div className="py-12 text-center text-xs text-ink-muted">Loading knowledge topology...</div>
            ) : !knowledgeMap || (!knowledgeMap.subjects?.length && !knowledgeMap.nodes?.length) ? (
              <div className="py-12 text-center text-xs text-ink-muted space-y-2">
                <Network size={32} className="mx-auto text-ink-muted" />
                <p>Knowledge map will automatically generate as you complete quizzes and syllabus topics.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {knowledgeMap.subjects && knowledgeMap.subjects.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {knowledgeMap.subjects.map((s) => (
                      <div key={s.id} className="p-4 rounded-xl border border-border bg-canvas space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="font-heading font-semibold text-xs text-ink">{s.name}</span>
                          <span className="text-xs font-mono font-bold text-focus">{s.mastery}%</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-border overflow-hidden">
                          <div
                            className="h-full bg-focus transition-all duration-300"
                            style={{ width: `${Math.min(100, Math.max(0, s.mastery))}%` }}
                          />
                        </div>
                        {s.topics && s.topics.length > 0 && (
                          <div className="pt-2 flex flex-wrap gap-1.5">
                            {s.topics.map((t, idx) => (
                              <span
                                key={idx}
                                className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                                  t.mastery >= 70
                                    ? 'bg-good-leaf/10 text-good-leaf'
                                    : t.mastery >= 40
                                    ? 'bg-spark-amber/10 text-spark-amber'
                                    : 'bg-weak-rose/10 text-weak-rose'
                                }`}
                              >
                                {t.name} ({t.mastery}%)
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}

                {/* Graph nodes preview if returned */}
                {knowledgeMap.nodes && knowledgeMap.nodes.length > 0 && (
                  <div className="p-4 rounded-xl border border-border bg-surface-muted/30 space-y-3">
                    <span className="text-xs font-semibold text-ink block">Concept Nodes ({knowledgeMap.nodes.length})</span>
                    <div className="flex flex-wrap gap-2">
                      {knowledgeMap.nodes.map((node) => (
                        <div
                          key={node.id}
                          className="px-3 py-1.5 rounded-lg border border-border bg-surface text-xs flex items-center gap-2 shadow-xs"
                        >
                          <span className="font-medium text-ink">{node.name}</span>
                          <span className="text-[10px] font-mono text-ink-muted">
                            {(node.mastery * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
