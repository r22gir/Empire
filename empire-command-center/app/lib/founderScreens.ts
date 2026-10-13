/** Founder-only portal screens. Isolated so Dell merges only need one-line hooks. */

export const FOUNDER_SCREEN_IDS = ['family-help'] as const;
export type FounderScreenMode = (typeof FOUNDER_SCREEN_IDS)[number];

export const FOUNDER_SCREEN_DEEP_LINKS: Record<FounderScreenMode, FounderScreenMode> = {
  'family-help': 'family-help',
};

export const FOUNDER_COMMAND_NAV_SPECS = [
  {
    id: 'family-help',
    name: 'Ayuda de ediciones familiares',
    screen: 'family-help',
    status: 'active' as const,
    color: '#b8960c',
    kind: 'screen' as const,
  },
] as const;

export const EMPIRE_ASSIST_NAV = {
  id: 'assist',
  name: 'Empire Assist: Family Requests',
  status: 'active' as const,
  color: '#b8960c',
  kind: 'product' as const,
  screen: 'family-help',
} as const;

export function isFounderScreen(screen: string | null | undefined): screen is FounderScreenMode {
  return !!screen && (FOUNDER_SCREEN_IDS as readonly string[]).includes(screen);
}

export function isEmpireAssistPath(pathname: string | null | undefined): boolean {
  const path = (pathname || '').replace(/\/+$/, '') || '/';
  return path === '/empireassist' || path === '/empire-assist';
}

export function hookFounderDeepLinks(
  deepLinks: Record<string, string>,
  screenIds: Set<string>,
): void {
  Object.assign(deepLinks, FOUNDER_SCREEN_DEEP_LINKS);
  for (const id of FOUNDER_SCREEN_IDS) {
    screenIds.add(id);
  }
  screenIds.add('empireassist');
  screenIds.add('empire-assist');
}

export function injectFounderCommandItems<T extends { key?: string; items: { id: string }[] }>(
  groups: T[],
  extras: { id: string }[],
): T[] {
  const command = groups.find((group) => group.key === 'command');
  if (!command) return groups;
  const toAdd = extras.filter((item) => !command.items.some((existing) => existing.id === item.id));
  if (!toAdd.length) return groups;
  const ownerIdx = command.items.findIndex((existing) => existing.id === 'owner');
  command.items.splice(ownerIdx >= 0 ? ownerIdx + 1 : 0, 0, ...toAdd);
  return groups;
}

export function renameAssistNavItem<T extends { id: string; name?: string; status?: string; screen?: string }>(
  items: T[],
): T[] {
  return items.map((item) => {
    if (item.id !== 'assist') return item;
    return {
      ...item,
      name: EMPIRE_ASSIST_NAV.name,
      status: EMPIRE_ASSIST_NAV.status,
      screen: EMPIRE_ASSIST_NAV.screen,
    };
  });
}
