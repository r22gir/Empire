export const PEDIR_CURSOR_NOTE =
  'Esto no lanza nada solo: Chief e lo revisa, te muestra el cambio y Rafael da el sí final.';

export const PEDIR_CURSOR_PAUSED =
  'Manito, ya usaste tu 20% del mes y Rafael está usando Max ahora. Guárdalo y lo mandas en un rato.';

export const PEDIR_CURSOR_APPROVED =
  'Listo, manito. Ya quedó aprobado de tu lado; Rafael da el sí final para desplegar.';

export const STATUS_CHIPS: Record<string, string> = {
  queued: 'En cola',
  in_progress: 'En progreso',
  pr_open: 'PR listo para revisar',
  owner_approved: 'Aprobado por ti',
  changes_requested: 'Pediste cambios',
  done: 'Listo',
  declined: 'No se hará',
};

export function statusChip(status?: string): string {
  return STATUS_CHIPS[status || ''] || status || '';
}
