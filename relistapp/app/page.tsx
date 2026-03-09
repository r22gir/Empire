'use client';

import { useState } from 'react';
import TopBar from './components/TopBar';
import Sidebar from './components/Sidebar';
import DashboardSection from './components/DashboardSection';
import ListingsSection from './components/ListingsSection';
import CrossPostSection from './components/CrossPostSection';
import PlatformsSection from './components/PlatformsSection';
import PricingSection from './components/PricingSection';
import SchedulerSection from './components/SchedulerSection';
import AnalyticsSection from './components/AnalyticsSection';
import SettingsSection from './components/SettingsSection';
import SellerProfileSection from './components/SellerProfileSection';
import SmartListerSection from './components/SmartListerSection';

export default function Home() {
  const [activeSection, setActiveSection] = useState('dashboard');

  const renderSection = () => {
    switch (activeSection) {
      case 'dashboard': return <DashboardSection onNavigate={setActiveSection} />;
      case 'profile': return <SellerProfileSection />;
      case 'smartlister': return <SmartListerSection />;
      case 'listings': return <ListingsSection />;
      case 'crosspost': return <CrossPostSection />;
      case 'platforms': return <PlatformsSection />;
      case 'pricing': return <PricingSection />;
      case 'scheduler': return <SchedulerSection />;
      case 'analytics': return <AnalyticsSection />;
      case 'settings': return <SettingsSection />;
      default: return <DashboardSection onNavigate={setActiveSection} />;
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activeSection} onNavigate={setActiveSection} />
        <main className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--bg)' }}>
          {renderSection()}
        </main>
      </div>
    </div>
  );
}
