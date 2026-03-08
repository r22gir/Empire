'use client';
import { useState, useEffect } from 'react';
import { API } from '../lib/api';
import TopNav from '../components/TopNav';
import KPICards from '../components/KPICards';
import DesignsList from '../components/DesignsList';
import JobsQueue from '../components/JobsQueue';
import InventoryPanel from '../components/InventoryPanel';
import MachineStatus from '../components/MachineStatus';
import NewDesignModal from '../components/NewDesignModal';

export default function Home() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [designs, setDesigns] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [showNewDesign, setShowNewDesign] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'designs' | 'jobs' | 'inventory'>('overview');

  const refresh = () => {
    fetch(API + '/dashboard').then(r => r.json()).then(setDashboard).catch(() => {});
    fetch(API + '/designs?limit=20').then(r => r.json()).then(d => setDesigns(d.designs || [])).catch(() => {});
    fetch(API + '/jobs?limit=20').then(r => r.json()).then(d => setJobs(d.jobs || [])).catch(() => {});
    fetch(API + '/inventory').then(r => r.json()).then(d => setInventory(d.items || [])).catch(() => {});
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div className="min-h-screen">
      <TopNav activeTab={activeTab} setActiveTab={setActiveTab} onNewDesign={() => setShowNewDesign(true)} />

      <main className="max-w-[1400px] mx-auto px-6 py-6">
        {activeTab === 'overview' && (
          <>
            <KPICards dashboard={dashboard} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
              <DesignsList designs={designs} onRefresh={refresh} />
              <JobsQueue jobs={jobs} onRefresh={refresh} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
              <InventoryPanel inventory={inventory} onRefresh={refresh} />
              <MachineStatus dashboard={dashboard} />
            </div>
          </>
        )}

        {activeTab === 'designs' && (
          <DesignsList designs={designs} onRefresh={refresh} full />
        )}

        {activeTab === 'jobs' && (
          <JobsQueue jobs={jobs} onRefresh={refresh} full />
        )}

        {activeTab === 'inventory' && (
          <InventoryPanel inventory={inventory} onRefresh={refresh} full />
        )}
      </main>

      {showNewDesign && (
        <NewDesignModal onClose={() => setShowNewDesign(false)} onCreated={() => { setShowNewDesign(false); refresh(); }} />
      )}
    </div>
  );
}
