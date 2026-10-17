export const PEDIR_CURSOR_COPY = {
  button: 'Pedir a Cursor',
  title: 'Pedir a Cursor',
  note: 'Esto no lanza nada solo: Chief e lo revisa, te muestra el cambio y Rafael da el sí final.',
  editionLabel: 'Edición: Max-e',
  fieldTitle: 'Título',
  fieldBody: '¿Qué necesitas y por qué?',
  fieldShots: 'Capturas (opcional)',
  submit: 'Enviar pedido',
  paused: 'Manito, ya usaste tu 20% del mes y Rafael está usando Max ahora. Guárdalo y lo mandas en un rato.',
  approve: 'Aprobar',
  changes: 'Pedir cambios',
  statuses: {
    queued: 'En cola',
    in_progress: 'En progreso',
    pr_open: 'PR listo para revisar',
    owner_approved: 'Aprobado por ti',
    changes_requested: 'Pediste cambios',
    done: 'Listo',
    declined: 'No se hará',
  } as Record<string, string>,
};

export function pedirCursorStatusLabel(status: string): string {
  return PEDIR_CURSOR_COPY.statuses[status] || status;
}
