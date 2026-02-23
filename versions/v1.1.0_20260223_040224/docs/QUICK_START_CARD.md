# Quick Start Card Design Specifications

## Overview

The Quick Start Card is included in every EmpireBox hardware bundle. It guides the customer through setup using a QR code that links to the web portal.

## Physical Specifications

### Card Dimensions
- **Size**: 3.5" x 2" (standard business card size)
- **Material**: 14pt cardstock with UV gloss coating
- **Orientation**: Landscape (horizontal)
- **Corners**: Rounded (3mm radius)

### Print Quality
- **Color**: Full CMYK, 300 DPI
- **Finish**: UV gloss on front, matte on back
- **Coating**: Scratch-resistant

---

## Design Layout

### Front Side

```
┌─────────────────────────────────────────────────────┐
│                                                      │
│  📱 EmpireBox                                        │
│  Your Reselling Empire Starts Here                  │
│                                                      │
│          ┌───────────────┐                           │
│          │               │                           │
│          │   [QR CODE]   │                           │
│          │               │                           │
│          │               │                           │
│          └───────────────┘                           │
│                                                      │
│     Scan to activate your subscription              │
│                                                      │
│  License: EMPIRE-XXXX-XXXX-XXXX                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Color Scheme:**
- Background: Gradient from #1E40AF (Empire Blue) to #60A5FA (Light Blue)
- Text: White (#FFFFFF)
- QR Code: White code on dark background for high contrast
- License Key: Bold, monospace font

**Logo:**
- EmpireBox logo in top left
- Icon: 📱 emoji or custom icon

**QR Code:**
- **Size**: 1.5" x 1.5" (centered)
- **Format**: QR Code Version 3 (29x29 modules)
- **Error Correction**: High (30% - allows for some damage/wear)
- **Content**: `https://empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX`
- **Style**: White modules on blue/dark background

**License Key:**
- **Font**: Roboto Mono, Bold, 10pt
- **Position**: Bottom center
- **Format**: EMPIRE-XXXX-XXXX-XXXX
- Each card has unique key

### Back Side

```
┌─────────────────────────────────────────────────────┐
│                                                      │
│  GETTING STARTED                                     │
│                                                      │
│  1️⃣ Scan the QR code with your phone                │
│                                                      │
│  2️⃣ Download MarketForge app                         │
│                                                      │
│  3️⃣ Create your secure wallet (Seeker only)         │
│                                                      │
│  4️⃣ Activate your subscription                       │
│                                                      │
│  5️⃣ Start selling!                                   │
│                                                      │
│  ────────────────────────────────────────────────   │
│                                                      │
│  Need help? support@empirebox.store                 │
│  📞 1-800-EMPIRE-BOX                                 │
│                                                      │
│  🌐 empirebox.store/help                             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Color Scheme:**
- Background: White with subtle texture/pattern
- Text: Dark gray (#333333)
- Icons: Empire Orange (#F97316)
- Divider: Light gray (#E5E7EB)

**Layout:**
- Steps listed with emoji numbers
- Large, readable font (11pt)
- Contact information at bottom

---

## Print-Ready Files

### File Format
- **Primary**: PDF (PDF/X-1a:2001 standard)
- **Alternative**: AI (Adobe Illustrator) or EPS
- **Backup**: High-res PNG (300 DPI)

### Color Profile
- **Color Space**: CMYK
- **Profile**: US Web Coated (SWOP) v2

### Bleed & Safe Area
- **Bleed**: 0.125" (3mm) on all sides
- **Safe Area**: 0.25" (6mm) margin from trim edge
- **Final Size**: 3.75" x 2.25" (with bleed)
- **Trim Size**: 3.5" x 2"

---

## Production Specifications

### Printing Options

#### Option 1: VistaPrint (Recommended for small batches)
- **Product**: Premium Business Cards
- **Quantity Pricing**:
  - 100 cards: $49.99 ($0.50 each)
  - 500 cards: $89.99 ($0.18 each)
  - 1,000 cards: $119.99 ($0.12 each)
- **Turnaround**: 3-5 business days
- **Shipping**: 3-5 business days
- **Order URL**: vistaprint.com/business-cards

#### Option 2: PrintPlace (Best for large batches)
- **Product**: Custom Business Cards, 14pt UV Gloss
- **Quantity Pricing**:
  - 1,000 cards: $150 ($0.15 each)
  - 5,000 cards: $450 ($0.09 each)
  - 10,000 cards: $750 ($0.075 each)
- **Turnaround**: 5-7 business days
- **Shipping**: 2-3 business days
- **Order URL**: printplace.com

#### Option 3: Local Print Shop
- For urgent needs or custom materials
- Get quote from 3 local printers
- Typically 20-30% more expensive but faster

### Quality Control
- **Proofing**: Request physical proof for first batch
- **Color Matching**: Compare to digital mockup
- **QR Code Testing**: Scan test cards before approving full run
- **License Key Verification**: Ensure all keys are unique

---

## QR Code Generation

### Technical Details
- **Encoding**: URL
- **Format**: PNG or SVG (vector preferred)
- **Quiet Zone**: 4 modules minimum around code
- **Size**: Minimum 1" x 1" for reliable scanning

### Generation Process

#### Using Python (Recommended)
```python
import qrcode

