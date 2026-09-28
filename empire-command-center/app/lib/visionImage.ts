/** Longest edge sent to /api/v1/vision/*. Smoke measure succeeded at 1280×960. */
export const VISION_IMAGE_MAX_EDGE = 1600;
export const VISION_IMAGE_JPEG_QUALITY = 0.8;

/**
 * Client cap for vision POSTs that travel through the Next rewrite proxy.
 * The proxy itself waits 180s. Past that, abort so a 500 or a hung socket
 * cannot leave Photo Analyzer / Quote Review spinning.
 */
export const VISION_REQUEST_TIMEOUT_MS = 185_000;

export function visionAbortSignal(ms: number = VISION_REQUEST_TIMEOUT_MS): AbortSignal {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(ms);
  }
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

export function visionTimeoutMessage(err: unknown): string | null {
  const name = err && typeof err === 'object' && 'name' in err ? String((err as { name?: string }).name) : '';
  if (name === 'TimeoutError' || name === 'AbortError') {
    return 'Analysis timed out. The vision service did not respond, so the spinner was stopped.';
  }
  return null;
}

export function fitWithinMaxEdge(
  width: number,
  height: number,
  maxEdge: number = VISION_IMAGE_MAX_EDGE,
): { width: number; height: number } {
  const w = Math.max(0, Math.round(Number(width) || 0));
  const h = Math.max(0, Math.round(Number(height) || 0));
  if (w < 1 || h < 1) {
    return { width: Math.max(w, 1), height: Math.max(h, 1) };
  }
  const longest = Math.max(w, h);
  if (!Number.isFinite(maxEdge) || maxEdge < 1 || longest <= maxEdge) {
    return { width: w, height: h };
  }
  const scale = maxEdge / longest;
  return {
    width: Math.max(1, Math.round(w * scale)),
    height: Math.max(1, Math.round(h * scale)),
  };
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const timer = setTimeout(() => reject(new Error('Image decode timed out')), 15_000);
    img.onload = () => {
      clearTimeout(timer);
      resolve(img);
    };
    img.onerror = () => {
      clearTimeout(timer);
      reject(new Error('Could not decode image'));
    };
    img.src = src;
  });
}

/**
 * Downscale a data-URL photo before a vision POST.
 * Phone camera JPEGs are often multi-MB; base64 plus the Next rewrite body
 * clone (default 10MB) drops the socket. Returns the original string when
 * the image is already small, decoding fails, or this is not a browser.
 */
export async function compressImageDataUrl(
  dataUrl: string,
  options?: { maxEdge?: number; quality?: number },
): Promise<string> {
  if (typeof dataUrl !== 'string' || !dataUrl.startsWith('data:image/')) {
    return dataUrl;
  }
  if (typeof document === 'undefined') return dataUrl;

  const maxEdge = options?.maxEdge ?? VISION_IMAGE_MAX_EDGE;
  const quality = options?.quality ?? VISION_IMAGE_JPEG_QUALITY;

  try {
    const img = await loadImage(dataUrl);
    const sourceWidth = img.naturalWidth || img.width;
    const sourceHeight = img.naturalHeight || img.height;
    const target = fitWithinMaxEdge(sourceWidth, sourceHeight, maxEdge);
    const alreadyFits = target.width === sourceWidth && target.height === sourceHeight;
    const alreadyJpeg = dataUrl.startsWith('data:image/jpeg') || dataUrl.startsWith('data:image/jpg');
    // ~700KB binary. Skip a re-encode that cannot shrink a small JPEG.
    if (alreadyFits && alreadyJpeg && dataUrl.length < 950_000) {
      return dataUrl;
    }

    const canvas = document.createElement('canvas');
    canvas.width = target.width;
    canvas.height = target.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return dataUrl;
    ctx.drawImage(img, 0, 0, target.width, target.height);
    const out = canvas.toDataURL('image/jpeg', quality);
    if (!out || !out.startsWith('data:image/jpeg')) return dataUrl;
    if (alreadyFits && out.length >= dataUrl.length) return dataUrl;
    return out;
  } catch {
    return dataUrl;
  }
}
