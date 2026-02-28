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
    <div className="flex-[1] overflow-y-auto p-4 space-y-4 min-w-[300px]">
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
