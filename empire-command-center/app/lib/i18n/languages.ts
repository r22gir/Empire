import type { Locale } from './types';

/** All translation modules that can be lazy-loaded */
export const TRANSLATION_MODULES = [
  'common', 'dashboard', 'crm', 'workroom', 'craftforge',
  'marketplace', 'social', 'construction', 'storefront', 'max',
  'relist', 'leads',
] as const;

export type TranslationModuleName = typeof TRANSLATION_MODULES[number];

/** Default locale per product */
export const PRODUCT_DEFAULT_LOCALE: Record<string, Locale> = {
  construction: 'es',
  // All others default to 'en'
};

/** Detect browser locale and map to supported locale */
export function detectBrowserLocale(): Locale {
  if (typeof navigator === 'undefined') return 'en';
  const lang = navigator.language?.toLowerCase() || 'en';
  if (lang.startsWith('es')) return 'es';
  return 'en';
}
