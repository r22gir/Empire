'use client';
import { ServiceHealth, SystemStats, AIModel } from '@/lib/types';
import SystemStatusPanel from './SystemStatusPanel';
import AiUsagePanel from './AiUsagePanel';
import EmpireBoxPanel from './EmpireBoxPanel';
import ForgePanel from './ForgePanel';
import CrmPanel from './CrmPanel';

interface Props {
  systemStats: SystemStats | null;
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
  models: AIModel[];
}

export default function RightColumn({ systemStats, serviceHealth, backendOnline, models }: Props) {
  return (
    <div className="overflow-y-auto p-2 space-y-2" style={{ width: '220px', minWidth: '220px' }}>
      <SystemStatusPanel
        systemStats={systemStats}
        serviceHealth={serviceHealth}
        backendOnline={backendOnline}
      />
      <AiUsagePanel backendOnline={backendOnline} />
      <EmpireBoxPanel
        serviceHealth={serviceHealth}
        backendOnline={backendOnline}
        models={models}
      />
      <ForgePanel serviceHealth={serviceHealth} />
      <CrmPanel />
    </div>
  );
}
