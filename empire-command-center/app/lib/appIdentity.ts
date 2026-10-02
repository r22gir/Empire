/**
 * App chrome title. Family editions are a personal command center
 * named after the assistant. A business inside the instance (AMP,
 * a GAC project) is not the app name.
 */
export function appTitleFromEnv(): string {
  const display = (process.env.NEXT_PUBLIC_EDITION_DISPLAY_NAME || '').trim();
  if (display) return display;
  const edition = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').trim().toLowerCase();
  if (edition !== 'amp' && edition !== 'maxine') return 'Empire Command Center';
  const fallback = edition === 'maxine' ? 'Maxine' : 'Max-e';
  const name = (process.env.NEXT_PUBLIC_ASSISTANT_NAME || '').trim() || fallback;
  return `${name} · Centro de mando`;
}

export function appDescriptionFromEnv(): string {
  const edition = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').trim().toLowerCase();
  if (edition === 'maxine') {
    return 'Centro de mando de desarrollos. El portafolio vive en ConstructionForge.';
  }
  if (edition === 'amp') {
    return 'Centro de mando del asistente. Las empresas de esta instancia viven adentro.';
  }
  return 'Business Operating System';
}
