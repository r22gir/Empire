export function familyHelpLabels(locale: string) {
  const es = (locale || 'es').toLowerCase().startsWith('es');
  return {
    ask: es ? 'Pedir ayuda a Max' : 'Ask Max for help',
    inbox: es ? 'Ayuda de ediciones familiares' : 'Family help',
    title: es ? 'Pedir ayuda a Max' : 'Ask Max for help',
    hint: es
      ? 'Escribe, graba un audio o adjunta una captura. Max (el de Rafael) lo verá. No se envían datos del Workroom.'
      : 'Type, record audio, or attach a screenshot. Rafael’s Max will see it. Workroom data is never sent.',
    message: es ? '¿Qué necesitas?' : 'What do you need?',
    send: es ? 'Enviar a Max' : 'Send to Max',
    sending: es ? 'Enviando…' : 'Sending…',
    voice: es ? 'Grabar audio' : 'Record audio',
    stopVoice: es ? 'Detener' : 'Stop',
    attach: es ? 'Adjuntar' : 'Attach',
    close: es ? 'Cerrar' : 'Close',
    sent: es ? 'Pedido enviado' : 'Request sent',
    replies: es ? 'Respuestas de Max' : 'Replies from Max',
    empty: es ? 'Aún no hay pedidos.' : 'No requests yet.',
    new: es ? 'Nuevo' : 'New',
    answered: es ? 'Respondido' : 'Answered',
    closedStatus: es ? 'Cerrado' : 'Closed',
    reply: es ? 'Responder' : 'Reply',
    sendReply: es ? 'Enviar respuesta' : 'Send reply',
    draft: es ? 'Borrador de Max' : 'Max draft',
    confirm: es ? 'Sí, enviar' : 'Yes, send',
    play: es ? 'Reproducir audio' : 'Play audio',
    transcript: es ? 'Transcripción' : 'Transcript',
    transcriptPending: es ? 'Transcripción pendiente' : 'Transcription pending',
    retryTranscript: es ? 'Reintentar transcripción' : 'Retry transcription',
    context: es ? 'Contexto del chat' : 'Chat context',
    files: es ? 'Archivos' : 'Files',
    fileTooBig: es ? 'El archivo supera 8 MB' : 'File is larger than 8 MB',
    fileTypeBlocked: es ? 'Tipo de archivo no permitido' : 'File type not allowed',
    attachmentWarning: es
      ? 'Aviso: el contenido de los adjuntos no se redacta. Solo se ocultan datos en el texto, la transcripción y el nombre del archivo.'
      : 'Warning: attachment contents are not redacted. Only the message, transcript, and filename are scrubbed.',
    hiddenAttachments: es
      ? 'Adjuntos de Maxine ocultos. Ábrelos solo cuando Rafael los revise.'
      : 'Maxine attachments are hidden until Rafael opens them.',
    openAttachments: es ? 'Abrir adjuntos' : 'Open attachments',
    usageNote: es
      ? 'El tope del 20% usa una estimación de tokens (caracteres ÷ 4 + archivo/voz), no el conteo del proveedor.'
      : 'The 20% cap uses a token estimate (characters ÷ 4 + file/voice overhead), not the provider count.',
    replyUsage: es ? 'Uso de respuestas cobrado a esta edición' : 'Reply usage charged to this edition',
    needYes: es
      ? 'Max no envía ni cambia nada sin tu sí explícito.'
      : 'Max will not send or change anything without your explicit yes.',
    noApply: es
      ? 'Los arreglos de código van por un PR de cloud-agent. Este ticket no escribe en la edición familiar.'
      : 'Code fixes go through a cloud-agent PR. This ticket does not write to the family edition.',
    passToRafael: es
      ? '¿Quieres que le pase esto a Rafael como solicitud?'
      : 'Want me to pass this to Rafael as a request?',
    yesPass: es ? 'Sí' : 'Yes',
    requestFiled: es ? 'Listo. Se lo pasé a Rafael.' : 'Done. I passed it to Rafael.',
    requestType: es ? 'Tipo' : 'Type',
  };
}
