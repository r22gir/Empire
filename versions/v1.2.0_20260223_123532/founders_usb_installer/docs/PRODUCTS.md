# EmpireBox Products

## Overview

The EmpireBox Founders Unit ships with 13 products, all running as independent Docker Compose stacks. Products are started on-demand using the `ebox` CLI.

## Products

### 🛒 MarketForge — Port 8010
AI-powered marketplace listing creation and optimization. Generate optimized listings for eBay, Amazon, Facebook Marketplace, and more.
```bash
ebox start marketforge
# Access: http://empirebox.local:8010
```

### 🏗️ ContractorForge — Port 8020
Universal SaaS platform for service businesses. AI intake forms, photo-based measurements, smart quoting.
```bash
ebox start contractorforge
# Access: http://empirebox.local:8020
```

### ✨ LuxeForge — Port 8030
Premium service business platform with luxury market positioning. Tailored for high-end contractors and service providers.
```bash
ebox start luxeforge
# Access: http://empirebox.local:8030
```

### 💬 SupportForge — Port 8040
AI-powered customer support and ticketing system. Multi-channel support with automated responses.
```bash
ebox start supportforge
# Access: http://empirebox.local:8040
```

### 🎯 LeadForge — Port 8050
Lead generation and nurturing automation. Capture, score, and convert leads across channels.
```bash
ebox start leadforge
# Access: http://empirebox.local:8050
```

### 📦 ShipForge — Port 8060
Integrated shipping with EasyPost. Compare rates across carriers, buy labels, print from phone.
```bash
ebox start shipforge
# Access: http://empirebox.local:8060
```

### 📋 ForgeCRM — Port 8070
CRM system for managing customers across all EmpireBox products. Unified customer view.
```bash
ebox start forgecrm
# Access: http://empirebox.local:8070
```

### 🔁 RelistApp — Port 8080
Cross-platform relisting tool. List once, sell everywhere across multiple marketplaces.
```bash
ebox start relistapp
# Access: http://empirebox.local:8080
```

### 📱 SocialForge — Port 8090
Social media management and automated posting. Schedule content across all platforms.
```bash
ebox start socialforge
# Access: http://empirebox.local:8090
```

### 🏢 LLCFactory — Port 8100
Automated LLC formation and business registration. State-by-state filing automation.
```bash
ebox start llcfactory
# Access: http://empirebox.local:8100
```

### 📜 ApostApp — Port 8110
Apostille and document legalization service platform. International document certification.
```bash
ebox start apostapp
# Access: http://empirebox.local:8110
```

### 🤝 EmpireAssist — Port 8120
Telegram/WhatsApp messenger integration for business management. Manage your business via chat from anywhere.
```bash
ebox start empireassist
# Access: http://empirebox.local:8120
```

### 💳 EmpirePay — Port 8130
Payment processing and invoicing with multi-gateway support. Stripe, PayPal, crypto.
```bash
ebox start empirepay
# Access: http://empirebox.local:8130
```

## Bundles

Start multiple related products at once:

### Reseller Bundle
Best for online resellers and marketplace sellers.
```bash
ebox bundle reseller
# Starts: marketforge, shipforge, relistapp, forgecrm
```

### Contractor Bundle
Best for service businesses and contractors.
```bash
ebox bundle contractor
# Starts: contractorforge, luxeforge, leadforge, forgecrm
```

### Support Bundle
Best for support-focused operations.
```bash
ebox bundle support
# Starts: supportforge, forgecrm, empireassist
```

### Full Suite
All 13 products.
```bash
ebox bundle full
```

## Managing Products

```bash
ebox list           # List all products with ports and status
ebox status         # Show only running products
ebox start <name>   # Start a specific product
ebox stop <name>    # Stop a specific product
ebox restart <name> # Restart a product
ebox logs <name>    # Tail product logs
ebox stop-all       # Stop all running products
```
