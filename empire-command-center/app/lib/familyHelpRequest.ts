export type FamilyRequestType = 'Ajuste' | 'Arreglo' | 'Crear';

export const FAMILY_REQUEST_OFFER = '¿Quieres que le pase esto a Rafael como solicitud?';

function foldAccents(text: string): string {
  return String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

const ARREGLO_RE = /no\s+(?:me\s+)?(?:funciona|anda|carga|abre|sale|deja|puedo)|se\s+(?:romp|cae|traba|congela|cierra)|error|falla|bug|roto|rota|404|500|doesn'?t\s+work|not\s+working|broken|crashed|crash/i;
const CREAR_RE = /(?:puedes|podrias|quiero|quisiera)\s+(?:agregar|anadir|crear|hacer)|agrega(?:r)?|anade(?:r)?|nueva\s+(?:funcion|caracteristica|feature)|can\s+you\s+add|please\s+add|new\s+feature|add\s+a\s+/i;
const AJUSTE_RE = /quisiera\s+que|me\s+gustaria\s+que|preferiria|puedes\s+(?:cambiar|ajustar|mejorar)|podrias\s+(?:cambiar|ajustar|mejorar)|ajusta(?:r)?|cambia(?:r)?|mejorar|ajuste|would\s+like|please\s+change|adjust|tweak/i;
const HELP_INTENT_RE = /pide(?:r|le)?\s+ayuda\s+a\s+max|pedir\s+ayuda\s+a\s+max|ask(?:\s+for)?\s+help(?:\s+from)?\s+(?:to\s+)?max|ask\s+max\s+for\s+help|help\s+from\s+max/i;
const REQUEST_NOISE_RE = /^(hola|hello|hi|hey|gracias|thanks|ok|okay|si|sí|no|vale)(?:[!?.\s]*)$/i;

export function classifyFamilyRequest(message: string): FamilyRequestType | null {
  const text = foldAccents((message || '').trim());
  if (!text || HELP_INTENT_RE.test(text)) return null;
  if (REQUEST_NOISE_RE.test(text) && text.split(/\s+/).length <= 3) return null;
  if (ARREGLO_RE.test(text)) return 'Arreglo';
  if (CREAR_RE.test(text)) return 'Crear';
  if (AJUSTE_RE.test(text)) return 'Ajuste';
  return null;
}

export function familyRequestOffer(message: string): {
  suggested_type: FamilyRequestType;
  offer: string;
  source_message: string;
} | null {
  const kind = classifyFamilyRequest(message);
  if (!kind) return null;
  return {
    suggested_type: kind,
    offer: FAMILY_REQUEST_OFFER,
    source_message: (message || '').trim().slice(0, 500),
  };
}
