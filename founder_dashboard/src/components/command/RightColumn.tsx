'use client';
import { ServiceHealth, SystemStats, AIModel, BrainStatus, TokenStats } from '@/lib/types';
import SystemStatusPanel from './SystemStatusPanel';
import TokenCostPanel from './TokenCostPanel';
import OllamaBrainPanel from './OllamaBrainPanel';
import EmpireBoxPanel from './EmpireBoxPanel';
import ForgePanel from './ForgePanel';
import CrmPanel from './CrmPanel';

interface Props {
  systemStats: SystemStats | null;
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
  models: AIModel[];
  brainStatus: BrainStatus | null;
  tokenStats: TokenStats | null;
}

export default function RightColumn({ systemStats, serviceHealth, backendOnline, models, brainStatus, tokenStats }: Props) {
  return (
    <div className="overflow-y-auto p-2 space-y-2" style={{ width: '220px', minWidth: '220px' }}>
      <SystemStatusPanel
        systemStats={systemStats}
        serviceHealth={serviceHealth}
        backendOnline={backendOnline}
      />
      <TokenCostPanel
        tokenStats={tokenStats}
        backendOnline={backendOnline}
      />
      <OllamaBrainPanel
        brainStatus={brainStatus}
        backendOnline={backendOnline}
      />
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
