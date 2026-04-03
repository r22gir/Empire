'use client';
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import React from 'react';
import type { Locale, I18nContextType, TranslationModule } from './types';
import { detectBrowserLocale } from './languages';

const STORAGE_KEY = 'empire-locale';

// Cache loaded translations in memory
const translationCache: Record<string, TranslationModule> = {};

/** Resolve a dotted key path in a nested object */
function resolve(obj: TranslationModule, path: string): string | undefined {
  const parts = path.split('.');
  let current: any = obj;
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return undefined;
    current = current[part];
  }
  return typeof current === 'string' ? current : undefined;
}

/** Interpolate {{var}} placeholders */
function interpolate(str: string, params?: Record<string, string | number>): string {
  if (!params) return str;
  return str.replace(/\{\{(\w+)\}\}/g, (_, key) => String(params[key] ?? `{{${key}}}`));
}

async function loadModule(locale: Locale, module: string): Promise<TranslationModule> {
  const cacheKey = `${locale}/${module}`;
  if (translationCache[cacheKey]) return translationCache[cacheKey];
  try {
    const mod = await import(`./locales/${locale}/${module}.json`);
    translationCache[cacheKey] = mod.default || mod;
    return translationCache[cacheKey];
  } catch {
    // Fall back to English if locale file missing
    if (locale !== 'en') {
      try {
        const fallback = await import(`./locales/en/${module}.json`);
        translationCache[cacheKey] = fallback.default || fallback;
        return translationCache[cacheKey];
      } catch { /* no fallback either */ }
    }
    translationCache[cacheKey] = {};
    return {};
  }
}

const I18nContext = createContext<I18nContextType>({
  locale: 'en',
  setLocale: () => {},
  t: (key) => key,
  isLoading: false,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('en');
  const [translations, setTranslations] = useState<TranslationModule>({});
  const [isLoading, setIsLoading] = useState(false);

  // Initialize locale from storage or browser detection
  useEffect(() => {
    const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) as Locale : null;
    const initial = stored || detectBrowserLocale();
    setLocaleState(initial);
  }, []);

  // Load common translations when locale changes
  useEffect(() => {
    setIsLoading(true);
    loadModule(locale, 'common').then(mod => {
      setTranslations(mod);
      setIsLoading(false);
    });
  }, [locale]);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, newLocale);
    }
  }, []);

  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    const value = resolve(translations, key);
    if (value) return interpolate(value, params);
    // Return the last segment of the key as readable fallback
    return key.split('.').pop() || key;
  }, [translations]);

  return React.createElement(I18nContext.Provider, { value: { locale, setLocale, t, isLoading } }, children);
}

/** Main hook — use in any component */
export function useTranslation(module?: string) {
  const ctx = useContext(I18nContext);
  const [moduleTrans, setModuleTrans] = useState<TranslationModule>({});

  useEffect(() => {
    if (module) {
      loadModule(ctx.locale, module).then(setModuleTrans);
    }
  }, [module, ctx.locale]);

  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    // First check module-specific translations
    if (module) {
      const modValue = resolve(moduleTrans, key);
      if (modValue) return interpolate(modValue, params);
    }
    // Fall back to common/context translations
    return ctx.t(key, params);
  }, [module, moduleTrans, ctx]);

  return { t, locale: ctx.locale, setLocale: ctx.setLocale, isLoading: ctx.isLoading };
}

export { I18nContext };
export type { Locale, I18nContextType };
