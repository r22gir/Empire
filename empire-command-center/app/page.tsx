'use client';
import { useState, useEffect, useCallback } from 'react';
import { BusinessTab, ScreenMode } from './lib/types';
import { useChat } from './hooks/useChat';
import { useSystemData } from './hooks/useSystemData';
import { useChatHistory } from './hooks/useChatHistory';

import TopBar from './components/layout/TopBar';
import GlobalSidebar from './components/layout/GlobalSidebar';
import ConversationSidebar from './components/layout/ConversationSidebar';
import RightPanel from './components/layout/RightPanel';
import TickerBar from './components/layout/TickerBar';
import QuickSwitch from './components/layout/QuickSwitch';

import ChatScreen from './components/screens/ChatScreen';
import QuoteReviewScreen from './components/screens/QuoteReviewScreen';
import DocumentScreen from './components/screens/DocumentScreen';
import ResearchScreen from './components/screens/ResearchScreen';
import VideoCallScreen from './components/screens/VideoCallScreen';
import DashboardScreen from './components/screens/DashboardScreen';
import WorkroomPage from './components/screens/WorkroomPage';
import CraftForgePage from './components/screens/CraftForgePage';
import PlatformPage from './components/screens/PlatformPage';
import SocialForgePage from './components/screens/SocialForgePage';
import DesksScreen from './components/screens/DesksScreen';
import InboxScreen from './components/screens/InboxScreen';
import SystemReportScreen from './components/screens/SystemReportScreen';

export default function CommandCenter() {
  const [activeTab, setActiveTab] = useState<BusinessTab>('max');
  const [activeScreen, setActiveScreen] = useState<ScreenMode>('chat');
  const [showQuickSwitch, setShowQuickSwitch] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [clientView, setClientView] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const chat = useChat();
  const sys = useSystemData();
  const history = useChatHistory();

  // Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowQuickSwitch(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleTabChange = useCallback((tab: BusinessTab) => {
    setActiveTab(tab);
    if (tab === 'max') setActiveScreen('chat');
    else setActiveScreen('dashboard');
  }, []);

  const handleScreenChange = useCallback((screen: ScreenMode | string) => {
    if (['chat', 'quote', 'docs', 'research', 'video', 'dashboard', 'desks', 'inbox'].includes(screen)) {
      setActiveScreen(screen as ScreenMode);
    }
  }, []);

  const handleQuickSwitchSelect = useCallback((screen: string) => {
    if (screen === 'workroom-page') { setActiveTab('workroom'); setActiveScreen('dashboard'); }
    else if (screen === 'craft-page') { setActiveTab('craft'); setActiveScreen('dashboard'); }
    else if (screen === 'platform-page') { setActiveTab('platform'); setActiveScreen('dashboard'); }
    else handleScreenChange(screen);
  }, [handleScreenChange]);

  const handleSendMessage = useCallback((msg: string, imageFilename?: string | null) => {
    chat.sendMessage(msg, imageFilename);
  }, [chat]);

  const filteredConvs = history.filterByBusiness(activeTab);

  const renderCenterContent = () => {
    if (activeScreen === 'dashboard') {
      switch (activeTab) {
        case 'workroom': return <WorkroomPage />;
        case 'craft': return <CraftForgePage />;
        case 'social': return <SocialForgePage />;
        case 'platform': return <PlatformPage />;
        default: return <DashboardScreen activeTab={activeTab} />;
      }
    }
    if (activeScreen === 'desks') return <DesksScreen desks={sys.desks} onSendTask={handleSendMessage} />;
    if (activeScreen === 'inbox') return <InboxScreen />;
    if (activeScreen === 'report') return <SystemReportScreen />;
    if (activeScreen === 'chat') {
      return (
        <ChatScreen
          messages={chat.messages}
          isStreaming={chat.isStreaming}
          streamingContent={chat.streamingContent}
          streamingModel={chat.streamingModel}
          onSend={handleSendMessage}
          onStop={chat.stopStreaming}
          onScreenChange={handleScreenChange}
        />
      );
    }
    if (activeScreen === 'quote') return <QuoteReviewScreen />;
    if (activeScreen === 'docs') return <DocumentScreen />;
    if (activeScreen === 'research') return <ResearchScreen />;
    if (activeScreen === 'video') return <VideoCallScreen />;
    return null;
  };

  return (
    <div className="h-screen flex flex-col">
      {clientView && (
        <div className="bg-[#16a34a] text-white text-center py-2 text-xs font-bold tracking-widest flex items-center justify-center gap-3 shadow-[0_2px_8px_rgba(22,163,74,0.3)]">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          CLIENT VIEW — Internal data hidden
          <button onClick={() => setClientView(false)}
            className="ml-2 px-3 py-1 rounded-md bg-white/20 hover:bg-white/30 cursor-pointer border border-white/30 text-white text-[10px] font-bold transition-all">
            EXIT
          </button>
        </div>
      )}

      <TopBar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onVideoCall={() => setActiveScreen('video')}
        onQuickSwitch={() => setShowQuickSwitch(true)}
        onClientView={() => setClientView(!clientView)}
        services={sys.services}
      />

      <div className="flex-1 flex overflow-hidden">
        <GlobalSidebar
          activeScreen={activeScreen}
          onScreenChange={handleScreenChange}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {!clientView && (
          <ConversationSidebar
            activeTab={activeTab}
            conversations={filteredConvs}
            activeConvId={activeConvId}
            onSelect={setActiveConvId}
            onNew={() => history.createConversation()}
            collapsed={leftCollapsed}
            onToggle={() => setLeftCollapsed(!leftCollapsed)}
          />
        )}

        <div className="flex-1 flex flex-col overflow-hidden bg-[#faf9f7]">
          {renderCenterContent()}
        </div>

        {!clientView && (
          <RightPanel
            desks={sys.desks}
            briefing={sys.briefing}
            systemStats={sys.systemStats}
            collapsed={rightCollapsed}
            onToggle={() => setRightCollapsed(!rightCollapsed)}
          />
        )}
      </div>

      <TickerBar />

      <QuickSwitch
        open={showQuickSwitch}
        onClose={() => setShowQuickSwitch(false)}
        onSelect={handleQuickSwitchSelect}
      />
    </div>
  );
}
