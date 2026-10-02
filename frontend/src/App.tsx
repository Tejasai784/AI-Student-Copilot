import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { AppShell, NavTab } from './components/layout/AppShell';
import { DashboardView } from './components/dashboard/DashboardView';
import { ChatView } from './components/chat/ChatView';
import { MaterialsView } from './components/materials/MaterialsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { SyllabusView } from './components/syllabus/SyllabusView';
import { QuizzesView } from './components/quizzes/QuizzesView';
import { MockExamsView } from './components/mock_exams/MockExamsView';
import { PlannerView } from './components/planner/PlannerView';
import { GoalsView } from './components/goals/GoalsView';
import { WeaknessesView } from './components/weaknesses/WeaknessesView';
import { AnalyticsView } from './components/analytics/AnalyticsView';
import { ReportsView } from './components/reports/ReportsView';
import { MemoryView } from './components/memory/MemoryView';
import { AgentsView } from './components/agents/AgentsView';
import { SettingsView } from './components/settings/SettingsView';
import { DiagnosticsView } from './components/diagnostics/DiagnosticsView';

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

      {currentTab === 'knowledge' && <KnowledgeView />}

      {currentTab === 'materials' && <MaterialsView />}

      {currentTab === 'syllabus' && <SyllabusView />}

      {currentTab === 'quizzes' && <QuizzesView />}

      {currentTab === 'mock_exams' && <MockExamsView />}

      {currentTab === 'planner' && <PlannerView />}

      {currentTab === 'goals' && <GoalsView />}

      {currentTab === 'weaknesses' && (
        <WeaknessesView
          onPracticeTopic={() => setCurrentTab('quizzes')}
          onAskTutor={() => setCurrentTab('chat')}
        />
      )}

      {currentTab === 'analytics' && <AnalyticsView />}

      {currentTab === 'reports' && <ReportsView />}

      {currentTab === 'memory' && <MemoryView />}

      {currentTab === 'agents' && <AgentsView />}

      {currentTab === 'settings' && <SettingsView />}

      {currentTab === 'diagnostics' && <DiagnosticsView />}
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
