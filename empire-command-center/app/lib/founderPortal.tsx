'use client';

import { Gauge, LifeBuoy } from 'lucide-react';
import FamilyHelpInbox from '../components/screens/FamilyHelpInbox';
import MinimaxUsageScreen from '../components/screens/MinimaxUsageScreen';
import {
  FOUNDER_COMMAND_NAV_SPECS,
  injectFounderCommandItems,
  isFounderScreen,
} from './founderScreens';

export function renderFounderScreen(activeScreen: string) {
  if (activeScreen === 'family-help') return <FamilyHelpInbox />;
  if (activeScreen === 'minimax-usage') return <MinimaxUsageScreen />;
  return null;
}

export function founderCommandNavItems() {
  return FOUNDER_COMMAND_NAV_SPECS.map((spec) => ({
    ...spec,
    icon: spec.id === 'family-help' ? <LifeBuoy size={16} /> : <Gauge size={16} />,
  }));
}

export function hookFounderNav<T extends { key?: string; items: { id: string }[] }>(groups: T[]): T[] {
  return injectFounderCommandItems(groups, founderCommandNavItems());
}

export { hookFounderDeepLinks, isFounderScreen } from './founderScreens';
