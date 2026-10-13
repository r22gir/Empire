export const IMPROVEMENT_PIPELINE = [
  { id: 'proposed', label: 'Proposed' },
  { id: 'approved', label: 'Approved' },
  { id: 'planning', label: 'Planning' },
  { id: 'pr_open', label: 'PR open' },
  { id: 'deployed', label: 'Deployed' },
] as const;

export type PipelineId = (typeof IMPROVEMENT_PIPELINE)[number]['id'];

const PIPELINE_INDEX: Record<string, number> = {
  proposed: 0,
  approved: 1,
  planning: 2,
  awaiting_build: 2,
  building: 2,
  pr_open: 3,
  merge_approved: 3,
  deployed: 4,
  done: 4,
};

export function pipelineIndex(status: string | undefined): number {
  if (!status) return 0;
  if (status === 'rejected' || status === 'build_failed') return -1;
  return PIPELINE_INDEX[status] ?? 0;
}

export function isRetryable(status: string | undefined): boolean {
  return status === 'build_failed' || status === 'awaiting_build';
}

export function usageBarPct(calls: number, cap: number): number {
  if (!cap || cap <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((calls / cap) * 100)));
}
