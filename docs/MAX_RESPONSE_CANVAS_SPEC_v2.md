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
- **Playlist:** MAX can queue multiple videos ("Here are 3 tutorials on cornice installation")
- **Timestamp linking:** MAX can jump to specific moments ("Skip to 2:34 where they show the mounting")
- **Background audio:** Music/podcasts play while canvas shows other content

**Triggers:**
- "Show me how to install a cornice" → YouTube search → plays best tutorial
- "Play some music while I work" → YouTube lo-fi stream, minimized to PiP
- "Find videos about CNC cabinet door designs" → gallery of video thumbnails → click to play
- "Play that video again" → recalls last played video

#### 2.8.2 Web Browser / iframe
- **Full web page embed:** Any URL rendered inside the canvas
- **Supplier websites:** MAX browses Kravet, Robert Allen for fabric lookups
- **Google Maps:** Show customer locations, job sites, driving directions
- **Documentation:** Show API docs, reference materials, tutorials
- **Social media:** Show Instagram, Facebook, X posts or profiles
- **Navigation controls:** Back, forward, refresh, open in external browser
- **MAX annotates:** Can highlight sections of the web page and comment on them

**Triggers:**
- "Show me the Kravet website" → iframe embed
- "Where is the Henderson job site?" → Google Maps embed with address
- "Pull up the Fabricut catalog" → supplier site in canvas
- "Show me our Google reviews" → Google Business profile in canvas

#### 2.8.3 Streaming / Live Content
- **Live YouTube streams:** News, music, events
- **Security cameras:** IP camera feeds from job sites or office (RTSP/HLS)
- **Screen share receive:** Someone shares their screen with you via the canvas
- **Dashboard feeds:** Embed external dashboards (analytics, monitoring)
- **Always-on option:** Pin a stream to a small PiP window permanently

**Triggers:**
- "Put on CNN" → live YouTube CNN stream
- "Show me the shop camera" → IP camera feed
- "Stream the Nationals game" → finds available stream

#### 2.8.4 Media Controls (Universal)
```
┌─────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────┐ │
│ │                                                 │ │
│ │           VIDEO / WEB / STREAM                  │ │
│ │              CONTENT AREA                       │ │
│ │                                                 │ │
│ └─────────────────────────────────────────────────┘ │
│ ◄◄  ▶  ►►  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁●▁▁▁▁  🔊  ⛶  📌 PiP │
│ Source: YouTube — "Cornice Installation Guide"      │
└─────────────────────────────────────────────────────┘

Controls:
  ▶  Play/Pause
  ◄◄ ►► Skip/Seek
  ●──── Progress bar
  🔊  Volume
  ⛶   Fullscreen
  📌  Pin to PiP (minimize to corner, keep playing)
  🔗  Open in browser (external)
  ✕   Close media
```

### 2.9 Comms Mode (NEW)
MAX handles communication directly on the canvas — calls, video chats, and messaging threads.

#### 2.9.1 Video/Voice Call
- **WebRTC video calls:** Customer consultations right in the dashboard
- **Voice-only calls:** VoIP integration for phone calls
- **Call controls:** Mute, camera on/off, screen share, end call
- **During call:** MAX can pull up documents, quotes, mockups on split canvas while call continues
- **Call recording:** Optional recording saved to customer file
- **Post-call summary:** MAX generates summary and action items from the call

**Triggers:**
- "Call Mrs. Henderson" → initiates video/voice call
- "Start a consultation" → opens call interface with screen share ready
- "Schedule a video call with the Hendersons for Thursday at 2pm" → books + sends invite

#### 2.9.2 Messaging Thread View
- **Telegram thread:** Show full conversation with a customer
- **Email thread:** Display email chain in canvas
- **SMS view:** Text message history
- **MAX can draft responses** inline while you review the thread
- **Quick actions:** Reply, forward, archive, add to CRM

**Triggers:**
- "Show me my conversation with Henderson" → Telegram/email thread on canvas
- "What did the client say about the fabric?" → searches messages, shows relevant thread
- "Draft a follow-up to Henderson" → shows thread + MAX's draft reply

