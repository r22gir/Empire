# EmpireBox Hardware Specification

## Core Devices

### 📱 Solana Seeker Phone
- **Purpose**: All-in-one mobile business device
- **Scanner**: Built-in camera (NO additional hardware needed)
- **Features**:
  - Barcode/QR scanning via camera + ML
  - Photo measurements for ContractorForge
  - EmpireAssist (Telegram/WhatsApp)
  - Full EmpireBox access
- **Modes**:
  - Standalone: Basic features work without connection
  - Connected: Link to EmpireBox for full potential

### 📲 Empire Tablet
- **Purpose**: Larger screen for detailed work
- **Scanner**: Built-in camera (same as phone)
- **Best For**:
  - Inventory management (larger view)
  - ContractorForge photo measurements
  - Trade shows and client meetings
  - Detailed project work

### 🖥️ Mini PC
- **Purpose**: Desktop power user experience
- **Features**:
  - Local AI processing (Ollama/OpenClaw)
  - Multi-monitor support
  - Heavy processing tasks

## Scanning Workflow (No Extra Hardware!)

```
1. Open EmpireAssist or MarketForge app
2. Tap "Scan Item" button
3. Point phone/tablet camera at:
   - Barcode → Auto-lookup product info
   - QR Code → Auto-fill listing details
   - Product (no barcode) → AI image recognition
4. App populates listing automatically
5. User confirms → Listed instantly
```

## Technical Implementation
- iOS: AVFoundation barcode scanning
- Android: ML Kit / ZXing barcode library
- AI Fallback: OpenClaw image recognition for non-barcoded items

## Key Message
**"Your phone IS the scanner. No extra hardware needed. 
Pull out your device, scan, and list in seconds."**