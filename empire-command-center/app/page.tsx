'use client';
import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { BusinessTab, ScreenMode, EcosystemProduct } from './lib/types';
import { useChat } from './hooks/useChat';
import { useSystemData } from './hooks/useSystemData';
import { useChatHistory } from './hooks/useChatHistory';
import { API } from './lib/api';

import TopBar from './components/layout/TopBar';
import LeftNav from './components/layout/LeftNav';
import RightPanel from './components/layout/RightPanel';
import BottomBar from './components/layout/BottomBar';
import QuickSwitch from './components/layout/QuickSwitch';
import ActiveJobBanner from './components/ActiveJobBanner';

import ChatScreen from './components/screens/ChatScreen';
import QuoteReviewScreen from './components/screens/QuoteReviewScreen';
import DocumentScreen from './components/screens/DocumentScreen';
import ResearchScreen from './components/screens/ResearchScreen';
import VideoCallScreen from './components/screens/VideoCallScreen';
import DashboardScreen from './components/screens/DashboardScreen';
import WorkroomPage from './components/screens/WorkroomPage';
import CraftForgePage from './components/screens/CraftForgePage';
import PlatformPage from './components/screens/PlatformPage';
import PricingPage from './components/screens/PricingPage';
import SocialForgePage from './components/screens/SocialForgePage';
import LuxeForgePage from './components/screens/LuxeForgePage';
import LLCFactoryPage from './components/screens/LLCFactoryPage';
import EmpirePayPage from './components/screens/EmpirePayPage';
import MarketForgePage from './components/screens/MarketForgePage';
import ContractorForgePage from './components/screens/ContractorForgePage';
import SupportForgePage from './components/screens/SupportForgePage';
import EmpireAssistPage from './components/screens/EmpireAssistPage';
import LeadForgePage from './components/screens/LeadForgePage';
import ApostAppPage from './components/screens/ApostAppPage';
import ShipForgePage from './components/screens/ShipForgePage';
import VetForgePage from './components/screens/VetForgePage';
import PetForgePage from './components/screens/PetForgePage';
import VisionAnalysisPage from './components/screens/VisionAnalysisPage';
import DrawingStudioPage from './components/screens/DrawingStudioPage';
import ForgeCRMPage from './components/screens/ForgeCRMPage';
import BusinessProfileScreen from './components/screens/BusinessProfileScreen';
import DesksScreen from './components/screens/DesksScreen';
import InboxScreen from './components/screens/InboxScreen';
import SystemReportScreen from './components/screens/SystemReportScreen';
import TelegramScreen from './components/screens/TelegramScreen';
import MemoryBankScreen from './components/screens/MemoryBankScreen';
import EcosystemProductPage from './components/screens/EcosystemProductPage';
import RecoveryForgeScreen from './components/screens/RecoveryForgeScreen';
import RelistAppPage from './components/screens/RelistAppPage';
import LeadForgePageNew from './components/screens/LeadForgePageNew';
import DevPanel from './components/screens/DevPanel';
import OpenClawTasksPage from './components/screens/OpenClawTasksPage';
import JobsScreen from './components/screens/JobsScreen';
import InvoiceScreen from './components/screens/InvoiceScreen';
import ConstructionForgePage from './components/screens/ConstructionForgePage';
import StoreFrontForgePage from './components/screens/StoreFrontForgePage';
const AmpLanding = lazy(() => import('./amp/page'));
import ProductDocs from './components/business/docs/ProductDocs';

import TasksScreen from './components/screens/TasksScreen';
import PresentationScreen from './components/screens/PresentationScreen';
const TicketsPage = lazy(() => import('./components/business/support/TicketsPage'));
const ShippingPage = lazy(() => import('./components/business/shipping/ShippingPage'));
const CostTracker = lazy(() => import('./components/business/costs/CostTracker'));

const Loading = () => (
  <div className="flex-1 flex items-center justify-center">
    <div className="text-sm text-[var(--muted)]">Loading...</div>
  </div>
);

