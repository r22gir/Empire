# MAX Response Canvas — Technical Specification v2
## Empire Box Founders Interface

**Version:** 2.0
**Date:** February 27, 2026
**Status:** Spec Ready for Implementation
**Updated:** Added Media/Embed Mode, Comms Mode, Live Workspace Mode — reframed canvas as MAX's multipurpose command screen

---

## 1. Overview

The Max Response Canvas is MAX's screen — a multipurpose command display that MAX controls to show the founder whatever is relevant in the moment. It replaces traditional chat bubbles with a rich, visual presentation layer. The left column of the Command Center IS Max's monitor. He uses it to play videos, make calls, display documents, render charts, browse the web, show mockups, stream content, and present information — adapting in real time based on context.

**Core Principle:** The canvas is MAX's screen. He shows you his world.

**Not just a response display — a living, multipurpose command surface.**

---

## 2. Canvas Modes

The canvas auto-selects mode based on response content analysis. Multiple modes can combine in a single response. The founder can also manually switch modes or request specific content.

### 2.1 Avatar Mode (Default/Conversational)
- Animated Max avatar center-screen
- Text appears below/beside avatar as Max "speaks"
- Typing animation synced with streaming response
- Avatar reacts: thinking (eyes move), speaking (mouth animates), done (nods)
- Used for: greetings, simple answers, confirmations

### 2.2 Document Mode
- Renders documents (PDF, DOCX, spreadsheet previews) in the canvas
- **Spotlight/Zoom feature:** Max can highlight and zoom into specific sections
- Quote callout: pulls key text into a styled callout box with citation
- Side-by-side: avatar on left (small), document on right
- Used for: contract review, report summaries, invoice details

### 2.3 Chart/Data Mode
- Live chart rendering using Recharts/Chart.js
- Charts build progressively as Max explains the data
- Interactive: hover for values, click to drill down
- Multiple chart types: bar, line, pie, area, scatter, gauge
- Data table toggle: switch between chart and raw data view
- Used for: financial reports, sales pipeline, analytics, KPIs

### 2.4 Web Content Mode
- Displays web page previews, article summaries
- Image pulled from source with citation overlay
- Screenshot/preview card with source URL
- Key quote highlighted with source attribution
- Used for: research results, competitor analysis, news, product info

### 2.5 Image Mode
- AI-generated images that match the response context
- Web-sourced images with proper attribution
- Gallery view for multiple images
- Before/after comparison slider
- Used for: design concepts, inspiration boards, visual references

### 2.6 Split Canvas Mode
- Divides canvas into 2-4 sections
- Each section can be a different mode
- Example: avatar speaking (top-left) + chart (top-right) + key metrics (bottom)
- Used for: complex responses that need multiple visual elements

### 2.7 Presentation Mode
- Full-screen slides that Max narrates
- Auto-advancing or click-through
- Each slide is a canvas mode (chart, image, text, etc.)
- Progress indicator at bottom
- Used for: morning briefings, project updates, strategy presentations

### 2.8 Media/Embed Mode (NEW)
MAX's screen for playing any media or embedding any web content. This is the canvas acting as a smart TV / browser / video phone that MAX controls.

#### 2.8.1 Video Player
- **YouTube/Vimeo embed:** MAX finds relevant videos, plays inline
- **Direct video files:** MP4, WebM playback from local or URL
- **Controls:** Play/pause, seek, volume, fullscreen, playback speed
- **Picture-in-Picture (PiP):** Minimize video to corner while working in other panels
- **Playlist:** MAX can queue multiple videos
- **Timestamp linking:** MAX can jump to specific moments
- **Background audio:** Music/podcasts play while canvas shows other content

#### 2.8.2 Web Browser / iframe
- **Full web page embed:** Any URL rendered inside the canvas
- **Supplier websites:** MAX browses Kravet, Robert Allen for fabric lookups
- **Google Maps:** Show customer locations, job sites, driving directions
- **Documentation:** Show API docs, reference materials, tutorials
- **Social media:** Show Instagram, Facebook, X posts or profiles
- **Navigation controls:** Back, forward, refresh, open in external browser
- **MAX annotates:** Can highlight sections of the web page and comment on them

#### 2.8.3 Streaming / Live Content
- **Live YouTube streams:** News, music, events
- **Security cameras:** IP camera feeds from job sites or office (RTSP/HLS)
- **Screen share receive:** Someone shares their screen with you via the canvas
- **Dashboard feeds:** Embed external dashboards (analytics, monitoring)
- **Always-on option:** Pin a stream to a small PiP window permanently

#### 2.8.4 Media Controls (Universal)
```
Controls:
  Play/Pause, Skip/Seek, Progress bar, Volume
  Fullscreen, Pin to PiP, Open in browser, Close media
```

### 2.9 Comms Mode (NEW)
MAX handles communication directly on the canvas — calls, video chats, and messaging threads.

#### 2.9.1 Video/Voice Call
- WebRTC video calls, VoIP integration
- Call controls: Mute, camera on/off, screen share, end call
- During call: MAX can pull up documents, quotes, mockups on split canvas
- Call recording, post-call summary with action items

#### 2.9.2 Messaging Thread View
- Telegram thread, email chain, SMS history display
- MAX can draft responses inline
- Quick actions: Reply, forward, archive, add to CRM

#### 2.9.3 Multi-Comms (Split)
- Video call + customer file split view
- Call in PiP while browsing options
- Thread on left, quote builder on right

### 2.10 Live Workspace Mode (NEW)
The canvas becomes a live working surface.

