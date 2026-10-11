/** Founder-only portal screens. Isolated so Dell merges only need one-line hooks. */

export const FOUNDER_SCREEN_IDS = ['family-help', 'minimax-usage'] as const;
export type FounderScreenMode = (typeof FOUNDER_SCREEN_IDS)[number];

export const FOUNDER_SCREEN_DEEP_LINKS: Record<FounderScreenMode, FounderScreenMode> = {
  'family-help': 'family-help',
  'minimax-usage': 'minimax-usage',
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
  {
    id: 'minimax-usage',
    name: 'Uso MiniMax',
    screen: 'minimax-usage',
    status: 'active' as const,
    color: '#b8960c',
    kind: 'screen' as const,
  },
] as const;

export function isFounderScreen(screen: string | null | undefined): screen is FounderScreenMode {
  return !!screen && (FOUNDER_SCREEN_IDS as readonly string[]).includes(screen);
}

export function hookFounderDeepLinks(
  deepLinks: Record<string, string>,
  screenIds: Set<string>,
): void {
  Object.assign(deepLinks, FOUNDER_SCREEN_DEEP_LINKS);
  for (const id of FOUNDER_SCREEN_IDS) {
    screenIds.add(id);
  }
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
