/** Interview welcome and the Maxine Argos consent step. Plain JS so Node 20 can import it. */

const SHARED = [
  { id: 'bienvenida', es: 'Bienvenida', en: 'Welcome' },
  { id: 'empresa', es: 'Tu empresa', en: 'Your company' },
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

export const ARGOS_OPTIONS = [
  {
    id: 'all',
    es: 'Sí, cargar todo',
    en: 'Yes, load all of it',
    detailEs: 'El lugar, los planos de 2022–2023 y la marca. Queda Confidencial hasta que lo apruebes.',
    detailEn: 'The place, the 2022–2023 plans, and the brand. It stays confidential until you approve it.',
  },
  {
    id: 'public',
    es: 'Solo lo público',
    en: 'Only what is public',
    detailEs: 'Solo la descripción pública del proyecto. También queda Confidencial hasta que la apruebes.',
    detailEn: 'Only the public description of the project. That stays confidential until you approve it too.',
  },
  {
    id: 'later',
    es: 'Ahora no',
    en: 'Not now',
    detailEs: 'No cargo nada de Argos Campestre en esta entrevista.',
    detailEn: 'I will not load Argos Campestre in this interview.',
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
  const offerAt = 3;
  const steps = SHARED.slice();
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
      ? 'También te voy a preguntar si quieres que Rafael cargue la información de Argos Campestre que ya tiene. Todo eso queda Confidencial hasta que tú lo apruebes.'
      : '',
    argosNoteEn: kind === 'maxine'
      ? 'I will also ask whether you want Rafael to load the Argos Campestre information he already has. All of that stays confidential until you approve it.'
      : '',
  };
}