#### 2.10.1 Code/Terminal View
- Live terminal output, code editor view, build logs, side-by-side code+preview

#### 2.10.2 Mockup Studio
- Canvas becomes mockup workspace with photo upload, segmentation, fabric rendering

#### 2.10.3 Quote Builder Live
- Real-time quote assembly on canvas with live PDF preview

#### 2.10.4 Calendar/Schedule View
- Full calendar embed, drag-and-drop, color-coded by type

---

## 3. Content Detection & Routing

```
Response Analysis Pipeline:
│
├── Contains data/numbers/metrics? → Chart Mode
├── References a document/file? → Document Mode
├── References a website/URL? → Web Content Mode or Media/Embed
│   ├── YouTube/Vimeo link → Media Mode (video player)
│   ├── Map/location → Media Mode (Google Maps embed)
│   └── General URL → Media Mode (iframe)
├── Video/media request? → Media/Embed Mode
├── Communication request? → Comms Mode
├── Active work request? → Live Workspace Mode
├── Describes something visual? → Image Mode
├── Multiple content types? → Split Canvas Mode
├── Structured briefing? → Presentation Mode
└── Simple conversation → Avatar Mode (default)
```

---

## 4. Progressive Rendering

1. **Stream starts:** Avatar appears, begins "speaking" animation
2. **Content detected:** Canvas mode transitions smoothly (fade/slide)
3. **Data arrives:** Charts/images/documents/media load progressively
4. **Stream ends:** Final state, interactive elements become active
5. **User can interact:** Click charts, zoom documents, expand images, control media

Key: The canvas NEVER waits for the full response. It builds as Max speaks.

---

## 5. Technical Architecture

### 5.1 Components

| Component | Purpose | Phase |
|-----------|---------|-------|
| `ResponseCanvas.tsx` | Main canvas orchestrator, mode switching | 1 |
| `AvatarDisplay.tsx` | Animated Max avatar with states | 1 |
| `ChartCanvas.tsx` | Dynamic chart rendering (Recharts) | 1 |
| `DocumentCanvas.tsx` | Document viewer with spotlight/zoom | 1 |
| `WebPreviewCanvas.tsx` | Web content cards with citations | 1 |
| `ImageCanvas.tsx` | Image display, gallery, comparison | 1 |
| `SplitCanvas.tsx` | Multi-panel layout manager | 1 |
| `PresentationCanvas.tsx` | Slide-based narrative mode | 2 |
| `MediaCanvas.tsx` | Video player, iframe embed, streaming | 2 |
| `CommsCanvas.tsx` | Video call, messaging threads, drafting | 3 |
| `WorkspaceCanvas.tsx` | Live workspace (code, mockup, quote, calendar) | 3 |
| `PiPOverlay.tsx` | Picture-in-picture floating window | 2 |
| `CanvasTransition.tsx` | Smooth mode transitions | 1 |
| `ContentAnalyzer.ts` | Real-time response analysis for mode selection | 1 |
| `MediaController.ts` | Universal media controls | 2 |
| `QuoteCallout.tsx` | Styled quote extraction with source | 1 |
| `MetricCard.tsx` | Big number / KPI display | 1 |
| `CanvasHistory.ts` | Remember and recall previous canvas states | 2 |

### 5.2 Data Flow

```
User Input → useChat → API (Grok/Claude) → Streaming Response
    → ContentAnalyzer (real-time) → ResponseCanvas (mode select + render)
    → Progressive UI: charts build, images load, text streams,
      video embeds, calls connect, workspaces hydrate, PiP overlays
```

---

## 6. Implementation Priority

### Phase 1 — Foundation
1. ResponseCanvas.tsx shell with mode switching
2. AvatarDisplay.tsx with basic states (SVG + CSS)
3. ChartCanvas.tsx with Recharts integration
4. ContentAnalyzer.ts for mode detection
5. Integration with existing useChat hook
6. DocumentCanvas.tsx with spotlight/zoom
7. WebPreviewCanvas.tsx with citations
8. ImageCanvas.tsx with gallery
9. SplitCanvas.tsx for multi-panel
10. Canvas action buttons

### Phase 2 — Media & Embed
11. MediaCanvas.tsx — YouTube embed, video player
12. iframe embedding for web content
13. PiPOverlay.tsx — picture-in-picture
14. MediaController.ts — universal controls
15. Canvas memory (recall previous visualizations and media)
16. PresentationCanvas.tsx (morning briefing)
17. Media library
18. Voice + canvas synchronization

### Phase 3 — Communication & Live Work
19. CommsCanvas.tsx — WebRTC video/voice calls
20. Messaging thread view
21. WorkspaceCanvas.tsx — live quote builder
22. Mockup Studio integration
23. Calendar/schedule view
24. Code/terminal view
25. Telegram canvas sync
26. Collaborative canvas sharing

### Phase 4 — Polish & Intelligence
27. Canvas themes / ambient modes
28. AI Desk push-to-canvas
29. Canvas history and recall
30. Smart mode suggestions
31. Mobile-optimized canvas modes
32. Canvas keyboard shortcuts and voice commands

---

## 7. Performance Requirements

- Canvas mode switch: < 200ms
- Chart render from data: < 500ms
- Video embed load: < 1 second to first frame
- iframe load: skeleton immediately, content within 2s
- Image load: progressive with placeholder
- Avatar animation: 60fps
- PiP overlay: draggable, no lag
- Components lazy-loaded, unmounted when not in use
