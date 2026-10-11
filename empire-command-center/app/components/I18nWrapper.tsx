'use client';
import { ReactNode } from 'react';
import { I18nProvider } from '../lib/i18n';
import { JobProvider } from '../hooks/useJob';
import FamilyTranslate from './FamilyTranslate';

export function I18nWrapper({ children }: { children: ReactNode }) {
  return (
    <I18nProvider>
      <JobProvider>
        {children}
        <FamilyTranslate />
      </JobProvider>
    </I18nProvider>
  );
}
