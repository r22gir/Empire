# EmpireBox Security Guide

## Founders Unit vs Customer Units

### Founders Unit (This Device)
- **Full access** — no guardrails, no sandbox
- **OpenClaw mode**: `founders` — can execute any system command
- **No phone-home** — not monitored by Control Center
- **Purpose**: Internal management, product development, fleet control

### Customer Units
- **Sandboxed** — restricted command execution
- **Phone-home**: POST to `/heartbeat` every 5 minutes
- **License validation** required on startup
- **Remote control**: Can be suspended or revoked from Control Center
- **OpenClaw mode**: `customer` — limited to product-specific skills only

## Credential Storage

All credentials are in `/opt/empirebox/.env`:
```
chmod 600 /opt/empirebox/.env
# Owner: root only
```

### What's in .env
- `POSTGRES_PASSWORD` — PostgreSQL database password
- `REDIS_PASSWORD` — Redis auth password
- `JWT_SECRET` — JWT signing secret for API auth
- `CONTROL_API_KEY` — Control Center API authentication
- `OPENCLAW_SECRET` — OpenClaw admin secret

All passwords are generated with `openssl rand -hex 32` (256-bit entropy).

## Firewall Configuration

UFW rules applied during installation:

| Port | Service | Rule |
|------|---------|------|
| 22 | SSH | ALLOW |
| 80 | Dashboard | ALLOW |
| 443 | HTTPS | ALLOW |
| 7878 | OpenClaw | ALLOW |
| 8000 | API Gateway | ALLOW |
| 8001 | Control Center | ALLOW |
| 8010-8130 | Products | ALLOW |
| 9000 | Portainer | ALLOW |
| 11434 | Ollama | ALLOW |
| 5432 | PostgreSQL | DENY (internal only) |
| 6379 | Redis | DENY (internal only) |

Note: PostgreSQL and Redis are only accessible within the `empirebox` Docker network, not exposed externally.

## Phone-Home System (Customer Units)

Customer units send a heartbeat every 5 minutes:
```http
POST /heartbeat
{
  "unit_id": "UNIT-ABC123",
  "license_key": "EMP-XXXXXXXX-YYYYYYYY",
  "hostname": "customer-unit-1",
  "ip": "192.168.1.100",
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

Response tells the unit whether to continue or stop:
```json
{
  "status": "active",
  "action": "continue",
  "timestamp": "2026-01-01T00:00:00"
}
```

If `action` is `"stop"`, the customer unit shuts down all products.

## Recommendations

1. **Change SSH password** after first login:
   ```bash
   passwd empirebox
   ```

2. **Rotate credentials** periodically:
   ```bash
   # Edit /opt/empirebox/.env with new passwords
   # Restart services: docker compose restart
   ```

3. **Keep Portainer behind firewall** — don't expose port 9000 to the internet.

4. **Use HTTPS** for production deployments — add nginx SSL termination.

5. **Backup .env securely** — store a copy in a password manager.
