import React, { useState, useEffect } from 'react';
import {
  Server,
  Database,
  Layers,
  HardDrive,
  Cpu,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Activity,
} from 'lucide-react';
import { api } from '../../lib/api';
import { SystemDiagnosticsData } from '../../types';

export const DiagnosticsView: React.FC = () => {
  const [stats, setStats] = useState<SystemDiagnosticsData | null>(null);
  const [health, setHealth] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDiagnostics = async () => {
    try {
      setLoading(true);
      const [sData, hData] = await Promise.all([
        api.getSystemDiagnostics(),
        api.getHealthDiagnostics(),
      ]);
      setStats(sData);
      setHealth(hData);
    } catch (err) {
      console.error('Failed to load diagnostics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDiagnostics();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Developer Diagnostics & System Vitals
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Real-time backend infrastructure telemetry, database connection health, and vector store indices.
          </p>
        </div>
        <button
          onClick={loadDiagnostics}
          className="self-start sm:self-auto p-2 rounded-lg border border-border bg-surface hover:bg-surface-muted text-ink transition-colors flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Vitals</span>
        </button>
      </div>

      {loading ? (
        <div className="py-20 text-center text-xs text-ink-muted">Polling system vitals...</div>
      ) : (
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Health Status Banner */}
          <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                  health?.status === 'healthy'
                    ? 'bg-good-leaf/10 text-good-leaf'
                    : 'bg-weak-rose/10 text-weak-rose'
                }`}
              >
                <Activity size={20} />
              </div>
              <div>
                <span className="font-heading font-bold text-base text-ink block">
                  System Status: <span className="capitalize">{health?.status || 'Unknown'}</span>
                </span>
                <span className="text-xs text-ink-muted">
                  {health?.app_name || 'Autonomous Student Intelligence Platform'} • v{health?.version || '2.0.0'}
                </span>
              </div>
            </div>

            <span
              className={`px-3 py-1 rounded-full text-xs font-mono font-bold ${
                health?.database_connected
                  ? 'bg-good-leaf/10 text-good-leaf'
                  : 'bg-weak-rose/10 text-weak-rose'
              }`}
            >
              DB: {health?.database_connected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>

          {/* Metric Cards */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-2">
                <div className="flex items-center gap-2 text-ink-muted">
                  <Database size={16} />
                  <span className="text-xs font-medium">Subjects</span>
                </div>
                <span className="font-heading font-bold text-2xl text-ink block">
                  {stats.subjects_count}
                </span>
              </div>

              <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-2">
                <div className="flex items-center gap-2 text-ink-muted">
                  <Layers size={16} />
                  <span className="text-xs font-medium">Documents</span>
                </div>
                <span className="font-heading font-bold text-2xl text-ink block">
                  {stats.documents_count}
                </span>
              </div>

              <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-2">
                <div className="flex items-center gap-2 text-ink-muted">
                  <Layers size={16} />
                  <span className="text-xs font-medium">Vector Chunks</span>
                </div>
                <span className="font-heading font-bold text-2xl text-focus block">
                  {stats.vector_store_count}
                </span>
              </div>

              <div className="bg-surface border border-border rounded-2xl p-5 shadow-sm space-y-2">
                <div className="flex items-center gap-2 text-ink-muted">
                  <HardDrive size={16} />
                  <span className="text-xs font-medium">Storage Size</span>
                </div>
                <span className="font-heading font-bold text-2xl text-ink block">
                  {stats.upload_storage_mb} MB
                </span>
              </div>
            </div>
          )}

          {/* Environment & Database Details */}
          {stats && (
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4 text-xs font-mono">
              <h3 className="font-heading font-bold text-sm text-ink font-sans">
                Infrastructure Parameters
              </h3>
              <div className="space-y-2 bg-canvas p-4 rounded-xl border border-border">
                <div className="flex items-center justify-between">
                  <span className="text-ink-muted">Database Engine:</span>
                  <span className="text-ink font-bold">SQLite 3 (WAL mode)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-muted">Database Path (Masked):</span>
                  <span className="text-focus">{stats.database_url_masked}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-muted">Vector Store Engine:</span>
                  <span className="text-ink font-bold">In-Memory / Persistent Cosine Index</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-ink-muted">Total DB Chunks Count:</span>
                  <span className="text-ink">{stats.document_chunks_count}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