// Map ecosystem product to legacy BusinessTab for data hooks
const PRODUCT_TO_TAB: Partial<Record<EcosystemProduct, BusinessTab>> = {
  owner: 'max',
  workroom: 'workroom',
  craft: 'craft',
  social: 'social',
  platform: 'platform',
  openclaw: 'max',
  recovery: 'max',
  dev: 'max',
  luxe: 'max',
  hardware: 'max',
  system: 'max',
  tokens: 'max',
  vision: 'max',
  drawings: 'workroom',
  construction: 'max',
  storefront: 'max',
};

export default function CommandCenter() {
  const [activeProduct, setActiveProduct] = useState<EcosystemProduct>('owner');
  const [activeScreen, setActiveScreen] = useState<ScreenMode>('chat');
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [showQuickSwitch, setShowQuickSwitch] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [clientView, setClientView] = useState(false);

  const chat = useChat();
  const sys = useSystemData();
  const history = useChatHistory();

  // Derive legacy tab from product
  const activeTab: BusinessTab = PRODUCT_TO_TAB[activeProduct] || 'max';

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

  const handleProductChange = useCallback((product: EcosystemProduct) => {
    setActiveProduct(product);
    setActiveSection(null);
    // When switching product, go to dashboard for that product (or chat for owner)
    if (product === 'owner') setActiveScreen('chat');
    else if (product === 'max-avatar') setActiveScreen('presentation');
    else if (product === 'tokens') setActiveScreen('costs');
    else if (product === 'system') setActiveScreen('report');
    else if (product === 'dev') setActiveScreen('dev');
    else setActiveScreen('dashboard');
  }, []);

  const handleScreenChange = useCallback((screen: ScreenMode | string) => {
    setActiveScreen(screen as ScreenMode);
    setActiveSection(null);
  }, []);

  const handleModuleClick = useCallback((module: string) => {
    // Tasks gets its own dedicated screen regardless of product
    if (module === 'tasks') {
      setActiveSection(null);
      setActiveScreen('tasks');
      return;
    }

    // CraftForge-specific module IDs (prefixed with 'craft-')
    const craftSections: Record<string, string> = {
      'craft-quotes': 'quotebuilder',
      'craft-inventory': 'inventory',
      'craft-crm': 'customers',
      'craft-finance': 'finance',
      'craft-jobs': 'jobs',
      'craft-payments': 'payments',
    };

    if (craftSections[module]) {
      setActiveProduct('craft');
      setActiveScreen('dashboard');
      setActiveSection(craftSections[module]);
      return;
    }

    // Shared module IDs that route based on active product context
    const sharedSections: Record<string, string> = {
      quotes: 'quotes',
      invoices: 'invoices',
      crm: 'customers',
      inventory: 'inventory',
    };

    if (sharedSections[module]) {
      // If currently on CraftForge, route to CraftForge sections
      if (activeProduct === 'craft') {
        const craftMapping: Record<string, string> = {
          quotes: 'quotebuilder',
          inventory: 'inventory',
          crm: 'customers',
          invoices: 'finance',
        };
        setActiveScreen('dashboard');
        setActiveSection(craftMapping[module] || sharedSections[module]);
      } else {
        // Default to Workroom
        setActiveProduct('workroom');
        setActiveScreen('dashboard');
        setActiveSection(sharedSections[module]);
      }
      return;
    }

    // Empire-wide CRM shortcut
    if (module === 'empire-crm') {
      setActiveProduct('crm');
      setActiveScreen('dashboard');
      return;
    }

    // Modules that map to standalone screens
    const moduleScreenMap: Record<string, ScreenMode> = {
      shipping: 'shipping',
      tickets: 'tickets',
      costs: 'costs',
      reports: 'report',
      calendar: 'calendar',
      documents: 'docs',
      'business-profile': 'business-profile',
      settings: 'business-profile',
      jobs: 'jobs',
      invoices: 'invoices',
    };
    setActiveSection(null);
    setActiveScreen(moduleScreenMap[module] || 'dashboard');
  }, [activeProduct]);

  const handleSendMessage = useCallback((msg: string, imageFilename?: string | null) => {
    chat.sendMessage(msg, imageFilename);
  }, [chat]);

  // Auto-save chat after every assistant message
  useEffect(() => {
    const msgs = chat.messages.filter(m => m.id !== 'welcome');
    if (msgs.length >= 2 && msgs[msgs.length - 1]?.role === 'assistant') {
      const chatId = (chat as any).chatId;
      const payload = msgs.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp }));
      if (chatId) {
        fetch(API + `/chats/${chatId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: payload }),
        }).catch(() => {});
      } else {
        fetch(API + '/chats/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: payload }),
        }).catch(() => {});
      }
    }
  }, [chat.messages]);

  const handleLoadChat = useCallback(async (chatId: string) => {
    try {
      const res = await fetch(API + `/chats/${chatId}`);
      if (res.ok) {
        const data = await res.json();
        const msgs = (data.messages || []).map((m: any, i: number) => ({
          id: m.id || `loaded-${i}`,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || '',
          model: m.model,
        }));
        chat.loadMessages(msgs, chatId);
        setActiveScreen('chat');
      }
    } catch { /* silent */ }
  }, [chat, setActiveScreen]);

  const handleNewChat = useCallback(() => {
    chat.loadMessages([], null);
    setActiveScreen('chat');
  }, [chat, setActiveScreen]);

  const handleQuickSwitchSelect = useCallback((screen: string) => {
    if (screen === 'workroom-page') { setActiveProduct('workroom'); setActiveScreen('dashboard'); }
    else if (screen === 'craft-page') { setActiveProduct('craft'); setActiveScreen('dashboard'); }
    else if (screen === 'platform-page') { setActiveProduct('platform'); setActiveScreen('dashboard'); }
    else if (screen === 'presentation') { setActiveProduct('max-avatar'); setActiveScreen('presentation'); }
    else if (screen === 'dev' || screen === 'dev-panel') { setActiveProduct('dev'); setActiveScreen('dev'); }
    else if (screen === 'recovery') { setActiveProduct('recovery'); setActiveScreen('dashboard'); }
    else if (screen === 'relist') { setActiveProduct('relist'); setActiveScreen('dashboard'); }
    else handleScreenChange(screen);
  }, [handleScreenChange]);

  const renderCenterContent = () => {
    // Dashboard renders product-specific pages
    if (activeScreen === 'dashboard') {
      switch (activeProduct) {
        case 'workroom': return <WorkroomPage initialSection={activeSection || undefined} />;
        case 'craft': return <CraftForgePage initialSection={activeSection || undefined} />;
        case 'social': return <SocialForgePage />;
        case 'platform': return <PlatformPage />;
        case 'owner': return <DashboardScreen activeTab={activeTab} />;
        case 'luxe': return <LuxeForgePage onNavigate={(product, screen, section) => {
            setActiveProduct(product as EcosystemProduct);
            setActiveScreen(screen as ScreenMode);
            if (section) setActiveSection(section);
          }} />;
        case 'llc': return <LLCFactoryPage />;
        case 'assist': return <EmpireAssistPage />;
        case 'support': return <SupportForgePage />;
        case 'contractor': return <ContractorForgePage />;
        case 'lead': return <LeadForgePageNew initialSection={activeSection || undefined} />;
        case 'market': return <MarketForgePage />;
        case 'pay': return <EmpirePayPage />;
        case 'ship': return <ShipForgePage />;
        case 'amp':
          return <Suspense fallback={<Loading />}><AmpLanding /></Suspense>;
        case 'crm':
          return <ForgeCRMPage />;
        case 'apost':
          return <ApostAppPage />;
        case 'recovery':
          return <RecoveryForgeScreen />;
        case 'relist':
          return <RelistAppPage initialSection={activeSection || undefined} />;
        case 'dev':
          return <DevPanel />;
        case 'openclaw':
          return <OpenClawTasksPage />;
        case 'hardware':
          return <EcosystemProductPage productId={activeProduct} productName="" productColor="#b8960c" productIcon={null} />;
        case 'vetforge':
          return <VetForgePage />;
        case 'petforge':
          return <PetForgePage />;
        case 'construction':
          return <ConstructionForgePage initialSection={activeSection || undefined} />;
        case 'storefront':
          return <StoreFrontForgePage initialSection={activeSection || undefined} />;
        case 'vision':
          return <VisionAnalysisPage />;
        case 'drawings':
          return <DrawingStudioPage initialView={activeSection === 'catalog' ? 'catalog' : 'studio'} />;
        default: return <DashboardScreen activeTab={activeTab} />;
      }
    }
    if (activeScreen === 'business-profile') return <BusinessProfileScreen />;
    if (activeScreen === 'pricing' && activeProduct === 'platform') return <PricingPage />;
    if (activeScreen === 'desks') return <DesksScreen desks={sys.desks} onSendTask={handleSendMessage} />;
    if (activeScreen === 'inbox' || activeScreen === 'mail') return <InboxScreen />;
    if (activeScreen === 'memory-bank') return <MemoryBankScreen />;
    if (activeScreen === 'telegram') return <TelegramScreen />;
    if (activeScreen === 'report') return <SystemReportScreen />;
    if (activeScreen === 'tasks') return <TasksScreen business={activeProduct === 'workroom' ? 'workroom' : activeProduct === 'craft' ? 'woodcraft' : activeProduct === 'owner' ? undefined : activeProduct} />;
    if (activeScreen === 'tickets') return <Suspense fallback={<Loading />}><TicketsPage /></Suspense>;
    if (activeScreen === 'shipping') return <Suspense fallback={<Loading />}><ShippingPage /></Suspense>;
    if (activeScreen === 'costs') return <Suspense fallback={<Loading />}><CostTracker /></Suspense>;
    if (activeScreen === 'presentation') return <PresentationScreen />;
    if (activeScreen === 'dev') return <DevPanel />;
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
          onProductNavigate={(product, screen = 'dashboard') => {
            setActiveProduct(product as EcosystemProduct);
            setActiveScreen(screen as ScreenMode);
          }}
          setOnMessageComplete={chat.setOnMessageComplete}
          onLoadChat={handleLoadChat}
          onNewChat={handleNewChat}
        />
      );
    }
    if (activeScreen === 'quote') return <QuoteReviewScreen />;
    if (activeScreen === 'jobs') return <JobsScreen business={activeProduct === 'workroom' ? 'workroom' : activeProduct === 'craft' ? 'woodcraft' : undefined} />;
    if (activeScreen === 'invoices') return <InvoiceScreen />;
    if (activeScreen === 'docs') return <DocumentScreen />;
    if (activeScreen === 'product-docs') return (
      <div style={{ padding: '24px 28px', maxWidth: 900, margin: '0 auto' }}>
        <ProductDocs product={activeProduct} />
      </div>
    );
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
        onQuickSwitch={() => setShowQuickSwitch(true)}
        onClientView={() => setClientView(!clientView)}
        onNavigate={(product, screen) => {
          setActiveProduct(product as EcosystemProduct);
          setActiveScreen(screen as ScreenMode);
        }}
        services={sys.services}
      />

      <ActiveJobBanner />

      <div className="flex-1 flex overflow-hidden">
        <LeftNav
          activeProduct={activeProduct}
          onProductChange={handleProductChange}
          dashboardProps={{
            desks: sys.desks,
            briefing: sys.briefing,
            systemStats: sys.systemStats,
            activeScreen,
            activeProduct,
            activeSection,
            onScreenChange: handleScreenChange,
            onModuleClick: handleModuleClick,
          }}
        />

        <div className="flex-1 flex flex-col overflow-y-auto bg-[var(--chat-bg)]">
          {renderCenterContent()}
        </div>

        {/* Right panel moved into left nav as Dashboard tab */}
      </div>

      <div className="hidden md:block">
        <BottomBar services={sys.services} />
      </div>

      <QuickSwitch
        open={showQuickSwitch}
        onClose={() => setShowQuickSwitch(false)}
        onSelect={handleQuickSwitchSelect}
      />
    </div>
  );
}
