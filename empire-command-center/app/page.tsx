'use client';
import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { BusinessTab, ScreenMode, EcosystemProduct } from './lib/types';
import { useChat } from './hooks/useChat';
import { useSystemData } from './hooks/useSystemData';
import { useChatHistory } from './hooks/useChatHistory';

import TopBar from './components/layout/TopBar';
import LeftNav from './components/layout/LeftNav';
import RightPanel from './components/layout/RightPanel';
import BottomBar from './components/layout/BottomBar';
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
import ForgeCRMPage from './components/screens/ForgeCRMPage';
import BusinessProfileScreen from './components/screens/BusinessProfileScreen';
import DesksScreen from './components/screens/DesksScreen';
import InboxScreen from './components/screens/InboxScreen';
import SystemReportScreen from './components/screens/SystemReportScreen';
import TelegramScreen from './components/screens/TelegramScreen';
import EcosystemProductPage from './components/screens/EcosystemProductPage';
const AmpLanding = lazy(() => import('./amp/page'));
import ProductDocs from './components/business/docs/ProductDocs';

import TasksScreen from './components/screens/TasksScreen';
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
  luxe: 'max',
  hardware: 'max',
  system: 'max',
  tokens: 'max',
  vision: 'max',
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
    else if (product === 'tokens') setActiveScreen('costs');
    else if (product === 'system') setActiveScreen('report');
    else setActiveScreen('dashboard');
  }, []);

  const handleScreenChange = useCallback((screen: ScreenMode | string) => {
    setActiveScreen(screen as ScreenMode);
    setActiveSection(null);
  }, []);

  const handleModuleClick = useCallback((module: string) => {
    // Modules that map to Workroom sections
    // Tasks gets its own dedicated screen
    if (module === 'tasks') {
      setActiveSection(null);
      setActiveScreen('tasks');
      return;
    }

    const workroomSections: Record<string, string> = {
      quotes: 'quotes',
      invoices: 'invoices',
      crm: 'customers',
      inventory: 'inventory',
    };

    if (workroomSections[module]) {
      setActiveProduct('workroom');
      setActiveScreen('dashboard');
      setActiveSection(workroomSections[module]);
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
    };
    setActiveSection(null);
    setActiveScreen(moduleScreenMap[module] || 'dashboard');
  }, []);

  const handleSendMessage = useCallback((msg: string, imageFilename?: string | null) => {
    chat.sendMessage(msg, imageFilename);
  }, [chat]);

  const handleQuickSwitchSelect = useCallback((screen: string) => {
    if (screen === 'workroom-page') { setActiveProduct('workroom'); setActiveScreen('dashboard'); }
    else if (screen === 'craft-page') { setActiveProduct('craft'); setActiveScreen('dashboard'); }
    else if (screen === 'platform-page') { setActiveProduct('platform'); setActiveScreen('dashboard'); }
    else handleScreenChange(screen);
  }, [handleScreenChange]);

  const renderCenterContent = () => {
    // Dashboard renders product-specific pages
    if (activeScreen === 'dashboard') {
      switch (activeProduct) {
        case 'workroom': return <WorkroomPage initialSection={activeSection || undefined} />;
        case 'craft': return <CraftForgePage />;
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
        case 'lead': return <LeadForgePage />;
        case 'market': return <MarketForgePage />;
        case 'pay': return <EmpirePayPage />;
        case 'ship': return <ShipForgePage />;
        case 'amp':
          return <Suspense fallback={<Loading />}><AmpLanding /></Suspense>;
        case 'crm':
          return <ForgeCRMPage />;
        case 'apost':
          return <ApostAppPage />;
        case 'relist':
          return (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 py-20">
              <div className="w-16 h-16 rounded-2xl bg-[#ecfeff] flex items-center justify-center">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
              </div>
              <h2 className="text-xl font-bold text-[#1a1a1a]">RelistApp</h2>
              <p className="text-sm text-[#777] text-center max-w-md">Cross-platform listing manager. List once, sell everywhere. AI-powered descriptions, pricing intelligence, and auto-relist scheduling.</p>
              <a href="http://localhost:3007" target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 px-6 py-3 rounded-xl text-white font-bold text-sm transition-all hover:brightness-110"
                style={{ background: 'linear-gradient(135deg, #06b6d4, #0891b2)', boxShadow: '0 4px 12px rgba(6,182,212,0.3)' }}>
                Open RelistApp <span style={{ fontSize: 16 }}>→</span>
              </a>
              <div className="flex gap-3 mt-2">
                <span className="text-[10px] font-bold px-3 py-1 rounded-full bg-[#dcfce7] text-[#16a34a]">eBay</span>
                <span className="text-[10px] font-bold px-3 py-1 rounded-full bg-[#fff7ed] text-[#f1641e]">Etsy</span>
                <span className="text-[10px] font-bold px-3 py-1 rounded-full bg-[#f0fdf4] text-[#96bf48]">Shopify</span>
                <span className="text-[10px] font-bold px-3 py-1 rounded-full bg-[#fdf8eb] text-[#b8960c]">+ More</span>
              </div>
            </div>
          );
        case 'openclaw':
        case 'recovery':
        case 'hardware':
          return <EcosystemProductPage productId={activeProduct} productName="" productColor="#b8960c" productIcon={null} />;
        case 'vetforge':
          return <VetForgePage />;
        case 'petforge':
          return <PetForgePage />;
        case 'vision':
          return <VisionAnalysisPage />;
        default: return <DashboardScreen activeTab={activeTab} />;
      }
    }
    if (activeScreen === 'business-profile') return <BusinessProfileScreen />;
    if (activeScreen === 'pricing' && activeProduct === 'platform') return <PricingPage />;
    if (activeScreen === 'desks') return <DesksScreen desks={sys.desks} onSendTask={handleSendMessage} />;
    if (activeScreen === 'inbox' || activeScreen === 'mail') return <InboxScreen />;
    if (activeScreen === 'telegram') return <TelegramScreen />;
    if (activeScreen === 'report') return <SystemReportScreen />;
    if (activeScreen === 'tasks') return <TasksScreen />;
    if (activeScreen === 'tickets') return <Suspense fallback={<Loading />}><TicketsPage /></Suspense>;
    if (activeScreen === 'shipping') return <Suspense fallback={<Loading />}><ShippingPage /></Suspense>;
    if (activeScreen === 'costs') return <Suspense fallback={<Loading />}><CostTracker /></Suspense>;
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

      <div className="flex-1 flex overflow-hidden">
        <LeftNav
          activeProduct={activeProduct}
          onProductChange={handleProductChange}
        />

        <div className="flex-1 flex flex-col overflow-y-auto bg-[var(--chat-bg)]">
          {renderCenterContent()}
        </div>

        {!clientView && (
          <RightPanel
            desks={sys.desks}
            briefing={sys.briefing}
            systemStats={sys.systemStats}
            activeScreen={activeScreen}
            activeProduct={activeProduct}
            activeSection={activeSection}
            onScreenChange={handleScreenChange}
            onModuleClick={handleModuleClick}
          />
        )}
      </div>

      <BottomBar services={sys.services} />

      <QuickSwitch
        open={showQuickSwitch}
        onClose={() => setShowQuickSwitch(false)}
        onSelect={handleQuickSwitchSelect}
      />
    </div>
  );
}
