/** Chat mic helpers. Touch defaults to tap-to-start / tap-to-stop. */

export const MIN_RECORDING_MS = 500;
export const HOLD_ARM_MS = 450;
export const HOLD_LONGER_HINT = 'Hold longer';
export const TRANSCRIBE_FAILED_HINT = 'Could not transcribe that recording';

export function clipTooShort(elapsedMs) {
  return elapsedMs < MIN_RECORDING_MS;
}

/** Touch: a second tap stops. Mouse: press starts, release stops. */
export function pointerDownAction(input) {
  if (input.touchDevice && input.alreadyRecording) return 'stop';
  if (input.alreadyRecording) return 'ignore';
  return 'start';
}

/**
 * The pointerup that follows a tap must not stop the take.
 * Holding past HOLD_ARM_MS opts into hold-to-talk, and a mouse
 * press is hold-to-talk already.
 */
export function shouldStopOnPointerUp(input) {
  if (input.touchDevice && !input.holdArmed) return false;
  return true;
}

export function isSafariUserAgent(userAgent) {
  const ua = userAgent || '';
  if (/iPhone|iPad|iPod/i.test(ua)) return true;
  return /safari/i.test(ua) && !/chrome|chromium|android|crios|fxios|edg/i.test(ua);
}

export function recorderFormat(userAgent, supported = () => false) {
  if (isSafariUserAgent(userAgent)) {
    return { mimeType: 'audio/mp4', filename: 'recording.mp4' };
  }
  if (supported('audio/webm;codecs=opus') || supported('audio/webm')) {
    return {
      mimeType: supported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm',
      filename: 'recording.webm',
    };
  }
  if (supported('audio/mp4')) return { mimeType: 'audio/mp4', filename: 'recording.mp4' };
  return { mimeType: 'audio/webm', filename: 'recording.webm' };
}

export function filenameForMime(mimeType) {
  const mime = (mimeType || '').toLowerCase();
  if (mime.includes('mp4') || mime.includes('m4a') || mime.includes('aac')) return 'recording.mp4';
  if (mime.includes('ogg')) return 'recording.ogg';
  if (mime.includes('wav')) return 'recording.wav';
  return 'recording.webm';
}

/** UI Spanish is passed through. English and unknown locales auto-detect. */
export function sttLanguage(locale) {
  const lang = (locale || '').toLowerCase();
  if (lang.startsWith('es')) return 'es';
  return null;
}

export function transcriptIsFailure(text) {
  const value = (text || '').trim();
  if (!value) return true;
  if (!value.startsWith('[')) return false;
  return /transcription failed|stt unavailable|audio file not found|could not process/i.test(value);
}

/** Toast copy. A Spanish UI does not show the English hint. */
export function micToast(kind, locale) {
  const es = String(locale || '').toLowerCase().startsWith('es');
  if (kind === 'short') return es ? 'Mantén un poco más' : HOLD_LONGER_HINT;
  if (kind === 'failed') return es ? 'No pude transcribir esa grabación' : TRANSCRIBE_FAILED_HINT;
  if (kind === 'denied') return es ? 'No hay acceso al micrófono' : 'Microphone access denied';
  return '';
}
