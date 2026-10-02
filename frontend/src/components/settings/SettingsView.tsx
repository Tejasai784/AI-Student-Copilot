import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  User,
  Sun,
  Moon,
  Cpu,
  CheckCircle,
  Save,
  Shield,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../lib/api';
import { ProviderTelemetry, StudentProfile, StudentSettingsData } from '../../types';

export const SettingsView: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  // Profile state
  const [profile, setProfile] = useState<StudentProfile>({
    name: '',
    course: '',
    branch: '',
    year: '',
    semester: '',
  });

  // Settings state
  const [settingsData, setSettingsData] = useState<StudentSettingsData>({
    preferred_provider: 'auto',
    default_answer_style: 'Simple explanation',
    default_difficulty: 'medium',
    preferred_session_minutes: 45,
    weekly_study_hours: 10,
  });

  // Provider telemetry
  const [telemetry, setTelemetry] = useState<ProviderTelemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      setLoading(true);
      const [prof, stg, tel] = await Promise.all([
        api.getProfile(),
        api.getSettings(),
        api.getProvidersTelemetry(),
      ]);
      setProfile(prof);
      setSettingsData(stg);
      setTelemetry(tel);
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingProfile(true);
      setSaveSuccessMsg(null);
      await api.updateProfile(profile);
      setSaveSuccessMsg('Profile updated successfully.');
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      alert(`Profile update failed: ${err.message}`);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleUpdateSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingSettings(true);
      setSaveSuccessMsg(null);
      await api.updateSettings(settingsData);
      setSaveSuccessMsg('Learning preferences saved successfully.');
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      alert(`Settings update failed: ${err.message}`);
    } finally {
      setSavingSettings(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-canvas p-6 md:p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-ink tracking-tight">
            Settings & Student Profile
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Configure your student identity, learning preferences, appearance, and AI provider routing.
          </p>
        </div>
      </div>

      {saveSuccessMsg && (
        <div className="max-w-4xl mx-auto p-4 rounded-xl bg-good-leaf/10 border border-good-leaf/20 text-good-leaf text-xs font-semibold flex items-center gap-2">
          <CheckCircle size={16} />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Student Profile Card */}
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center gap-3 border-b border-border pb-4">
            <div className="h-10 w-10 rounded-xl bg-focus/10 text-focus flex items-center justify-center">
              <User size={20} />
            </div>
            <div>
              <h2 className="font-heading font-bold text-base text-ink">Academic Identity</h2>
              <p className="text-xs text-ink-muted">Personalizes tutor tone and curriculum scope</p>
            </div>
          </div>

          <form onSubmit={handleUpdateProfile} className="space-y-4 text-xs">
            <div>
              <label className="block font-medium text-ink mb-1">Full Name</label>
              <input
                type="text"
                value={profile.name}
                onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
              />
            </div>

            <div>
              <label className="block font-medium text-ink mb-1">Degree / Course</label>
              <input
                type="text"
                value={profile.course}
                onChange={(e) => setProfile({ ...profile, course: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-ink mb-1">Branch</label>
                <input
                  type="text"
                  value={profile.branch}
                  onChange={(e) => setProfile({ ...profile, branch: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>

              <div>
                <label className="block font-medium text-ink mb-1">Year</label>
                <input
                  type="text"
                  value={profile.year}
                  onChange={(e) => setProfile({ ...profile, year: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>
            </div>

            <div>
              <label className="block font-medium text-ink mb-1">Current Semester</label>
              <input
                type="text"
                value={profile.semester}
                onChange={(e) => setProfile({ ...profile, semester: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
              />
            </div>

            <button
              type="submit"
              disabled={savingProfile}
              className="w-full py-2.5 px-4 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Save size={14} />
              <span>{savingProfile ? 'Saving Profile...' : 'Save Profile'}</span>
            </button>
          </form>
        </div>

        {/* Learning Preferences Card */}
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center gap-3 border-b border-border pb-4">
            <div className="h-10 w-10 rounded-xl bg-spark-amber/10 text-spark-amber flex items-center justify-center">
              <Sparkles size={20} />
            </div>
            <div>
              <h2 className="font-heading font-bold text-base text-ink">Tutor Pedagogical Preferences</h2>
              <p className="text-xs text-ink-muted">Tailor explanation styles and question difficulty</p>
            </div>
          </div>

          <form onSubmit={handleUpdateSettings} className="space-y-4 text-xs">
            <div>
              <label className="block font-medium text-ink mb-1">Default Explanation Style</label>
              <select
                value={settingsData.default_answer_style}
                onChange={(e) => setSettingsData({ ...settingsData, default_answer_style: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
              >
                <option value="Simple explanation">Simple Explanation (Plain English)</option>
                <option value="Deep dive">Deep Dive (Mathematical Proofs & Rigor)</option>
                <option value="Analogies only">Intuition & Real-World Analogies</option>
                <option value="Code-first">Code-First Implementations</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-ink mb-1">Default Difficulty</label>
                <select
                  value={settingsData.default_difficulty}
                  onChange={(e) => setSettingsData({ ...settingsData, default_difficulty: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                >
                  <option value="easy">Easy (Fundamentals)</option>
                  <option value="medium">Medium (Standard College)</option>
                  <option value="hard">Hard (GATE / Competition)</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-ink mb-1">Session Target (Min)</label>
                <input
                  type="number"
                  min="15"
                  max="180"
                  step="15"
                  value={settingsData.preferred_session_minutes}
                  onChange={(e) =>
                    setSettingsData({
                      ...settingsData,
                      preferred_session_minutes: Number(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
                />
              </div>
            </div>

            <div>
              <label className="block font-medium text-ink mb-1">Weekly Target Study Hours</label>
              <input
                type="number"
                min="1"
                max="60"
                value={settingsData.weekly_study_hours}
                onChange={(e) =>
                  setSettingsData({
                    ...settingsData,
                    weekly_study_hours: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 rounded-lg border border-border bg-canvas text-ink focus:outline-none focus:border-focus"
              />
            </div>

            <button
              type="submit"
              disabled={savingSettings}
              className="w-full py-2.5 px-4 rounded-xl bg-focus text-white font-semibold text-xs hover:bg-focus-hover shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Save size={14} />
              <span>{savingSettings ? 'Saving Preferences...' : 'Save Preferences'}</span>
            </button>
          </form>
        </div>

        {/* Appearance & Studio Theme */}
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 border-b border-border pb-4">
            <div className="h-10 w-10 rounded-xl bg-surface-muted text-ink flex items-center justify-center">
              {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
            </div>
            <div>
              <h2 className="font-heading font-bold text-base text-ink">Appearance & Theme</h2>
              <p className="text-xs text-ink-muted">Calm Study Studio color palette</p>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl border border-border bg-canvas">
            <div>
              <span className="text-xs font-semibold text-ink block">
                Current Theme: <span className="capitalize text-focus font-bold">{theme}</span>
              </span>
              <span className="text-[11px] text-ink-muted">High-contrast WCAG AA accessible</span>
            </div>

            <button
              onClick={toggleTheme}
              className="px-4 py-2 rounded-lg border border-border bg-surface hover:bg-surface-muted text-xs font-semibold text-ink flex items-center gap-2 transition-colors"
            >
              {theme === 'dark' ? (
                <>
                  <Sun size={14} className="text-spark-amber" />
                  <span>Switch to Light</span>
                </>
              ) : (
                <>
                  <Moon size={14} className="text-focus" />
                  <span>Switch to Dark</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* AI Provider Telemetry Status */}
        <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 border-b border-border pb-4">
            <div className="h-10 w-10 rounded-xl bg-focus/10 text-focus flex items-center justify-center">
              <Cpu size={20} />
            </div>
            <div>
              <h2 className="font-heading font-bold text-base text-ink">AI Provider Status</h2>
              <p className="text-xs text-ink-muted">Dual-engine circuit breaker routing</p>
            </div>
          </div>

          {telemetry ? (
            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl border border-border bg-canvas flex items-center justify-between">
                <div>
                  <span className="font-semibold text-ink block">Google Gemini</span>
                  <span className="text-[11px] text-ink-muted font-mono">{telemetry.gemini.model}</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                    telemetry.gemini.configured && telemetry.gemini.connection === 'SUCCESS'
                      ? 'bg-good-leaf/10 text-good-leaf'
                      : 'bg-weak-rose/10 text-weak-rose'
                  }`}
                >
                  {telemetry.gemini.connection}
                </span>
              </div>

              <div className="p-3 rounded-xl border border-border bg-canvas flex items-center justify-between">
                <div>
                  <span className="font-semibold text-ink block">OpenAI</span>
                  <span className="text-[11px] text-ink-muted font-mono">{telemetry.openai.model}</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                    telemetry.openai.configured
                      ? 'bg-good-leaf/10 text-good-leaf'
                      : 'bg-surface-muted text-ink-muted'
                  }`}
                >
                  {telemetry.openai.configured ? 'CONFIGURED' : 'OFFLINE'}
                </span>
              </div>

              <div className="text-[11px] text-ink-muted text-center pt-1 font-mono">
                Active Provider: <strong className="text-focus">{telemetry.active_provider}</strong>
              </div>
            </div>
          ) : (
            <div className="text-xs text-ink-muted py-4 text-center">Detecting AI provider connections...</div>
          )}
        </div>
      </div>
    </div>
  );
};
