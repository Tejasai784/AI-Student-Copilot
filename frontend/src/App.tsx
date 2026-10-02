import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { AppShell, NavTab } from './components/layout/AppShell';
import { DashboardView } from './components/dashboard/DashboardView';
import { ChatView } from './components/chat/ChatView';
import { Sparkles, ArrowRight } from 'lucide-react';

const queryClient = new QueryClient();

export const AppContent: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('dashboard');

  return (
    <AppShell currentTab={currentTab} onSelectTab={setCurrentTab}>
      {currentTab === 'dashboard' && (
        <DashboardView
          onNavigateToChat={() => setCurrentTab('chat')}
          onNavigateToPlanner={() => setCurrentTab('planner')}
          onNavigateToQuizzes={() => setCurrentTab('quizzes')}
        />
      )}

      {currentTab === 'chat' && <ChatView />}

      {currentTab !== 'dashboard' && currentTab !== 'chat' && (
        <div className="p-8 max-w-4xl mx-auto text-center py-20 space-y-4">
          <div className="h-14 w-14 rounded-2xl bg-focus/10 text-focus flex items-center justify-center mx-auto shadow-sm">
            <Sparkles size={28} />
          </div>
          <h2 className="font-heading font-bold text-2xl text-ink capitalize">
            {currentTab.replace('_', ' ')}
          </h2>
          <p className="text-sm text-ink-muted max-w-md mx-auto">
            This module connects directly to your verified ASIP V2.0 backend services. You can practice in AI Chat or review Today's progress on the Dashboard.
          </p>
          <div className="pt-4 flex items-center justify-center gap-3">
            <button
              onClick={() => setCurrentTab('dashboard')}
              className="px-4 py-2 rounded-lg bg-surface border border-border text-xs font-semibold text-ink hover:bg-surface-muted transition-colors"
            >
              Back to Dashboard
            </button>
            <button
              onClick={() => setCurrentTab('chat')}
              className="px-4 py-2 rounded-lg bg-focus text-white text-xs font-semibold hover:bg-focus-hover flex items-center gap-1.5 shadow-sm transition-colors"
            >
              <span>Open AI Tutor</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
