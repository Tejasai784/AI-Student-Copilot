import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  UploadCloud,
  FileText,
  HelpCircle,
  Award,
  Calendar,
  CheckSquare,
  AlertTriangle,
  TrendingUp,
  FileCheck,
  Brain,
  Activity,
  Settings as SettingsIcon,
  Server,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  Menu,
  Sparkles,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../lib/api';

export type NavTab =
  | 'dashboard'
  | 'chat'
  | 'knowledge'
  | 'materials'
  | 'syllabus'
  | 'quizzes'
  | 'mock_exams'
  | 'planner'
  | 'goals'
  | 'weaknesses'
  | 'analytics'
  | 'reports'
  | 'memory'
  | 'agents'
  | 'settings'
  | 'diagnostics';

interface AppShellProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ currentTab, onSelectTab, children }) => {
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [providerInfo, setProviderInfo] = useState<string>('Detecting...');

  useEffect(() => {
    api.getProvidersTelemetry()
      .then((tel) => {
        if (tel.gemini?.configured && tel.gemini?.connection === 'SUCCESS') {
          setProviderInfo(`Gemini (${tel.gemini.model})`);
        } else if (tel.openai?.configured) {
          setProviderInfo(`OpenAI (${tel.openai.model})`);
        } else {
          setProviderInfo('Offline Mode');
        }
      })
      .catch(() => setProviderInfo('Offline Mode'));
  }, []);

  const navGroups = [
    {
      label: 'Learn',
      items: [
        { id: 'dashboard', label: 'Today Dashboard', icon: LayoutDashboard },
        { id: 'chat', label: 'AI Academic Tutor', icon: MessageSquare },
        { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
        { id: 'materials', label: 'Course Materials', icon: UploadCloud },
        { id: 'syllabus', label: 'Syllabus & Topics', icon: FileText },
      ],
    },
    {
      label: 'Practice',
      items: [
        { id: 'quizzes', label: 'Practice Quizzes', icon: HelpCircle },
        { id: 'mock_exams', label: 'Mock Exams', icon: Award },
      ],
    },
    {
      label: 'Track',
      items: [
        { id: 'planner', label: 'Study Planner', icon: Calendar },
        { id: 'goals', label: 'Goals & Tasks', icon: CheckSquare },
        { id: 'weaknesses', label: 'Weak Topics', icon: AlertTriangle },
        { id: 'analytics', label: 'Progress Analytics', icon: TrendingUp },
        { id: 'reports', label: 'Readiness Reports', icon: FileCheck },
      ],
    },
    {
      label: 'System',
      items: [
        { id: 'memory', label: 'Personalization', icon: Brain },
        { id: 'agents', label: 'Agent Traces', icon: Activity },
        { id: 'settings', label: 'Settings', icon: SettingsIcon },
        { id: 'diagnostics', label: 'Diagnostics', icon: Server },
      ],
    },
  ];

  return (
    <div className="flex h-screen w-full bg-canvas text-ink overflow-hidden font-sans">
      {/* Sidebar Desktop */}
      <aside
        className={`hidden md:flex flex-col border-r border-border bg-surface transition-all duration-200 z-20 ${
          collapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between px-4 h-16 border-b border-border">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="h-9 w-9 rounded-lg bg-focus flex items-center justify-center text-white font-heading font-bold text-lg shadow-sm flex-shrink-0">
              🎓
            </div>
            {!collapsed && (
              <div className="leading-tight">
                <span className="font-heading font-bold text-base text-ink block tracking-tight">
                  ASIP V2.0
                </span>
                <span className="text-[11px] text-ink-muted block font-medium">
                  Autonomous Copilot
                </span>
              </div>
            )}
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-muted transition-colors"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Nav Items List */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navGroups.map((group) => (
            <div key={group.label} className="space-y-1">
              {!collapsed && (
                <div className="px-3 text-[11px] font-semibold tracking-wider text-ink-muted/80 uppercase font-sans mb-1.5">
                  {group.label}
                </div>
              )}
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id as NavTab)}
                    title={collapsed ? item.label : undefined}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-focus text-white shadow-sm'
                        : 'text-ink-muted hover:text-ink hover:bg-surface-muted'
                    } ${collapsed ? 'justify-center' : ''}`}
                  >
                    <Icon size={18} className={isActive ? 'text-white' : 'text-ink-muted'} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* User Pill Footer */}
        <div className="p-3 border-t border-border bg-surface-muted/40">
          <div className={`flex items-center gap-3 ${collapsed ? 'justify-center' : ''}`}>
            <div className="h-8 w-8 rounded-full bg-focus/15 text-focus font-heading font-bold text-xs flex items-center justify-center flex-shrink-0">
              AL
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <p className="text-xs font-semibold text-ink truncate">Alex Morgan</p>
                <p className="text-[11px] text-ink-muted truncate">CS · 3rd Year</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="h-16 border-b border-border bg-surface px-4 md:px-8 flex items-center justify-between z-10 flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-muted"
            >
              <Menu size={20} />
            </button>
            <h1 className="font-heading font-bold text-lg md:text-xl text-ink capitalize tracking-tight">
              {currentTab.replace('_', ' ')}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Provider indicator badge */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-surface-muted border border-border text-xs font-medium text-ink-muted">
              <span className={`h-2 w-2 rounded-full ${providerInfo.includes('Offline') ? 'bg-weak' : 'bg-good'}`} />
              <span className="truncate max-w-[160px]">{providerInfo}</span>
            </div>

            {/* Quick Ask Tutor shortcut */}
            {currentTab !== 'chat' && (
              <button
                onClick={() => onSelectTab('chat')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-focus/10 text-focus hover:bg-focus/15 text-xs font-semibold transition-colors"
              >
                <Sparkles size={14} />
                <span>Ask AI Tutor</span>
              </button>
            )}

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              aria-label="Toggle light or dark theme"
              className="p-2 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-muted transition-colors border border-transparent hover:border-border"
            >
              {theme === 'dark' ? <Sun size={18} className="text-spark" /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 overflow-y-auto bg-canvas">
          {children}
        </main>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden bg-ink/40 backdrop-blur-sm">
          <div className="w-72 bg-surface h-full flex flex-col p-4 shadow-xl border-r border-border">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <span className="font-heading font-bold text-lg">🎓 ASIP V2.0</span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-1 rounded text-ink-muted hover:text-ink"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-4 space-y-4">
              {navGroups.map((group) => (
                <div key={group.label}>
                  <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-2">
                    {group.label}
                  </p>
                  {group.items.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        onSelectTab(item.id as NavTab);
                        setMobileMenuOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm mb-1 ${
                        currentTab === item.id ? 'bg-focus text-white font-semibold' : 'text-ink-muted hover:bg-surface-muted'
                      }`}
                    >
                      <item.icon size={18} />
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
        </div>
      )}
    </div>
  );
};
