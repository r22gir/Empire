import assert from 'node:assert/strict';
import test from 'node:test';
import {
  applyTailscaleHeaderPolicy,
  isLoopbackPeer,
  stampIncomingMessage,
} from './tailscaleProxy.ts';

test('ipv4-mapped loopback counts as loopback', () => {
  assert.equal(isLoopbackPeer('::ffff:127.0.0.1'), true);
  assert.equal(isLoopbackPeer('::1'), true);
  assert.equal(isLoopbackPeer('100.110.233.75'), false);
});

test('loopback serve keeps the login and stamps the hop', () => {
  const previous = process.env.EMPIRE_PROXY_AUTH_SECRET;
  process.env.EMPIRE_PROXY_AUTH_SECRET = 'hop-secret';
  const req = {
    socket: { remoteAddress: '::ffff:127.0.0.1' },
    headers: {
      'tailscale-user-login': 'founder@example.com',
      'x-empire-proxy-secret': 'spoofed',
      'x-empire-tailscale-verified': '1',
    } as Record<string, string>,
  };
  stampIncomingMessage(req);
  assert.equal(req.headers['x-empire-socket-peer'], '127.0.0.1');
  assert.equal(req.headers['x-empire-proxy-secret'], 'hop-secret');
  assert.equal(req.headers['x-empire-tailscale-verified'], '1');
  assert.equal(req.headers['tailscale-user-login'], 'founder@example.com');
  process.env.EMPIRE_PROXY_AUTH_SECRET = previous;
});

test('a LAN peer cannot inject Tailscale identity', () => {
  const previous = process.env.EMPIRE_PROXY_AUTH_SECRET;
  process.env.EMPIRE_PROXY_AUTH_SECRET = 'hop-secret';
  const req = {
    socket: { remoteAddress: '192.168.1.20' },
    headers: {
      'tailscale-user-login': 'founder@example.com',
      'tailscale-user-name': 'Founder',
      'x-empire-proxy-secret': 'spoofed',
      'x-empire-tailscale-verified': '1',
    } as Record<string, string>,
  };
  stampIncomingMessage(req);
  assert.equal(req.headers['x-empire-socket-peer'], '192.168.1.20');
  assert.equal(req.headers['x-empire-proxy-secret'], 'hop-secret');
  assert.equal(req.headers['tailscale-user-login'], undefined);
  assert.equal(req.headers['tailscale-user-name'], undefined);
  assert.equal(req.headers['x-empire-tailscale-verified'], undefined);

  const headers = new Headers({
    'x-empire-socket-peer': '192.168.1.20',
    'tailscale-user-login': 'founder@example.com',
    'x-empire-tailscale-verified': '1',
    'x-empire-proxy-secret': 'hop-secret',
  });
  const next = applyTailscaleHeaderPolicy(headers);
  assert.equal(next.get('tailscale-user-login'), null);
  assert.equal(next.get('x-empire-tailscale-verified'), null);
  assert.equal(next.get('x-empire-proxy-secret'), 'hop-secret');
  process.env.EMPIRE_PROXY_AUTH_SECRET = previous;
});
