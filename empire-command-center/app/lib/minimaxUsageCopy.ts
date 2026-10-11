export function minimaxUsageLabels(locale: string = 'es') {
  const es = locale.toLowerCase().startsWith('es');
  return {
    nav: es ? 'Uso MiniMax' : 'MiniMax usage',
    title: es ? 'Uso MiniMax por edición' : 'MiniMax usage by edition',
    intro: es
      ? 'Max-e y Maxine: 10% cada una del cupo de texto (juntas bajo el 20%). La parte de Rafael queda reservada. No se gastan créditos de regalo.'
      : 'Max-e and Maxine: 10% each of the text pool (together under 20%). Rafael\'s share stays reserved. Gift credits are not spent.',
    plan: es ? 'Barra del plan' : 'Plan bar',
    reserved: es ? 'Reservado para Rafael' : 'Reserved for Rafael',
    family: es ? 'Familia (Max-e + Maxine)' : 'Family (Max-e + Maxine)',
    images: es ? 'Imágenes hoy' : 'Images today',
    voice: es ? 'Voz hoy' : 'Voice today',
    video: es ? 'Video esta semana' : 'Video this week',
    approve: es ? 'Aprobar' : 'Approve',
    reject: es ? 'Rechazar' : 'Reject',
    queue: es ? 'Cola de video H3 (borradores)' : 'H3 video queue (drafts)',
    aiLabel: es ? 'Generado por IA. No publicado.' : 'AI-generated. Not posted.',
    denied: es ? 'Solo el Max personal de Rafael ve este medidor.' : 'Only Rafael\'s personal Max can see this meter.',
    credits: es
      ? 'Los créditos de regalo no se usan. Si la barra del plan llega al 80%, todos los agentes se detienen. Si remains no responde, se bloquea (imágenes, voz, video, texto familiar). Apaga Auto credit usage en MiniMax.'
      : 'Gift credits are not used. If the plan bar reaches 80%, every agent stops. If remains is down, we block (images, voice, video, family text). Turn off Auto credit usage on MiniMax.',
    remainsDown: es
      ? 'No hay lectura de /token_plan/remains. Bloqueo cerrado. El texto personal sigue solo con la estimación local. Recomendación: apaga Auto credit usage.'
      : 'Could not read /token_plan/remains. Fail closed. Personal text continues only on the local estimate. Recommendation: turn off Auto credit usage.',
    generate: es ? 'Generar (aprobar)' : 'Generate (approve)',
  };
}
