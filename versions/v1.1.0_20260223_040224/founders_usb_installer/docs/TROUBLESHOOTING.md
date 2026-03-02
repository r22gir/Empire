# Troubleshooting Guide

## Common Issues

### Installation Failed / Stuck

```bash
# Check install log
tail -100 /var/log/empirebox-install.log

# Re-run install manually
sudo /opt/empirebox/install-founders.sh
```

### Service Won't Start

```bash
# Check all container status
docker ps -a

# View specific service logs
docker logs empirebox-postgres
docker logs empirebox-openclaw
docker logs empirebox-control

# Restart core services
cd /opt/empirebox
docker compose down
docker compose up -d
```

### Product Won't Start

```bash
# Check product status
ebox list

# View product logs
ebox logs marketforge

# Restart a product
ebox restart marketforge

# Check if port is in use
ss -tlnp | grep 8010
```

### Can't Access Dashboard

```bash
# Check nginx container
docker logs empirebox-dashboard

# Check if port 80 is listening
ss -tlnp | grep ':80'

# Restart dashboard
docker restart empirebox-dashboard
```

### Ollama Not Working

```bash
# Check Ollama service
systemctl status ollama

# List available models
ollama list

# Re-pull a model
ollama pull llama3.1:8b

# Check Ollama API
curl http://localhost:11434/api/tags
```

### OpenClaw Not Responding

```bash
# Check OpenClaw container
docker logs empirebox-openclaw

# Restart OpenClaw
docker restart empirebox-openclaw

# Verify config
cat /opt/empirebox/openclaw/config.yaml
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker logs empirebox-postgres
docker exec empirebox-postgres pg_isready -U empirebox

# Check Redis
docker exec empirebox-redis redis-cli -a $REDIS_PASSWORD ping

# Verify .env has correct passwords
cat /opt/empirebox/.env | grep POSTGRES
```

### Firewall Blocking Access

```bash
# Check UFW status
sudo ufw status verbose

# Allow a port manually
sudo ufw allow 8010/tcp

# Temporarily disable (NOT for production)
sudo ufw disable
```

### ebox Command Not Found

```bash
# Reinstall ebox CLI
sudo cp /opt/empirebox/scripts/ebox /usr/local/bin/ebox
sudo chmod +x /usr/local/bin/ebox

# Verify
which ebox
ebox list
```

## How to Check Logs

```bash
# Installation log
tail -f /var/log/empirebox-install.log

# Core service logs
docker compose -f /opt/empirebox/docker-compose.yml logs -f

# Specific product logs
ebox logs <product>

# System journal
journalctl -u empirebox-install -f
journalctl -u ollama -f

# All Docker logs
docker ps --format "{{.Names}}" | xargs -I{} sh -c 'echo "=== {} ===" && docker logs {} --tail=20'
```

## How to Reset / Reinstall

### Soft Reset (keep data)
```bash
cd /opt/empirebox
docker compose down
docker compose up -d
```

### Full Reset (wipe everything)
```bash
# Stop all services
cd /opt/empirebox && docker compose down
ebox stop-all

# Remove containers and volumes
docker system prune -af --volumes

# Re-run install
sudo /opt/empirebox/install-founders.sh
```

### Reinstall from USB
1. Boot from USB again
2. When Ubuntu asks about existing installation: choose "Erase and reinstall"
3. The autoinstall will run automatically

## Getting System Info

```bash
# Hardware info
lscpu
free -h
df -h

# Network
hostname -I
ip addr show

# Docker
docker info
docker stats --no-stream

# Installed models
ollama list
```

## Support

For issues not covered here:
1. Check `/var/log/empirebox-install.log`
2. Check `docker logs <container-name>`
3. Review `docs/ARCHITECTURE.md` for system overview
4. Contact: EmpireBox internal team
