# Storage Recommendations

## Internal SSD

EmpireBox requires fast storage for Docker images, databases, and AI models.

| Use Case | Minimum | Recommended |
|----------|---------|-------------|
| Core stack (no AI) | 128 GB | 256 GB |
| Full stack + Ollama | 256 GB | 512 GB |
| Enterprise (13B models) | 512 GB | 1 TB+ |

### Recommended Internal NVMe SSDs

| Model | Capacity | Speed (Read/Write) | Price |
|-------|----------|--------------------|-------|
| Samsung 980 | 500 GB | 3,500/3,000 MB/s | ~$55 |
| WD Blue SN570 | 1 TB | 3,500/3,000 MB/s | ~$65 |
| Crucial P3 Plus | 2 TB | 5,000/4,200 MB/s | ~$99 |

## External SSD (Backups & Data)

| Model | Capacity | Interface | Price |
|-------|----------|-----------|-------|
| Samsung T7 | 500 GB | USB 3.2 Gen 2 | ~$60 |
| Samsung T7 | 1 TB | USB 3.2 Gen 2 | ~$90 |
| Samsung T7 Shield | 2 TB | USB 3.2 Gen 2 | ~$169 |
| WD My Passport | 2 TB | USB 3.0 | ~$75 |

## Tips

- Use the internal NVMe for Docker volumes and databases.
- Use the external SSD for nightly backups (`backup/` directory).
- Avoid SD cards or USB thumb drives for persistent storage.
- Enable TRIM on SSDs: `sudo systemctl enable fstrim.timer`
