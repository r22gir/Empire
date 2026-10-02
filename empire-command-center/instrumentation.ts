function loadHttp(): typeof import('http') {
  const proc = process as NodeJS.Process & { getBuiltinModule?: (id: string) => typeof import('http') };
  if (typeof proc.getBuiltinModule === 'function') return proc.getBuiltinModule('http');
  const loaded = new Function('return typeof require === "function" ? require("http") : null')() as
    | typeof import('http')
    | null;
  if (loaded) return loaded;
  throw new Error('http module unavailable');
}

export async function register() {
  if (process.env.NEXT_RUNTIME !== 'nodejs') return;
  const http = loadHttp();
  const { stampIncomingMessage } = await import('./app/lib/tailscaleProxy');
  const proto = http.Server.prototype as typeof http.Server.prototype & { __empireStamped?: boolean };
  if (proto.__empireStamped) return;
  const original = proto.emit as (this: unknown, event: string | symbol, ...args: unknown[]) => boolean;
  proto.emit = function (this: typeof http.Server.prototype, event: string | symbol, ...args: unknown[]) {
    if (event === 'request' || event === 'upgrade') {
      const req = args[0] as { headers?: Record<string, string | string[] | undefined>; socket?: { remoteAddress?: string } } | undefined;
      if (req?.headers && req.socket) stampIncomingMessage({ headers: req.headers, socket: req.socket });
    }
    return original.call(this, event, ...args);
  } as typeof proto.emit;
  proto.__empireStamped = true;
}
