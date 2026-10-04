/** Interview welcome and the Maxine Argos consent step. Plain JS so Node 20 can import it. */

const SHARED = [
  { id: 'bienvenida', es: 'Bienvenida', en: 'Welcome' },
  { id: 'empresa', es: 'Tu empresa', en: 'Your company' },
  { id: 'whatsapp', es: 'Conectar WhatsApp', en: 'Connect WhatsApp' },
  { id: 'industria', es: 'Industria', en: 'Industry' },
  { id: 'clientes', es: 'Clientes', en: 'Customers' },
  { id: 'dinero', es: 'Dinero', en: 'Money' },
  { id: 'equipo', es: 'Equipo', en: 'Team' },
  { id: 'herramientas', es: 'Herramientas', en: 'Tools' },
  { id: 'confirmar', es: 'Confirmar datos', en: 'Confirm facts' },
  { id: 'revision', es: 'Revisión', en: 'Review' },
];

const OFFER = {
  amp: { id: 'oferta', es: 'Qué vendes', en: 'What you sell' },
  maxine: { id: 'oferta', es: 'Qué vendes, etapas y lotes', en: 'What you sell, phases and lots' },
};

const ARGOS_STEP = { id: 'argos', es: 'Argos Campestre', en: 'Argos Campestre' };

export const ARGOS_QUESTION = {
  es: '¿Quieres que Rafael cargue toda la información relacionada con Argos Campestre que tiene (correos y archivos 2021–2024, planos) para que yo la revise contigo?',
  en: 'Do you want Rafael to load all the Argos Campestre information he has (emails and files from 2021–2024, plans) so I can review it with you?',
};

export const ARGOS_OPTIONS = [
  {
    id: 'all',
    es: 'Sí, cargar todo',
    en: 'Yes, load all of it',
    detailEs: 'Creo la tarea «Importación Argos pendiente» para Rafael y te muestro la cola de revisión. Cada pieza entra Confidencial y no se usa ni se muestra hasta que tú la apruebes.',
    detailEn: 'I create the task “Importación Argos pendiente” for Rafael and show you the review queue. Each piece stays confidential and is not used or shown until you approve it.',
  },
  {
    id: 'public',
    es: 'Solo lo público',
    en: 'Only what is public',
    detailEs: 'Dejo solo la semilla pública. No cargo correos, archivos ni planos.',
    detailEn: 'I keep only the public seed. I do not load emails, files, or plans.',
  },
  {
    id: 'later',
    es: 'Ahora no',
    en: 'Not now',
    detailEs: 'No cargo nada de eso ahora.',
    detailEn: 'I will not load any of that now.',
  },
];

function family(edition) {
  const key = String(edition || '').trim().toLowerCase();
  if (key === 'maxine') return 'maxine';
  if (key === 'amp' || key === 'max-e' || key === 'max_e' || key === 'maxe') return 'amp';
  return 'amp';
}

export function interviewSteps(edition) {
  const kind = family(edition);
  const steps = SHARED.slice();
  // Place offer step after industria
  const industriaIndex = steps.findIndex((s) => s.id === 'industria');
  const offerAt = industriaIndex >= 0 ? industriaIndex + 1 : 4;
  steps.splice(offerAt, 0, OFFER[kind]);
  if (kind === 'maxine') steps.splice(1, 0, ARGOS_STEP);
  return steps;
}

export function welcomeCopy(edition) {
  const kind = family(edition);
  const sections = interviewSteps(kind)
    .filter((step) => step.id !== 'bienvenida' && step.id !== 'argos')
    .map((step) => ({ es: step.es, en: step.en }));
  return {
    introEs: 'Esta entrevista recorre tu empresa de principio a fin, una pregunta por pantalla. Puedes volver atrás, guardar y seguir después. Nada queda creado hasta la revisión.',
    introEn: 'This interview walks through your company from start to finish, one question per screen. You can go back, save, and continue later. Nothing is created until the review.',
    sections,
    argosNoteEs: kind === 'maxine'
      ? 'También te voy a preguntar si quieres que Rafael cargue los correos, archivos 2021–2024 y planos de Argos Campestre. Nada de eso se usa ni se muestra hasta que tú lo apruebes. Queda Confidencial.'
      : '',
    argosNoteEn: kind === 'maxine'
      ? 'I will also ask whether you want Rafael to load the Argos Campestre emails, 2021–2024 files, and plans. None of that is used or shown until you approve it. It stays confidential.'
      : '',
  };
}
