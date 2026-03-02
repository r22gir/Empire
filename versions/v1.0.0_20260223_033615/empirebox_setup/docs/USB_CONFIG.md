# EmpireBox USB Configuration Guide

Zero-touch deployment using a USB drive containing `empirebox-config.json`.

## How It Works

1. Create `empirebox-config.json` with your settings.
2. Copy it to the **root** of a USB drive (FAT32 or exFAT).
3. Plug the USB into any port on your EmpireBox.
4. The device detects the file within 30 seconds and starts setup automatically.

## Configuration File Format

```json
{
  "licenseKey": "EMPIRE-XXXX-XXXX-XXXX-XXXX",
  "accountEmail": "you@example.com",
  "accountToken": "optional-jwt-from-portal",
  "wifi": {
    "ssid": "YourNetwork",
    "password": "YourPassword"
  },
  "selectedProducts": [
    "marketforge",
    "shipforge",
    "forgecrm"
  ],
  "ollamaModels": [
    "llama3.1:8b",
    "codellama:7b",
    "nomic-embed-text"
  ],
  "enableCrypto": false,
  "timezone": "America/New_York"
}
```

## Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `licenseKey` | ✅ | Format: `EMPIRE-XXXX-XXXX-XXXX-XXXX` |
| `accountEmail` | ✅ | Your EmpireBox account email |
| `accountToken` | ❌ | JWT from `setup.empirebox.com` (skips login step) |
| `wifi.ssid` | ❌ | WiFi network name |
| `wifi.password` | ❌ | WiFi password |
| `selectedProducts` | ✅ | At least one product ID |
| `ollamaModels` | ❌ | Ollama models to download |
| `enableCrypto` | ❌ | Enable crypto payments (default: false) |
| `timezone` | ❌ | System timezone (default: America/New_York) |

## Available Products

| ID | Name | Size |
|----|------|------|
| `marketforge` | MarketForge | 850MB |
| `supportforge` | SupportForge | 420MB |
| `contractorforge` | ContractorForge | 680MB |
| `luxeforge` | LuxeForge | 520MB |
| `leadforge` | LeadForge | 380MB |
| `shipforge` | ShipForge | 290MB |
| `forgecrm` | ForgeCRM | 450MB |
| `relistapp` | RelistApp | 180MB |
| `socialforge` | SocialForge | 340MB |
| `llcfactory` | LLCFactory | 220MB |
| `apostapp` | ApostApp | 190MB |
| `empireassist` | EmpireAssist | 310MB |

## Available AI Models

| ID | Size | Notes |
|----|------|-------|
| `llama3.1:8b` | 4.7GB | Recommended |
| `llama3.1:70b` | 40GB | Needs 64GB+ RAM |
| `codellama:7b` | 3.8GB | Recommended for dev |
| `mistral:7b` | 4.1GB | Fast |
| `nomic-embed-text` | 274MB | Recommended for RAG |

## Security Notes

- The config file may contain your WiFi password. Delete it from the USB after setup.
- The `accountToken` field is sensitive — treat it like a password.
- Config files are copied to `/var/lib/empirebox/` and then the original USB can be removed.