def generate_qr_for_license(license_key):
    url = f"https://empirebox.store/setup/{license_key}"
    
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="white", back_color="#1E40AF")
    img.save(f"qr_cards/qr_{license_key}.png")

# Generate for all licenses
for license in license_keys:
    generate_qr_for_license(license)
```

#### Using Online Tool
1. Go to qr-code-generator.com
2. Select "URL" type
3. Enter: `https://empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX`
4. Set error correction to "High"
5. Download as PNG or SVG

#### Testing QR Codes
- Scan with iPhone camera app
- Scan with Android camera app
- Test from different distances (6" to 24")
- Verify URL opens correctly

---

## Variable Data Printing (VDP)

Since each card needs a unique license key and QR code, use Variable Data Printing:

### Setup Process
1. **Generate CSV** with license keys and QR code filenames:
```csv
license_key,qr_code_file
EMPIRE-A3F2-9K4L-B7J8,qr_EMPIRE-A3F2-9K4L-B7J8.png
EMPIRE-C5H1-2M9N-D4P6,qr_EMPIRE-C5H1-2M9N-D4P6.png
...
```

2. **Create Template** in Adobe InDesign or Illustrator:
- Design layout with placeholder for QR code
- Add placeholder text for license key
- Link to CSV data source

3. **Generate Print Files**:
- Export as individual PDFs or multi-page PDF
- Each page contains one unique card design
- VistaPrint and PrintPlace both support VDP

### Alternative: Mail Merge
- Use mail merge in Word or Pages
- Import card design as background
- Merge license keys from spreadsheet
- Export as PDF for printing

---

## Packaging & Insertion

### In-Box Placement
- **Location**: Top of box, visible when opened
- **Protection**: Clear plastic sleeve or envelope
- **Attachment**: None (loose card)

### Budget Bundle
- Card placed on top of phone box
- No additional packaging needed

### Seeker Pro & Empire Bundles
- Card in premium envelope with EmpireBox logo
- Envelope attached to top of foam insert
- "Open First" label on envelope

---

## Design Templates

### Figma Template
- **URL**: figma.com/community (search "business card template")
- Customize with EmpireBox brand colors
- Export as PDF for printing

### Canva Template
- **URL**: canva.com/business-cards
- Use "Custom Size" (3.5" x 2")
- Import QR codes as images
- Download as PDF (print quality)

### Adobe Illustrator
- Create new document: 3.5" x 2"
- Add 0.125" bleed
- Design with CMYK colors
- Save as PDF/X-1a

---

## Checklist for Production

### Pre-Print
- [ ] All license keys generated and unique
- [ ] QR codes generated and tested
- [ ] Design approved by team
- [ ] Colors match brand guide
- [ ] Print files in correct format (PDF/X-1a)
- [ ] Bleed and safe areas correct
- [ ] Fonts embedded or outlined
- [ ] Quantity determined

### Proof Review
- [ ] Request physical proof from printer
- [ ] Check color accuracy
- [ ] Scan QR code to verify functionality
- [ ] Verify license key legibility
- [ ] Check for typos in text
- [ ] Confirm material and finish

### Post-Print
- [ ] Inspect sample cards from batch
- [ ] Scan multiple QR codes to verify batch quality
- [ ] Check for print defects (smudging, misalignment)
- [ ] Sort and organize by bundle type
- [ ] Store in cool, dry place

---

## Costs

### Per-Card Cost Breakdown
- **Printing**: $0.12 (at 1,000 qty)
- **Envelope (premium bundles)**: $0.10
- **Labor (insertion)**: $0.05
- **Total per card**: $0.15 - $0.27

### Batch Costs
- 100 cards: $50
- 500 cards: $90
- 1,000 cards: $150
- 5,000 cards: $750

---

## Example Card Mockup

### Front
```
════════════════════════════════════════════════════════
║                                                        ║
║   📱 EmpireBox                                         ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━             ║
║   Your Reselling Empire Starts Here                   ║
║                                                        ║
║                    ███████████████                     ║
║                    ███░░░░░░░░███                     ║
║                    ███░░███░░░███                     ║
║                    ███░░░░░░░░███                     ║
║                    ███████████████                     ║
║                                                        ║
║           👆 Scan to Get Started                       ║
║                                                        ║
║   License: EMPIRE-A3F2-9K4L-B7J8                      ║
║                                                        ║
════════════════════════════════════════════════════════
```

---

*Document Version: 1.0*
*Last Updated: 2026-02-17*
*Owner: EmpireBox Product Team*
