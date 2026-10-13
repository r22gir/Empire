/**
 * Client-side Simli / avatar lip-sync timing.
 * Must stay in lockstep with backend/app/services/max/simli_lipsync.py
 */
export const LIP_SYNC_OFFSET_MS = 220;
export const SIMLI_SAMPLE_RATE = 16000;
export const PREFERRED_CHUNK_BYTES = 6000;

export type LipsyncConfig = {
  playback_delay_ms: number;
  lip_sync_offset_ms: number;
  sample_rate: number;
  chunk_bytes: number;
};

export function playbackDelayMs(config?: Partial<LipsyncConfig> | null): number {
  const raw = config?.playback_delay_ms ?? config?.lip_sync_offset_ms ?? LIP_SYNC_OFFSET_MS;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : LIP_SYNC_OFFSET_MS;
}

/** Slice an Int16Array to the exact view — never send the backing ArrayBuffer. */
export function pcm16WireBytes(int16: Int16Array | ArrayBuffer): ArrayBuffer {
  if (int16 instanceof ArrayBuffer) return int16;
  return int16.buffer.slice(int16.byteOffset, int16.byteOffset + int16.byteLength);
}

export function chunkPcm16(bytes: ArrayBuffer, chunkBytes = PREFERRED_CHUNK_BYTES): ArrayBuffer[] {
  const size = Math.max(2, chunkBytes - (chunkBytes % 2));
  const out: ArrayBuffer[] = [];
  for (let i = 0; i < bytes.byteLength; i += size) {
    out.push(bytes.slice(i, Math.min(i + size, bytes.byteLength)));
  }
  return out;
}

export function delayMs(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));
}
