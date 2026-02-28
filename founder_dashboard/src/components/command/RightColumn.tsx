'use client';
import { ServiceHealth, SystemStats, AIModel, BrainStatus } from '@/lib/types';
import SystemStatusPanel from './SystemStatusPanel';
import AiUsagePanel from './AiUsagePanel';
import EmpireBoxPanel from './EmpireBoxPanel';
import OllamaBrainPanel from './OllamaBrainPanel';
import ForgePanel from './ForgePanel';
import CrmPanel from './CrmPanel';

interface Props {
  systemStats: SystemStats | null;
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
  models: AIModel[];
  brainStatus: BrainStatus | null;
}

export default function RightColumn({ systemStats, serviceHealth, backendOnline, models, brainStatus }: Props) {
  return (
    <div className="overflow-y-auto p-2 space-y-2" style={{ width: '220px', minWidth: '220px' }}>
      <SystemStatusPanel
        systemStats={systemStats}
        serviceHealth={serviceHealth}
        backendOnline={backendOnline}
      />
      <OllamaBrainPanel
        brainStatus={brainStatus}
        backendOnline={backendOnline}
      />
      <AiUsagePanel backendOnline={backendOnline} />
      <EmpireBoxPanel
        serviceHealth={serviceHealth}
        backendOnline={backendOnline}
        models={models}
        brainStatus={brainStatus}
      />
      <ForgePanel serviceHealth={serviceHealth} />
      <CrmPanel />
    </div>
  );
}
