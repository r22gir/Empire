# Network Topology

## Standard EmpireBox Network Setup

```
                    ┌─────────────────┐
                    │  ISP Modem/Router│
                    │  192.168.1.1     │
                    └────────┬────────┘
                             │ Gigabit Ethernet
                    ┌────────▼────────┐
                    │ Gigabit Switch  │
                    │ (8-port)        │
                    └──┬──┬──┬──┬────┘
                       │  │  │  │
          ─────────────┘  │  │  └──────────────
          │                │  │                │
 ┌────────▼──────┐  ┌──────▼──┐  ┌────────────▼──┐
 │ EmpireBox PC  │  │ Label   │  │ Wi-Fi AP       │
 │ 192.168.1.100 │  │ Printer │  │ (optional)     │
 │               │  │         │  └───────┬────────┘
 │ Ports:        │  └─────────┘          │
 │  :8000 Backend│               ┌───────▼────────┐
 │  :7878 OpenClaw              │ Mobile Devices  │
 │  :5432 Postgres│              │ (tablets, phones)
 │  :6379 Redis  │               └────────────────┘
 └───────────────┘
```

## Port Reference

| Port | Service | Protocol |
|------|---------|----------|
| 8000 | EmpireBox Backend API | HTTP |
| 7878 | OpenClaw AI Assistant | HTTP |
| 5432 | PostgreSQL | TCP |
| 6379 | Redis | TCP |
| 11434 | Ollama (local AI) | HTTP |
| 80 | Nginx reverse proxy (HTTP) | HTTP |
| 443 | Nginx reverse proxy (HTTPS) | HTTPS |

## Recommended Static IP Assignment

| Device | IP Address |
|--------|-----------|
| Router | 192.168.1.1 |
| EmpireBox PC | 192.168.1.100 |
| Label Printer | 192.168.1.101 |
| Network Switch | 192.168.1.102 (managed) |

## DNS (Optional)

For internal hostname resolution, add to `/etc/hosts` on client machines:

```
192.168.1.100  empirebox.local
192.168.1.100  openclaw.local
```

Or configure a local DNS resolver (Pi-hole, dnsmasq) to resolve `*.local` to 192.168.1.100.