#### 2.9.3 Multi-Comms (Split)
- Video call on top half, customer file on bottom half
- Call running in PiP while browsing fabric options
- Telegram thread on left, quote builder on right

### 2.10 Live Workspace Mode (NEW)
The canvas becomes a live working surface — not just displaying content but actively working alongside you.

#### 2.10.1 Code/Terminal View
- **Live terminal output:** Watch Claude Code or scripts running
- **Code editor view:** MAX shows code he's writing or reviewing
- **Build logs:** Show deployment or build progress
- **Side-by-side:** Code on left, preview on right

**Triggers:**
- "Show me what Claude Code is doing" → live terminal feed
- "Let me see the code for the quote system" → syntax-highlighted code view
- "Deploy the latest build" → shows deployment progress on canvas

#### 2.10.2 Mockup Studio (links to Visual Mockup Engine)
- Canvas becomes the mockup workspace
- Upload photos, segment, select treatments, render — all on canvas
- Before/after slider built into canvas
- Fabric swatches displayed in canvas sidebar
- Fully interactive — not just a display

#### 2.10.3 Quote Builder Live
- Canvas shows quote being assembled in real-time
- Line items, pricing, materials — all visible on canvas
- PDF preview renders live as you build
- Customer info auto-populated from CRM

#### 2.10.4 Calendar/Schedule View
- Full calendar embed on canvas
- Drag-and-drop scheduling
- MAX suggests optimal scheduling
- Color-coded by: installations, consultations, follow-ups, personal

---

## 3. Content Detection & Routing

Max's response is analyzed in real-time during streaming to determine which canvas mode(s) to activate.

```
Response Analysis Pipeline:
│
├── Contains data/numbers/metrics? → Chart Mode
│   ├── Time series → Line/Area chart
│   ├── Comparisons → Bar chart
│   ├── Proportions → Pie/Donut chart
│   └── Single metric → Gauge/Big Number
│
├── References a document/file? → Document Mode
│   ├── PDF/DOCX → Document viewer with spotlight
│   ├── Spreadsheet → Data table with highlights
│   └── Code → Syntax-highlighted code block
│
├── References a website/URL? → Web Content Mode or Media/Embed
│   ├── YouTube/Vimeo link → Media Mode (video player)
│   ├── Article → Preview card + key quote
│   ├── Product → Product card with image
│   ├── Map/location → Media Mode (Google Maps embed)
│   └── General URL → Media Mode (iframe)
│
├── Video/media request? → Media/Embed Mode
│   ├── "Show me" / "Play" / "Stream" → Video player
│   ├── "Browse" / "Pull up" / "Open" → iframe embed
│   └── "Put on" / "Background music" → Streaming + PiP
│
├── Communication request? → Comms Mode
│   ├── "Call" / "Video call" → WebRTC call interface
│   ├── "Show messages" / "Show thread" → Message thread view
│   └── "Draft reply" / "Send message" → Compose + thread
│
├── Active work request? → Live Workspace Mode
│   ├── "Build a quote" → Quote builder live
│   ├── "Show mockup" → Mockup studio
│   ├── "Show calendar" → Calendar view
│   └── "Show terminal" / "Show code" → Code/terminal view
│
├── Describes something visual? → Image Mode
│   ├── Design concept → AI-generated image
│   ├── Existing thing → Web image search
│   └── Comparison → Side-by-side
│
├── Multiple content types? → Split Canvas Mode
│
├── Structured briefing? → Presentation Mode
│
└── Simple conversation → Avatar Mode (default)
```

---

## 4. Progressive Rendering

Inspired by Coherence's streaming chart approach and Vercel AI SDK's generative UI:

1. **Stream starts:** Avatar appears, begins "speaking" animation
2. **Content detected:** Canvas mode transitions smoothly (fade/slide)
3. **Data arrives:** Charts/images/documents/media load progressively
4. **Stream ends:** Final state, interactive elements become active
5. **User can interact:** Click charts, zoom documents, expand images, control media

Key: The canvas NEVER waits for the full response. It builds as Max speaks.

