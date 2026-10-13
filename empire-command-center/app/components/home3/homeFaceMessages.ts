/**
 * Home-face host messages from /avatar.html.
 * Early Simli onStatus posts are progress, not failure — only a hard
 * failure or a 15s hang should tear down the iframe (and the session).
 */

export const HOME_FACE_LOAD_TIMEOUT_MS = 15_000;
export const HOME_FACE_UNAVAILABLE = 'Face unavailable — tap to retry';

export type HomeFacePhase = 'orb' | 'ready' | 'live';

export type HomeFaceView = {
  phase: HomeFacePhase;
  started: boolean;
  loaded: boolean;
  hint: string;
};

export type AvatarHostMessage = {
  type?: string;
  success?: boolean;
  renderer?: string;
};

export function iframeMounted(view: HomeFaceView): boolean {
  return view.phase === 'live';
}

export function isHomeFaceHardFailure(data: AvatarHostMessage | null | undefined): boolean {
  if (!data) return false;
  if (data.type !== 'avatar-status' && data.type !== 'avatar-loaded') return false;
  if (data.renderer === 'none') return true;
  if (data.type === 'avatar-loaded' && data.success === false) return true;
  return false;
}

export function startHomeFace(view: HomeFaceView): HomeFaceView {
  if (view.started) return view;
  return { phase: 'live', started: true, loaded: false, hint: '' };
}

function unavailable(): HomeFaceView {
  return {
    phase: 'orb',
    started: false,
    loaded: false,
    hint: HOME_FACE_UNAVAILABLE,
  };
}

export function applyHomeFaceMessage(view: HomeFaceView, data: AvatarHostMessage): HomeFaceView {
  if (data?.type !== 'avatar-status' && data?.type !== 'avatar-loaded') return view;
  if (isHomeFaceHardFailure(data)) return unavailable();
  if (data.type === 'avatar-loaded' && data.success !== false) {
    return { ...view, loaded: true };
  }
  return view;
}

export function applyHomeFaceTimeout(view: HomeFaceView, elapsedMs: number): HomeFaceView {
  if (view.phase !== 'live' || view.loaded) return view;
  if (elapsedMs < HOME_FACE_LOAD_TIMEOUT_MS) return view;
  return unavailable();
}
