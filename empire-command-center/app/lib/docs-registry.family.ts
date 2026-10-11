// Family-edition (AMP / Maxine) docs registry.
//
// Family builds must not ship Empire's internal documentation list. In those
// builds next.config swaps app/lib/docs-registry.ts for this file, so the
// Documentation module only lists the edition's own documents (kept under
// /data/<edition>/docs). It is empty until documents are added for the edition.

export interface DocEntry {
  title: string;
  path: string;
  type: 'spec' | 'readme' | 'guide' | 'api' | 'plan' | 'report' | 'update' | 'config' | 'audit' | 'session' | 'architecture' | 'legal' | 'business' | 'pdf' | 'image' | 'presentation' | 'mockup' | 'diagram' | 'compliance' | 'code' | 'research' | 'strategy' | 'playbook' | 'analysis' | 'framework';
  description: string;
}

export const DOCS_REGISTRY: Record<string, DocEntry[]> = {};

export function getDocCount(product: string): number {
  return (DOCS_REGISTRY[product] || []).length;
}

export function getAllUniqueDocs(): DocEntry[] {
  return [];
}

export const DOC_TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  spec: { bg: '#eff6ff', text: '#2563eb' },
  readme: { bg: '#f0fdf4', text: '#16a34a' },
  guide: { bg: '#fefce8', text: '#ca8a04' },
  api: { bg: '#fdf4ff', text: '#a855f7' },
  plan: { bg: '#fff7ed', text: '#ea580c' },
  report: { bg: '#f0f9ff', text: '#0284c7' },
  update: { bg: '#ecfdf5', text: '#047857' },
  config: { bg: '#f5f5f5', text: '#737373' },
  audit: { bg: '#fef2f2', text: '#dc2626' },
  session: { bg: '#f5f3ff', text: '#7c3aed' },
  architecture: { bg: '#ecfdf5', text: '#059669' },
  legal: { bg: '#fef2f2', text: '#b91c1c' },
  business: { bg: '#fffbeb', text: '#b45309' },
  pdf: { bg: '#fef2f2', text: '#dc2626' },
  image: { bg: '#f5f3ff', text: '#7c3aed' },
  presentation: { bg: '#fff7ed', text: '#ea580c' },
  mockup: { bg: '#fdf4ff', text: '#a855f7' },
  diagram: { bg: '#ecfdf5', text: '#059669' },
  research: { bg: '#dbeafe', text: '#2563eb' },
  strategy: { bg: '#fdf8eb', text: '#b8960c' },
  playbook: { bg: '#dcfce7', text: '#16a34a' },
  analysis: { bg: '#ede9fe', text: '#7c3aed' },
  framework: { bg: '#fef3c7', text: '#d97706' },
  compliance: { bg: '#fef2f2', text: '#b91c1c' },
  code: { bg: '#f3f4f6', text: '#374151' },
};