**Media-specific rendering:**
- Video: thumbnail loads first, then player initializes, autoplay optional
- iframe: loading skeleton shown, then page renders
- Call: ringtone/connecting UI, then video feed
- Workspace: skeleton layout, then components hydrate

---

## 5. Technical Architecture

### 5.1 Components

| Component | Purpose | ~Lines | Phase |
|-----------|---------|--------|-------|
| `ResponseCanvas.tsx` | Main canvas orchestrator, mode switching | 400 | 1 |
| `AvatarDisplay.tsx` | Animated Max avatar with states | 200 | 1 |
| `ChartCanvas.tsx` | Dynamic chart rendering (Recharts) | 250 | 1 |
| `DocumentCanvas.tsx` | Document viewer with spotlight/zoom | 200 | 1 |
| `WebPreviewCanvas.tsx` | Web content cards with citations | 150 | 1 |
| `ImageCanvas.tsx` | Image display, gallery, comparison | 180 | 1 |
| `SplitCanvas.tsx` | Multi-panel layout manager | 120 | 1 |
| `PresentationCanvas.tsx` | Slide-based narrative mode | 200 | 2 |
| `MediaCanvas.tsx` | Video player, iframe embed, streaming | 350 | 2 |
| `CommsCanvas.tsx` | Video call, messaging threads, drafting | 300 | 3 |
| `WorkspaceCanvas.tsx` | Live workspace (code, mockup, quote, calendar) | 250 | 3 |
| `PiPOverlay.tsx` | Picture-in-picture floating window | 120 | 2 |
| `CanvasTransition.tsx` | Smooth mode transitions | 80 | 1 |
| `ContentAnalyzer.ts` | Real-time response analysis for mode selection | 200 | 1 |
| `MediaController.ts` | Universal media controls (play, pause, volume, PiP) | 150 | 2 |
| `QuoteCallout.tsx` | Styled quote extraction with source | 60 | 1 |
| `MetricCard.tsx` | Big number / KPI display | 50 | 1 |
| `CanvasHistory.ts` | Remember and recall previous canvas states | 100 | 2 |

### 5.2 Integration Points

- **useChat hook:** Extended to emit content-type hints as streaming progresses
- **BottomBar:** Chat input triggers canvas response
- **CommandCenter:** Canvas IS the left column — always active, always available
- **Telegram:** Canvas content can be serialized and sent as Telegram messages (simplified)
- **WebRTC:** For video/voice calls via canvas
- **YouTube Data API:** For video search and embed
- **Google Maps Embed API:** For location displays
- **AI Desks:** Each desk can push content to the canvas via MAX

### 5.3 Data Flow

```
User Input (text/voice/Telegram)
    ↓
BottomBar → useChat hook → API (Grok/Claude)
    ↓
Streaming Response
    ↓
ContentAnalyzer (real-time parsing — expanded for media/comms/workspace detection)
    ↓
ResponseCanvas (mode selection + rendering)
    ↓
Progressive UI Update
    ├── Charts build
    ├── Images load
    ├── Text streams
    ├── Video embeds
    ├── Calls connect
    ├── Workspaces hydrate
    └── PiP overlays activate
```

---

## 6. Features — Full Feature Set

### 6.1 Generative UI (from Vercel AI SDK)
- Max can dynamically generate UI components based on context
- Example: "Show me contractor availability" → generates interactive calendar widget
- Example: "Compare these two quotes" → generates comparison table with highlights

### 6.2 Interactive Data Visualization (from Coherence)
- Charts render inline as data streams in
- Hover, zoom, filter capabilities on all charts
- Export chart as image or data

### 6.3 Canvas Memory
- Canvas remembers previous visualizations in the conversation
- "Show me that chart again" → recalls and re-renders
- "Play that video from earlier" → recalls and plays
- "Go back to the Henderson quote" → restores workspace state
- Pin important canvases to a sidebar for reference

### 6.4 Canvas Actions
Each canvas mode has contextual action buttons:

