'use client';

import { LifeBuoy } from 'lucide-react';
import EmpireAssistPage from '../components/screens/EmpireAssistPage';
import {
  EMPIRE_ASSIST_NAV,
  FOUNDER_COMMAND_NAV_SPECS,
  injectFounderCommandItems,
  isEmpireAssistPath,
  isFounderScreen,
  renameAssistNavItem,
} from './founderScreens';

export function renderFounderScreen(activeScreen: string, activeProduct?: string) {
  if (activeScreen === 'family-help' || activeProduct === 'assist') {
    return <EmpireAssistPage />;
  }
  return null;
}

export function founderCommandNavItems() {
  return FOUNDER_COMMAND_NAV_SPECS.map((spec) => ({
    ...spec,
    icon: <LifeBuoy size={16} />,
  }));
}

export function hookFounderNav<T extends { key?: string; items: { id: string; name?: string; status?: string }[] }>(
  groups: T[],
): T[] {
  for (const group of groups) {
    group.items = renameAssistNavItem(group.items);
  }
  return injectFounderCommandItems(groups, founderCommandNavItems());
}

export { hookFounderDeepLinks, isEmpireAssistPath, isFounderScreen, EMPIRE_ASSIST_NAV } from './founderScreens';
