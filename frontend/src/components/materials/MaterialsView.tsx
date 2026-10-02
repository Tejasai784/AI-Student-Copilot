import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Layers,
  Search,
  Filter,
  RefreshCw,
  Eye,
  FileCheck,
} from 'lucide-react';
import { api } from '../../lib/api';
import { DocumentItem, DocumentChunkItem, Subject } from '../../types';

export const MaterialsView: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [selectedDocChunks, setSelectedDocChunks] = useState<{ doc: DocumentItem; chunks: DocumentChunkItem[] } | null>(null);
  const [loadingChunks, setLoadingChunks] = useState(false);

  // Form state
  const [targetSubjectId, setTargetSubjectId] = useState<number | ''>('');
  const [docType, setDocType] = useState('Lecture Notes');
  const [unitNumber, setUnitNumber] = useState<number | ''>('');
  const [topicName, setTopicName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [docs, subs] = await Promise.all([
        api.getDocuments(selectedSubject),
        api.getSubjects(),
      ]);
      setDocuments(docs);
      setSubjects(subs);
      if (subs.length > 0 && targetSubjectId === '') {
        setTargetSubjectId(subs[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load materials data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSubject]);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError(null);
    setUploadSuccess(null);

    const files = fileInputRef.current?.files;
    if (!files || files.length === 0) {
      setUploadError('Please choose a file to upload.');
      return;
    }
    if (!targetSubjectId) {
      setUploadError('Please select a subject for this material.');
      return;
    }

    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject_id', String(targetSubjectId));
    formData.append('document_type', docType);
    if (unitNumber) formData.append('unit_number', String(unitNumber));
    if (topicName.trim()) formData.append('topic_name', topicName.trim());

    try {
      setUploading(true);
      await api.uploadDocument(formData);
      setUploadSuccess(`"${file.name}" uploaded and indexed successfully.`);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setTopicName('');
      setUnitNumber('');
      await loadData();
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed. Ensure file is valid PDF/DOCX/TXT/MD under 50MB.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"? This removes all vector chunks and search embeddings.`)) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      if (selectedDocChunks?.doc.id === docId) {
        setSelectedDocChunks(null);
      }
      await loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleInspectChunks = async (doc: DocumentItem) => {
    try {
      setLoadingChunks(true);
      const chunks = await api.getDocumentChunks(doc.id);
      setSelectedDocChunks({ doc, chunks });
    } catch (err: any) {
      alert(`Could not load chunks: ${err.message}`);
    } finally {
      setLoadingChunks(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'READY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-good-leaf/10 text-good-leaf">
            <CheckCircle size={12} />
            <span>Ready / Indexed</span>
          </span>
        );
      case 'PROCESSING':
      case 'INDEXING':
      case 'UPLOADING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-spark-amber/10 text-spark-amber">
            <RefreshCw size={12} className="animate-spin" />
            <span>{status}</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-weak-rose/10 text-weak-rose">
            <AlertCircle size={12} />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-muted text-ink-muted">
            <Clock size={12} />
            <span>{status}</span>
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
            Course Materials & Library
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Upload syllabi, notes, textbooks, and past papers. Automatically chunked and indexed into the RAG vector store.
          </p>
        </div>
        <button
          onClick={loadData}
          className="self-start sm:self-auto p-2 rounded-lg border border-border bg-surface hover:bg-surface-muted text-ink transition-colors flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Form Card */}
        <div className="lg:col-span-1 bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-5 h-fit">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-focus/10 text-focus flex items-center justify-center">
              <UploadCloud size={20} />
            </div>
            <div>
              <h2 className="font-heading font-bold text-base text-ink">Upload Academic Material</h2>
              <p className="text-xs text-ink-muted">PDF, DOCX, TXT, MD, CSV (max 50MB)</p>
            </div>
          </div>

          {uploadError && (
            <div className="p-3 rounded-lg bg-weak-rose/10 border border-weak-rose/20 text-weak-rose text-xs flex items-start gap-2">
              <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
              <span>{uploadError}</span>
            </div>
          )}

          {uploadSuccess && (
            <div className="p-3 rounded-lg bg-good-leaf/10 border border-good-leaf/20 text-good-leaf text-xs flex items-start gap-2">
              <CheckCircle size={16} className="flex-shrink-0 mt-0.5" />
              <span>{uploadSuccess}</span>
            </div>
          )}

          <form onSubmit={handleFileUpload} className="space-y-4 text-xs">
            <div>
              <label className="block font-medium text-ink mb-1.5">File Document *</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md,.csv,.json"
                className="w-full text-xs text-ink file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-surface-muted file:text-ink hover:file:bg-border cursor-pointer border border-border rounded-lg p-1.5 bg-canvas"
              />
            </div>

            <div>
              <label className="block font-medium text-ink mb-1.5">Subject *</label>
              <select
                value={targetSubjectId}
                onChange={(e) => setTargetSubjectId(Number(e.target.value))}
                className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
              >
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-ink mb-1.5">Document Type</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
                >
                  <option value="Lecture Notes">Lecture Notes</option>
                  <option value="Syllabus">Syllabus</option>
                  <option value="Textbook Chapter">Textbook Chapter</option>
                  <option value="Past Exam">Past Exam</option>
                  <option value="Reference">Reference</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-ink mb-1.5">Unit (Optional)</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  placeholder="e.g. 1"
                  value={unitNumber}
                  onChange={(e) => setUnitNumber(e.target.value ? Number(e.target.value) : '')}
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
                />
              </div>
            </div>

            <div>
              <label className="block font-medium text-ink mb-1.5">Topic Focus (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Dynamic Programming, Normalization"
                value={topicName}
                onChange={(e) => setTopicName(e.target.value)}
                className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-ink text-xs focus:outline-none focus:border-focus"
              />
            </div>

            <button
              type="submit"
              disabled={uploading}
              className="w-full py-2.5 px-4 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Processing & Indexing...</span>
                </>
              ) : (
                <>
                  <UploadCloud size={16} />
                  <span>Upload & Embed</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Documents Table / List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Filter size={14} className="text-ink-muted" />
              <span className="text-xs font-semibold text-ink">Filter by Subject:</span>
              <select
                value={selectedSubject ?? ''}
                onChange={(e) => setSelectedSubject(e.target.value ? Number(e.target.value) : undefined)}
                className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-focus"
              >
                <option value="">All Subjects ({documents.length})</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-xs text-ink-muted">
              Total Chunks in Vector Store:{' '}
              <span className="font-semibold text-ink">
                {documents.reduce((acc, d) => acc + (d.total_chunks || d.chunks || 0), 0)}
              </span>
            </div>
          </div>

          {documents.length === 0 ? (
            <div className="bg-surface border border-border rounded-2xl p-12 text-center space-y-3">
              <div className="h-12 w-12 rounded-xl bg-surface-muted text-ink-muted flex items-center justify-center mx-auto">
                <FileText size={24} />
              </div>
              <h3 className="font-heading font-semibold text-base text-ink">No course materials uploaded yet</h3>
              <p className="text-xs text-ink-muted max-w-sm mx-auto">
                Upload your course syllabus or lecture notes to enable AI tutor citations and deep knowledge retrieval.
              </p>
            </div>
          ) : (
            <div className="bg-surface border border-border rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border bg-surface-muted/50 text-ink-muted font-medium">
                      <th className="py-3 px-4">Document</th>
                      <th className="py-3 px-4">Subject</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-center">Pages / Chunks</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {documents.map((doc) => {
                      const subj = subjects.find((s) => s.id === doc.subject_id);
                      return (
                        <tr key={doc.id} className="hover:bg-surface-muted/30 transition-colors">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2.5">
                              <FileText size={18} className="text-focus flex-shrink-0" />
                              <div className="truncate max-w-[200px] sm:max-w-xs">
                                <span className="font-semibold text-ink block truncate" title={doc.filename}>
                                  {doc.filename}
                                </span>
                                <span className="text-[11px] text-ink-muted">
                                  {doc.document_type || 'Document'} • {doc.size_kb ? `${doc.size_kb} KB` : 'Indexed'}
                                </span>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded bg-surface-muted text-ink text-[11px] font-medium">
                              {subj ? subj.name : `Subject #${doc.subject_id}`}
                            </span>
                          </td>
                          <td className="py-3 px-4">{getStatusBadge(doc.status)}</td>
                          <td className="py-3 px-4 text-center font-mono text-[11px] text-ink">
                            {doc.total_pages || doc.pages || 1}p / {doc.total_chunks || doc.chunks || 0}c
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleInspectChunks(doc)}
                                title="Inspect Vector Chunks"
                                className="p-1.5 rounded-lg border border-border hover:bg-surface-muted text-ink transition-colors"
                              >
                                <Layers size={14} />
                              </button>
                              <button
                                onClick={() => handleDelete(doc.id, doc.filename)}
                                title="Delete Document & Chunks"
                                className="p-1.5 rounded-lg border border-border hover:bg-weak-rose/10 hover:text-weak-rose text-ink-muted transition-colors"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Modal / Panel for Inspected Chunks */}
          {selectedDocChunks && (
            <div className="bg-surface border border-focus/30 rounded-2xl p-6 shadow-md space-y-4 animate-in fade-in">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Layers size={18} className="text-focus" />
                  <h3 className="font-heading font-bold text-sm text-ink">
                    Vector Store Chunks: {selectedDocChunks.doc.filename}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedDocChunks(null)}
                  className="text-xs text-ink-muted hover:text-ink font-semibold px-2 py-1 rounded border border-border hover:bg-surface-muted"
                >
                  Close
                </button>
              </div>

              {loadingChunks ? (
                <div className="py-8 text-center text-xs text-ink-muted">Loading chunks...</div>
              ) : selectedDocChunks.chunks.length === 0 ? (
                <div className="py-6 text-center text-xs text-ink-muted">No chunks found for this document.</div>
              ) : (
                <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                  {selectedDocChunks.chunks.map((chk) => (
                    <div key={chk.id} className="p-3 rounded-xl border border-border bg-canvas text-xs space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] text-ink-muted font-mono">
                        <span>Chunk #{chk.chunk_index + 1} (Page {chk.page_number})</span>
                        {chk.token_count && <span>~{chk.token_count} tokens</span>}
                      </div>
                      <p className="text-ink text-[12px] leading-relaxed whitespace-pre-wrap font-sans bg-surface/50 p-2.5 rounded-lg border border-border/50">
                        {chk.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
