# Empire Design System
**Extracted:** 2026-03-20 during ecosystem audit

---

## Color Palette

### Core Colors (Command Center)
| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#f5f2ed` | Page background, warm off-white |
| `--panel` | `#fff` | Panel/card backgrounds |
| `--hover` | `#f8f6f2` | Hover states |
| `--chat-bg` | `#f5f2ed` | Chat area background |
| `--card-bg` | `#faf9f7` | Card backgrounds |
| `--border` | `#ece8e0` | Default borders |
| `--border-h` | `#d5d0c8` | Hover borders |
| `--text` | `#1a1a1a` | Primary text |
| `--text-secondary` | `#555` | Secondary text |
| `--dim` | `#777` | Dimmed text |
| `--muted` | `#999` | Muted text |
| `--faint` | `#c5c0b8` | Faintest text/borders |

### Accent Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--gold` | `#b8960c` | Primary accent (brand gold) |
| `--gold-light` | `#fdf8eb` | Gold background tint |
| `--gold-border` | `#d4b84a` | Gold border |
| `--green` | `#22c55e` | Success states |
| `--blue` | `#2563eb` | Info/links |
| `--red` | `#dc2626` | Error/danger |
| `--orange` | `#f59e0b` | Warning |
| `--purple` | `#7c3aed` | Special/premium |

### AMP Colors (Standalone App)
| Token | Value | Usage |
|-------|-------|-------|
| Gold | `#D4A030` | Primary accent |
| Sunrise | warm orange | CTA buttons, gradients |
| Sage | muted green | Success, wellness |
| Lavender | soft purple | Calm, meditation |
| Warmwhite | `#F8F6F1` (approx) | Background |
| Cream | slightly darker | Section backgrounds |

## Typography

### Command Center
- **Primary:** Inter (weights: 300, 400, 500, 600, 700)
- **Fallback:** -apple-system, BlinkMacSystemFont, sans-serif
- Loaded from Google Fonts in `globals.css`

### AMP
- **Serif:** Custom serif font for headings (warm, editorial feel)
- **Body:** System fonts

### Founder Dashboard (Legacy)
- **UI:** Outfit
- **Code:** JetBrains Mono

## Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| `--radius` | `14px` | Standard cards |
| `--radius-sm` | `10px` | Smaller elements |
| `--radius-lg` | `16px` | Large cards/modals |

## Component Patterns

### Cards (`.empire-card`)
- Background: `var(--card-bg)`
- Border: `1px solid var(--border)`
- Radius: `var(--radius)` (14px)
- Padding: `14px 16px`
- Hover: border darkens, subtle shadow, `-1px` translateY
- Active: gold background tint, gold border
- `.flat` variant: no hover effects

### Status Pills (`.status-pill`)
- Padding: `4px 10px`
- Radius: `8px`
- Font: `11px`, weight 600
- Variants: `.open` (gold), plus green/blue/red

### Icons
- Library: `lucide-react` (used consistently across ALL apps)
- Sizes: 14-20px typical

## Responsive Breakpoints
- Mobile: < 768px (`md:` prefix in Tailwind)
- LeftNav collapses to hamburger on mobile
- RightPanel and BottomBar hidden on mobile (`hidden md:block`)

## Cross-App Consistency Status
| App | Design System | Consistent? |
|-----|--------------|-------------|
| Command Center | Custom CSS vars + Tailwind | Reference implementation |
| AMP | Custom Tailwind config (gold/sage/sunrise) | Different palette, AMP-specific |
| LuxeForge Intake | Matches CC style | Yes |
| WorkroomForge | Older design | Partially |
| Founder Dashboard | Different (dark theme, Outfit/JetBrains) | No — legacy |
| Empire App | Mixed | Partially |

**Recommendation:** The Command Center is the canonical design. All future UX work should align to CC's warm white/gold palette and Inter font.
