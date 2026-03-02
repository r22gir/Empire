# Enterprise Build (~$1,299)

Full EmpireBox stack with local AI and high availability.

## Specifications

| Item | Detail |
|------|--------|
| **CPU** | Intel Core i7-1360P (12-core, 5.0 GHz Turbo) |
| **RAM** | 32 GB DDR4 |
| **Storage** | 1 TB NVMe SSD (internal) |
| **External Storage** | Samsung T7 Shield 2 TB USB 3.2 |
| **OS** | Ubuntu 24.04 LTS |
| **Network** | 2.5 GbE Ethernet + Wi-Fi 6E |
| **Power** | 28 W TDP (configurable up to 64 W) |

## Supported Forge Products

All Forge products plus full local AI:

- ✅ All Forge products (full stack)
- ✅ OpenClaw with Ollama (13B models)
- ✅ Agent Framework (all agents)
- ✅ Local Whisper STT
- ✅ Concurrent agent workflows

## Recommended Mini PCs

| Model | Price | Link |
|-------|-------|------|
| Intel NUC 13 Pro (i7-1360P) | ~$799 | [Amazon](https://www.amazon.com) |
| ASUS NUC 13 Pro | ~$749 | [Amazon](https://www.amazon.com) |
| Beelink GTR7 Pro | ~$599 | [Amazon](https://www.amazon.com) |

## High Availability Notes

- Use a UPS with ≥1500 VA to handle power fluctuations.
- Configure automatic Docker container restart (`restart: unless-stopped`).
- Set up nightly backups to an external SSD or cloud storage.
- Monitor with Prometheus + Grafana (optional; see `docs/monitoring.md`).