| Mode | Actions |
|------|---------|
| Chart | Export, Fullscreen, Change Type, Add to Dashboard |
| Document | Highlight, Annotate, Share, Send to Desk |
| Image | Save, Send to Telegram, Use in Marketing |
| Web | Open Source, Save Link, Share |
| Video | PiP, Fullscreen, Share Link, Save to Library |
| Call | Mute, Camera, Share Screen, Record, End |
| Workspace | Save, Export, Share, Assign to Desk |

### 6.5 Morning Briefing Mode
- Triggered by "Good morning" or scheduled
- Max presents a multi-slide canvas:
  - Slide 1: System status + overnight alerts
  - Slide 2: Overnight Telegram messages (processed by desks)
  - Slide 3: Today's schedule + priorities
  - Slide 4: Pending client communications
  - Slide 5: Financial snapshot
  - Slide 6: Each AI Desk's status report
  - Slide 7: Tasks requiring your attention
- Each slide uses the appropriate canvas mode
- Background music option during briefing

### 6.6 Telegram Canvas Sync
- When Max responds on Telegram, create simplified versions:
  - Charts → rendered as images sent via Telegram
  - Documents → key quotes as text + file attachment
  - Videos → YouTube links with timestamp
  - Images → sent directly
  - Complex canvases → link to web dashboard for full view
  - Calls → Telegram voice/video call initiation

### 6.7 Voice + Canvas Sync
- When using voice chat, Max narrates while canvas updates
- TTS synchronized with canvas transitions
- "Let me show you..." triggers canvas mode change
- "Let me play this for you..." triggers media mode
- Voice commands control media: "Pause," "Skip ahead," "Turn it up"

### 6.8 Collaborative Canvas
- Share a canvas view with team members
- Real-time annotation on shared canvases
- Used for client presentations, team reviews
- Share a mockup canvas with customer for live feedback

### 6.9 Media Library (NEW)
- Saved videos, links, streams organized by category
- Favorites and recently played
- MAX can suggest: "Last time you were working on cornices, you found this video helpful"
- Playlists: "Work music," "Installation tutorials," "Marketing inspiration"

### 6.10 Canvas Themes / Ambient Mode (NEW)
- **Work mode:** Clean, focused, minimal — charts and docs
- **Creative mode:** Mood boards, images, videos, music
- **Monitoring mode:** System stats, cameras, dashboards tiled
- **Presentation mode:** Polished, client-facing, branded
- **Night mode:** Dimmed, ambient music, low-priority content only

---

## 7. Avatar Specifications

### 7.1 Visual Design
- Style: Modern, minimalist, professional
- Colors: Gold/dark theme consistent with Empire branding
- States: Idle, Thinking, Speaking, Presenting, Listening, Watching (new — when media plays)
- Size: Adaptive — large in avatar mode, small thumbnail when content is showing
- During media: Avatar minimizes to corner, occasionally reacts

### 7.2 Animation States

| State | Visual | Trigger |
|-------|--------|---------|
| Idle | Subtle breathing, gentle glow | No active response |
| Thinking | Eyes scanning, particles moving | After user sends message |
| Speaking | Mouth moving, hand gestures | During text streaming |
| Presenting | Pointing at content, turning to canvas | When showing charts/docs |
| Listening | Head tilted, ear highlighted | During voice input |
| Watching | Eyes on media, relaxed pose | During video/stream playback |
| On Call | Headset glow, attentive posture | During video/voice call |
| Alert | Gold pulse, attention indicator | Important notification |
| Working | Typing animation, focused | During live workspace tasks |

### 7.3 Implementation Options
- **Option A:** CSS/SVG animated avatar (lightweight, fast)
- **Option B:** Lottie animation (smooth, pre-rendered)
- **Option C:** Three.js 3D model (premium, interactive)
- **Recommended:** Start with Option A (SVG + CSS), upgrade to B or C later

---

## 8. Implementation Priority

### Phase 1 — Foundation (Build First)
1. ResponseCanvas.tsx shell with mode switching
2. AvatarDisplay.tsx with basic states (SVG + CSS)
3. ChartCanvas.tsx with Recharts integration
4. ContentAnalyzer.ts for mode detection (expanded for all modes)
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
17. Media library (save, organize, recall)
18. Voice + canvas synchronization

