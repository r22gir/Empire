const LUXE_HOSTS = new Set(['luxe.empirebox.store', 'test-luxe.empirebox.store']);
const FABRICS_HOSTS = new Set(['fabrics.empirebox.store', 'test-fabrics.empirebox.store']);

export const LUXE_DOCUMENT_TITLE = 'Empire Workroom · Designer Intake';
export const FABRICS_DOCUMENT_TITLE = 'Empire Fine Fabrics';
export const COMMAND_CENTER_DOCUMENT_TITLE = 'Empire Command Center';

export function documentTitleForHost(host: string | null | undefined): string {
  const name = (host || '').split(',')[0].trim().split(':')[0].toLowerCase().replace(/\.$/, '');
  if (LUXE_HOSTS.has(name)) return LUXE_DOCUMENT_TITLE;
  if (FABRICS_HOSTS.has(name)) return FABRICS_DOCUMENT_TITLE;
  return COMMAND_CENTER_DOCUMENT_TITLE;
}