### Phase 3 — Communication & Live Work
19. CommsCanvas.tsx — WebRTC video/voice calls
20. Messaging thread view (Telegram, email, SMS)
21. WorkspaceCanvas.tsx — live quote builder
22. Mockup Studio integration on canvas
23. Calendar/schedule view on canvas
24. Code/terminal view on canvas
25. Telegram canvas sync
26. Collaborative canvas sharing

### Phase 4 — Polish & Intelligence
27. Canvas themes / ambient modes
28. AI Desk push-to-canvas (desks show content via MAX)
29. Canvas history and recall
30. Smart mode suggestions ("Want me to show you a chart of that?")
31. Mobile-optimized canvas modes
32. Canvas keyboard shortcuts and voice commands

---

## 9. Performance Requirements

- Canvas mode switch: < 200ms
- Chart render from data: < 500ms
- Video embed load: < 1 second to first frame
- iframe load: show skeleton immediately, content within 2s
- Image load: progressive, show placeholder immediately
- Avatar animation: 60fps, no jank
- PiP overlay: stays above all content, draggable, no lag
- Video call: < 500ms latency for WebRTC
- Memory: Canvas components lazy-loaded, unmounted when not in use
- Mobile: Simplified canvas modes for Telegram/small screens
- Media: Buffer and preload for smooth playback

---

## 10. Example Scenarios

**Scenario 1: "How are sales this month?"**
→ Avatar appears thinking → Chart Mode activates → Bar chart builds progressively showing weekly sales → Big number card shows total → Avatar says "Sales are up 15% from last month"

**Scenario 2: "Review the Henderson contract"**
→ Document Mode → PDF renders in canvas → Max highlights payment terms section → Quote callout: "Net 30 payment terms" → Avatar: "I notice the liability clause needs attention"

**Scenario 3: "Good morning Max"**
→ Presentation Mode → 7 slides auto-advance → System status → Overnight messages → Today's schedule → Client comms → Financial snapshot → Desk reports → "You have 2 overdue invoices and a consultation at 2pm"

**Scenario 4: "Show me CNC router designs for cabinet doors"**
→ Image Mode → Web search results with 4 images → Gallery view → Source citations below each → Avatar: "Here are some popular CNC patterns. Want me to find installation videos too?"

**Scenario 5: "Show me how to install a board-mounted cornice"**
→ Media Mode → YouTube search → Best tutorial found → Video plays inline on canvas → MAX: "This one covers the exact technique. Skip to 3:24 for the mounting brackets." → Timestamp link highlighted

**Scenario 6: "Call Mrs. Henderson about the fabric selection"**
→ Comms Mode → Call interface appears → Split canvas: video call (top) + Henderson's quote with fabric options (bottom) → MAX has customer file ready → Post-call: "Here's what was discussed. She wants the Kravet 36922. Want me to update the quote?"

**Scenario 7: "Play some lo-fi beats while I work on quotes"**
→ Media Mode → YouTube lo-fi stream starts → Auto-minimizes to PiP corner → Canvas returns to previous mode (quote workspace) → Music continues in background

**Scenario 8: "What did I miss last night?"**
→ Split Canvas → Left: timeline of Telegram messages (categorized by desk) → Right: priority alerts and actions taken → Bottom: quick action buttons → Avatar narrates highlights → "ForgeDesk followed up with Henderson at 9am. She confirmed the cornice. MarketDesk relisted 3 items. You have 2 items needing your approval."

**Scenario 9: "Show me the Henderson job site on a map"**
→ Media Mode (Maps) → Google Maps embed with Henderson address pinned → Driving directions from your location → Nearby supplier locations highlighted → "It's 23 minutes from your shop. Fabric Depot is on the way if you need to pick up supplies."

**Scenario 10: "Build a quote for Henderson — cornices for 3 windows"**
→ Live Workspace Mode → Quote builder opens on canvas → Customer info auto-fills from CRM → MAX: "I have her measurements from the consultation. The 3 windows are 48", 72", and 60". Which cornice style?" → Line items build in real-time as you configure → PDF preview renders live → "Ready to send?"
