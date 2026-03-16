// Complete Empire Documentation Registry
// Every document mapped to every ecosystem product it applies to
// Documents that overlap appear under ALL relevant products

export interface DocEntry {
  title: string;
  path: string;
  type: 'spec' | 'readme' | 'guide' | 'api' | 'plan' | 'report' | 'config' | 'audit' | 'session' | 'architecture' | 'legal' | 'business' | 'pdf' | 'image' | 'presentation' | 'mockup' | 'diagram' | 'compliance' | 'code';
  description: string;
}

// ═══════════════════════════════════════════════
// SHARED DOCUMENTS — appear across multiple products
// ═══════════════════════════════════════════════
const SHARED_ARCHITECTURE: DocEntry[] = [
  { title: "Empire v4 Architecture (FINAL PDF)", path: "docs/recovered/architecture/Empire_v4_Architecture_FINAL_2026-03-07.pdf", type: "architecture", description: "Final v4 architecture diagram — PDF" },
  { title: "Empire v4 Architecture (Corrected PDF)", path: "docs/recovered/architecture/Empire_v4_Architecture_CORRECTED_2026-03-07.pdf", type: "architecture", description: "Corrected architecture diagram — PDF" },
  { title: "Empire v4 Architecture Map (PDF)", path: "docs/recovered/architecture/Empire_v4_Architecture_Map_2026-03-06.pdf", type: "architecture", description: "Architecture map overview — PDF" },
  { title: "Empire v4 Architecture (Mermaid)", path: "docs/recovered/architecture/EmpireBox_v4_Architecture.mermaid", type: "diagram", description: "Architecture diagram — Mermaid source" },
  { title: "Architecture Diagram (MMD)", path: "~/Empire/data/architecture_diagram.mmd", type: "diagram", description: "Mermaid diagram of full architecture (356 lines)" },
  { title: "Architecture Map (HTML)", path: "~/Downloads/Empire_v4_Architecture_Map.html", type: "mockup", description: "Interactive HTML architecture map" },
  { title: "EmpireBox Architecture v4 (HTML)", path: "~/Downloads/EmpireBox_Architecture_v4.html", type: "mockup", description: "Interactive v4 architecture visualization" },
];

const SHARED_SESSION_REPORTS: DocEntry[] = [
  { title: "Session Report Mar 8 (PDF)", path: "docs/Empire_Session_Report_2026-03-08_0400.pdf", type: "report", description: "Empire session report — March 8, 2026" },
  { title: "Session Context Mar 7 (PDF)", path: "~/Documents/EMPIRE SESSION CONTEXT — 2026-03-07 23-55pm.pdf", type: "session", description: "Session context handoff — March 7" },
  { title: "Session Context Mar 8 (PDF)", path: "~/Documents/EMPIRE SESSION CONTEXT — 2026-03-08 430 pm.pdf", type: "session", description: "Session context handoff — March 8" },
  { title: "Full System Audit (DOCX)", path: "docs/recovered/EmpireBox_Full_Audit_2026-03-06.docx", type: "audit", description: "Complete EmpireBox system audit — March 6, 2026" },
];

const SHARED_MOCKUPS: DocEntry[] = [
  { title: "Command Center Full Mockup (HTML)", path: "~/Downloads/Empire_Command_Center_Full_Mockup_2026-03-07.html", type: "mockup", description: "Full multi-page dashboard mockup" },
  { title: "Command Center v3 MultiScreen (HTML)", path: "~/Downloads/Empire_Command_Center_v3_MultiScreen_2026-03-07.html", type: "mockup", description: "v3 multi-screen layout mockup" },
  { title: "MAX Command Center Redesign (HTML)", path: "~/Downloads/MAX_Command_Center_Redesign_Mockup_2026-03-07.html", type: "mockup", description: "MAX AI interface redesign mockup" },
  { title: "Multi-Page Mockup (HTML)", path: "~/Documents/Empire Command Center — Multi-Page Mockup.html", type: "mockup", description: "Empire Command Center multi-page mockup" },
  { title: "QB-Replacement Dashboard (PDF)", path: "~/Documents/BUILD: Full QB-Replacement Business Dashboard.pdf", type: "mockup", description: "Full QuickBooks replacement dashboard spec" },
];

const SHARED_GENESIS: DocEntry[] = [
  { title: "Project Origin (PDF)", path: "Idea started after video from Alex Fin.pdf", type: "report", description: "Original inspiration — Alex Fin AI video" },
  { title: "Project Origin (DOCX)", path: "Idea started after video from Alex Fin.docx", type: "report", description: "Original inspiration document — editable" },
];

const QUOTE_PDFS: DocEntry[] = [
  { title: "Quote PDF: EST-2026-001", path: "data/quotes/pdf/EST-2026-001.pdf", type: "pdf", description: "Generated estimate PDF — #001" },
  { title: "Quote PDF: EST-2026-005", path: "data/quotes/pdf/EST-2026-005.pdf", type: "pdf", description: "Generated estimate PDF — #005" },
  { title: "Quote PDF: EST-2026-007", path: "data/quotes/pdf/EST-2026-007.pdf", type: "pdf", description: "Generated estimate PDF — #007" },
  { title: "Quote PDF: EST-2026-010", path: "data/quotes/pdf/EST-2026-010.pdf", type: "pdf", description: "Generated estimate PDF — #010" },
  { title: "Quote PDF: EST-2026-012", path: "data/quotes/pdf/EST-2026-012.pdf", type: "pdf", description: "Generated estimate PDF — #012" },
  { title: "Quote PDF: EST-2026-016", path: "data/quotes/pdf/EST-2026-016.pdf", type: "pdf", description: "Generated estimate PDF — #016" },
  { title: "Quote PDF: EST-2026-022", path: "data/quotes/pdf/EST-2026-022.pdf", type: "pdf", description: "Generated estimate PDF — #022" },
  { title: "Customer Quote: EMP-Q-260301", path: "data/quotes/pdf/EMP-Q-260301-7FF9.pdf", type: "pdf", description: "Customer quote PDF — March 1" },
  { title: "Customer Quote: EMP-Q-260303-CFF9", path: "data/quotes/pdf/EMP-Q-260303-CFF9.pdf", type: "pdf", description: "Customer quote PDF — March 3" },
  { title: "Customer Quote: EMP-Q-260303-900C", path: "data/quotes/pdf/EMP-Q-260303-900C.pdf", type: "pdf", description: "Customer quote PDF — March 3" },
];

const DESIGN_IMAGES: DocEntry[] = [
  { title: "DreamFurniture Feather Design", path: "~/Empire/uploads/images/DreamFurnitureFeather.webp", type: "image", description: "Furniture design reference image" },
  { title: "Windows by Room — Dining", path: "~/Empire/uploads/images/windows-by-room-dining-room-900x600.webp", type: "image", description: "Window treatment reference — dining room" },
  { title: "Whittington Design 1", path: "~/Empire/uploads/images/Whittington Desing 1.jpg", type: "image", description: "Whittington design reference" },
  { title: "Master Bedroom Ideas", path: "~/Empire/uploads/images/master-bedroom-ideas-bedroom-with-white-curtains-jpg-77K.jpg", type: "image", description: "Master bedroom design reference" },
  { title: "Tan Couch Window Treatment", path: "~/Empire/uploads/images/tan-couch-front-windows-living-room-118K.jpg", type: "image", description: "Living room window treatment reference" },
];

const MARKET_PRESENTATION: DocEntry[] = [
  { title: "Drapery Market Trends 2026 (PDF)", path: "data/presentations/260303_0314_dc-custom-drapery-market-trends-2026.pdf", type: "presentation", description: "Custom drapery market trends — 462KB presentation" },
];

// ═══════════════════════════════════════════════
// NEW SHARED: Chat Archives & Session Summaries
// ═══════════════════════════════════════════════
const SHARED_CHAT_ARCHIVES: DocEntry[] = [
  { title: "Chat Summary 2026-02-22 23:45 UTC", path: "CHAT_SUMMARY_2026-02-22_2345UTC.md", type: "session", description: "Chat summary — Feb 22 late night session" },
  { title: "Chat Summary: lm-sensors Crashes", path: "CHAT_SUMMARY_2026-02-22-lm-sensors-crashes.md", type: "session", description: "lm-sensors installation & system stability issues" },
  { title: "Chat Summary 2026-02-22", path: "CHAT_SUMMARY_2026-02-22.md", type: "session", description: "Chat session summary — Feb 22" },
  { title: "Chat Archive: Feb 19 Main Session", path: "docs/CHAT_ARCHIVE/2026-02-19_MAIN_CHAT_SUMMARY.md", type: "session", description: "Main development chat — Feb 19" },
  { title: "Chat Archive: Feb 25 Claude Session", path: "docs/CHAT_ARCHIVE/2026-02-25_2041_claude_session.md", type: "session", description: "Claude session — Feb 25" },
  { title: "Chat Archive: Feb 26 Session", path: "docs/CHAT_ARCHIVE/2026-02-26_0015_session.md", type: "session", description: "Session summary — Feb 26" },
  { title: "Chat Archive: Latest Claude", path: "docs/CHAT_ARCHIVE/latest_claude.md", type: "session", description: "Most recent Claude chat save" },
  { title: "Chat Archive README", path: "docs/CHAT_ARCHIVE/README.md", type: "readme", description: "Chat archive index and organization" },
  { title: "Salvaged Chat: Feb 16", path: "docs/salvaged/2026-02-16_MAIN_CHAT_SUMMARY.md", type: "session", description: "Salvaged main dev chat — Feb 16" },
  { title: "Salvaged Chat: Feb 17", path: "docs/salvaged/2026-02-17_MAIN_CHAT_SUMMARY.md", type: "session", description: "Salvaged main dev chat — Feb 17" },
  { title: "Salvaged Chat: Feb 18", path: "docs/salvaged/2026-02-18_MAIN_CHAT_SUMMARY.md", type: "session", description: "Salvaged main dev chat — Feb 18" },
  { title: "MAX Session Feb 22", path: "docs/MAX_SESSION_2026-02-22.md", type: "session", description: "EmpireBox MAX Command Center dev summary" },
  { title: "Session Log Feb 24", path: "logs/2026-02-24/session-log.md", type: "session", description: "EmpireBox session log — Feb 24" },
  { title: "Session Save Feb 27", path: "saves/EMPIRE_SESSION_SAVE_20260227.md", type: "session", description: "Empire session save — Feb 27 evening" },
  { title: "Opus 4.5 Chat Issues (Fri)", path: "fri_feb_20_2026_chat_issues_with_opus_4_5.md", type: "session", description: "Copilot chat issues with Opus 4.5 — Feb 20" },
  { title: "Opus 4.5 Chat Issues (Sat)", path: "sat_feb_21_2026_chat_issues_with_opus_4_5.md", type: "session", description: "Copilot chat issues with Opus 4.5 — Feb 21" },
];

// ═══════════════════════════════════════════════
// NEW SHARED: Recovered Mermaid Diagrams
// ═══════════════════════════════════════════════
const SHARED_MERMAID_DIAGRAMS: DocEntry[] = [
  { title: "Empire v4 Full Ecosystem Diagram", path: "docs/recovered/mermaid/Empire_v4_Full_Ecosystem_2026-03-06.md", type: "diagram", description: "Full ecosystem Mermaid diagram — v4" },
  { title: "Empire v4 Redesigned Ecosystem", path: "docs/recovered/mermaid/Empire_v4_Redesigned_Ecosystem_2026-03-06.md", type: "diagram", description: "Redesigned ecosystem diagram — v4" },
  { title: "Mermaid: Full System", path: "docs/recovered/mermaid/mermaid_1_full_system.md", type: "diagram", description: "Full system architecture diagram" },
  { title: "Mermaid: Services & Ports", path: "docs/recovered/mermaid/mermaid_2_services_ports.md", type: "diagram", description: "Services and ports diagram" },
  { title: "Mermaid: Memory Flow", path: "docs/recovered/mermaid/mermaid_3_memory_flow.md", type: "diagram", description: "Memory flow diagram" },
  { title: "Mermaid: AI Routing", path: "docs/recovered/mermaid/mermaid_4_ai_routing.md", type: "diagram", description: "AI routing diagram" },
  { title: "Mermaid: Data Flow", path: "docs/recovered/mermaid/mermaid_5_data_flow.md", type: "diagram", description: "Data flow diagram" },
  { title: "Mermaid: Products", path: "docs/recovered/mermaid/mermaid_6_products.md", type: "diagram", description: "Products architecture diagram" },
];

// ═══════════════════════════════════════════════
// NEW SHARED: Recovered HTML Mockups
// ═══════════════════════════════════════════════
const SHARED_RECOVERED_MOCKUPS: DocEntry[] = [
  { title: "EmpireBox Architecture v4 (Recovered HTML)", path: "docs/recovered/mockups/EmpireBox_Architecture_v4.html", type: "mockup", description: "Interactive v4 architecture — recovered" },
  { title: "Command Center Full Mockup (Recovered HTML)", path: "docs/recovered/mockups/Empire_Command_Center_Full_Mockup_2026-03-07.html", type: "mockup", description: "Full dashboard mockup — recovered" },
  { title: "Command Center v3 MultiScreen (Recovered HTML)", path: "docs/recovered/mockups/Empire_Command_Center_v3_MultiScreen_2026-03-07.html", type: "mockup", description: "Multi-screen layout — recovered" },
  { title: "Architecture Map (Recovered HTML)", path: "docs/recovered/mockups/Empire_v4_Architecture_Map.html", type: "mockup", description: "Architecture map — recovered" },
  { title: "MAX Redesign Mockup (Recovered HTML)", path: "docs/recovered/mockups/MAX_Command_Center_Redesign_Mockup_2026-03-07.html", type: "mockup", description: "MAX interface redesign — recovered" },
];

// ═══════════════════════════════════════════════
// NEW SHARED: Context & Memory Files
// ═══════════════════════════════════════════════
const SHARED_CONTEXT_FILES: DocEntry[] = [
  { title: "Session Context Mar 7", path: "docs/recovered/session-contexts/claude_code_context_2026-03-07.md", type: "session", description: "Empire session context — Mar 7" },
  { title: "Session Context Mar 7 (11:30 PM)", path: "docs/recovered/session-contexts/claude_code_context_2026-03-07_2330.md", type: "session", description: "Empire session context — Mar 7 late night" },
  { title: "Session Context Mar 8 (Final)", path: "docs/recovered/session-contexts/claude_code_context_2026-03-08_0000.md", type: "session", description: "Final session context — Mar 7→8 handoff" },
  { title: "Latest Context Mar 8", path: "docs/claude_code_context_2026-03-08.md", type: "session", description: "Empire session context — Mar 8" },
  { title: "MAX Brain v4.0 (Recovered)", path: "docs/recovered/memory_v4.md", type: "report", description: "Complete MAX brain v4.0 — recovered" },
  { title: "Context Bridge Reference", path: "docs/recovered/tools/context-bridge-reference.md", type: "guide", description: "Claude context bridge reference" },
  { title: "MAX Memory (Live)", path: "max/memory.md", type: "report", description: "MAX AI complete brain v3.1 — live" },
  { title: "Inpainting Mega Task", path: "docs/recovered/claude_code_inpaint_prompt_2026-03-08_0015.md", type: "session", description: "Mega task: inpainting + PDF redesign + wiring" },
];

// ═══════════════════════════════════════════════
// NEW SHARED: Reports & Audits
// ═══════════════════════════════════════════════
const SHARED_REPORTS: DocEntry[] = [
  { title: "Chat Report — Full Ecosystem", path: "docs/CHAT_REPORT.md", type: "report", description: "EmpireBox ecosystem comprehensive chat report" },
  { title: "GitHub Audit Report", path: "docs/reports/2026-03-02_github_audit_report.md", type: "audit", description: "GitHub audit & brain update report — Mar 2" },
  { title: "Wiring Audit Report", path: "empire-command-center/WIRING_REPORT.md", type: "audit", description: "Command center frontend-to-backend wiring audit" },
  { title: "Crash Incident Report", path: "logs/crash_report.md", type: "report", description: "System crash incident report" },
  { title: "EmpireBox Summary", path: "empirebox_summary.md", type: "report", description: "EmpireBox platform summary overview" },
  { title: "Daily Report PDF", path: "backend/data/presentations/260308_0611_daily-report-for-empire-operations.pdf", type: "presentation", description: "Daily operations report — March 8, 2026" },
];

export const DOCS_REGISTRY: Record<string, DocEntry[]> = {

  // ═══════════════════════════════════════════════
  // OWNER'S DESK
  // ═══════════════════════════════════════════════
  owner: [
    ...SHARED_ARCHITECTURE,
    ...SHARED_SESSION_REPORTS,
    ...SHARED_MOCKUPS,
    ...SHARED_GENESIS,
    ...SHARED_CHAT_ARCHIVES,
    ...SHARED_MERMAID_DIAGRAMS,
    ...SHARED_RECOVERED_MOCKUPS,
    ...SHARED_CONTEXT_FILES,
    ...SHARED_REPORTS,
    { title: "Empire README", path: "README.md", type: "readme", description: "Main EmpireBox platform overview with full ecosystem table" },
    { title: "CLAUDE.md", path: "CLAUDE.md", type: "guide", description: "Claude Code development guidance for the repository" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products in 8 categories overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "Comprehensive listing of 30+ products" },
    { title: "MAX Brain Spec", path: "docs/MAX_BRAIN_SPEC.md", type: "spec", description: "Persistent AI memory system (Ollama + portable drive)" },
    { title: "MAX Response Canvas v1", path: "docs/MAX_RESPONSE_CANVAS_SPEC.md", type: "spec", description: "MAX interface canvas specification" },
    { title: "MAX Response Canvas v2", path: "docs/MAX_RESPONSE_CANVAS_SPEC_v2.md", type: "spec", description: "MAX interface canvas v2 specification" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "Founder → MAX → AI Desks architecture" },
    { title: "Desk Consolidation Plan", path: "docs/DESK_CONSOLIDATION_PLAN.md", type: "plan", description: "Overlapping desk systems consolidation strategy" },
    { title: "Desks & Task Engine Plan", path: "docs/EMPIRE_DESKS_AND_TASK_ENGINE_PLAN.md", type: "plan", description: "Desk & agent consolidation plan" },
    { title: "Brand Guidelines", path: "docs/BRAND_GUIDELINES.md", type: "guide", description: "Brand colors, typography, styling" },
    { title: "Telegram Setup", path: "docs/TELEGRAM_SETUP.md", type: "guide", description: "Telegram bot configuration guide" },
    { title: "EmpireBox System README", path: "EMPIREBOX_SYSTEM_README.md", type: "readme", description: "Hybrid AI system with token budgets & routing" },
    { title: "EmpireBox Master Backup", path: "EMPIREBOX_MASTER_BACKUP_2026-02-19_Version7.md", type: "report", description: "Version 7 master backup documentation" },
    { title: "Economic Intelligence", path: "docs/ECONOMIC_INTELLIGENCE.md", type: "spec", description: "Financial tracking & analytics system" },
    { title: "Legal Compliance Audit", path: "docs/LEGAL_COMPLIANCE_AUDIT.md", type: "legal", description: "Legal compliance & IP protection audit" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections (Conservative/Moderate/Aspirational)" },
    { title: "Product Decisions Log", path: "docs/PRODUCT_DECISIONS.md", type: "plan", description: "Key product decisions log" },
    { title: "Setup Guide", path: "docs/SETUP.md", type: "guide", description: "Prerequisites & backend setup" },
    { title: "Setup Flow", path: "docs/SETUP_FLOW.md", type: "guide", description: "Application setup workflow" },
    { title: "Quick Start Card", path: "docs/QUICK_START_CARD.md", type: "guide", description: "Quick reference card" },
    { title: "Known Issues", path: "docs/KNOWN_ISSUES.md", type: "report", description: "Known bugs & workarounds" },
    { title: "Crash Recovery Runbook", path: "docs/CRASH_RECOVERY_RUNBOOK.md", type: "guide", description: "Recovery procedures after system freeze" },
    { title: "MAX Memory v3.1", path: "backend/data/max/memory.md", type: "report", description: "MAX AI persistent memory (founder profile, products, status)" },
    { title: "Memory v4 (Downloads)", path: "~/Downloads/memory_v4.md", type: "report", description: "Complete MAX brain v4.0 (260-line system memory)" },
    { title: "Architecture Map", path: "~/Empire/data/architecture_map.md", type: "architecture", description: "Complete architecture map (571 lines, services, DBs, tools)" },
    { title: "Beelink Operations Audit", path: "~/Empire/data/beelink_operations_audit.md", type: "audit", description: "Full development audit Feb 20 - Mar 6, 2026 (1167 lines)" },
    { title: "Implementation Summary", path: "IMPLEMENTATION_SUMMARY.md", type: "report", description: "EmpireBox implementation overview (81 files, ~3,815 lines)" },
    { title: "Implementation Complete", path: "IMPLEMENTATION_COMPLETE.md", type: "report", description: "Hybrid AI system implementation status" },
    { title: "Conversation Summary", path: "conversation_summary.md", type: "session", description: "General conversation summary" },
    { title: "Modules Index", path: "modules/INDEX.md", type: "architecture", description: "Product index with all 23 ecosystem products" },
    { title: "Owner Module README", path: "modules/owner/README.md", type: "readme", description: "Owner's Desk — central command hub" },
  ],

  // ═══════════════════════════════════════════════
  // EMPIRE WORKROOM
  // ═══════════════════════════════════════════════
  workroom: [
    ...QUOTE_PDFS,
    ...DESIGN_IMAGES,
    ...MARKET_PRESENTATION,
    ...SHARED_ARCHITECTURE,
    ...SHARED_REPORTS,
    { title: "Workroom Module README", path: "modules/workroom/README.md", type: "readme", description: "Upholstery/sewing business — quotes, jobs, finance, inventory" },
    { title: "Visual Mockup Engine Spec", path: "docs/VISUAL_MOCKUP_ENGINE_SPEC.md", type: "spec", description: "Photo-to-mockup visualization for workrooms" },
    { title: "Shipping Integration", path: "docs/SHIPPING_INTEGRATION.md", type: "guide", description: "EasyPost shipping integration" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "Founder → MAX → AI Desks architecture" },
    { title: "Desk Consolidation Plan", path: "docs/DESK_CONSOLIDATION_PLAN.md", type: "plan", description: "Overlapping desk systems consolidation" },
    { title: "Industry Templates", path: "docs/INDUSTRY_TEMPLATES.md", type: "guide", description: "Custom industry template guide (drapery, electrical, landscape)" },
    { title: "Stripe Compliance", path: "docs/STRIPE_COMPLIANCE_CHECKLIST.md", type: "legal", description: "Stripe merchant requirements" },
    { title: "Backend README", path: "backend/README.md", type: "readme", description: "FastAPI backend with quotes, jobs, finance endpoints" },
    { title: "Quick Start", path: "QUICK_START.md", type: "guide", description: "5-minute quick start guide" },
    { title: "API Reference", path: "docs/API.md", type: "api", description: "REST API documentation" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
  ],

  // ═══════════════════════════════════════════════
  // WOODCRAFT (CraftForge)
  // ═══════════════════════════════════════════════
  craft: [
    ...SHARED_ARCHITECTURE,
    ...DESIGN_IMAGES,
    ...SHARED_REPORTS,
    { title: "CraftForge Status Report (Mar 8)", path: "docs/CRAFTFORGE_STATUS_2026-03-08.md", type: "report", description: "CraftForge current status — March 8, 2026" },
    { title: "WoodCraft Module README", path: "modules/craft/README.md", type: "readme", description: "CNC routing, 3D printing, woodworking" },
    { title: "CraftForge Spec", path: "docs/CRAFTFORGE_SPEC.md", type: "spec", description: "AI-powered wood design & CNC platform" },
    { title: "CraftForge SpaceScan Addendum", path: "docs/CRAFTFORGE_SPACESCAN_ADDENDUM.md", type: "spec", description: "CraftForge space scanning addon" },
    { title: "CraftForge README", path: "craftforge/README.md", type: "readme", description: "CraftForge implementation" },
    { title: "Industry Templates", path: "docs/INDUSTRY_TEMPLATES.md", type: "guide", description: "Custom industry templates" },
    { title: "Desks & Task Engine Plan", path: "docs/EMPIRE_DESKS_AND_TASK_ENGINE_PLAN.md", type: "plan", description: "Desk & agent consolidation" },
    { title: "API Reference", path: "docs/API.md", type: "api", description: "REST API documentation" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // LUXEFORGE
  // ═══════════════════════════════════════════════
  luxe: [
    ...QUOTE_PDFS,
    ...DESIGN_IMAGES,
    ...MARKET_PRESENTATION,
    ...SHARED_ARCHITECTURE,
    ...SHARED_REPORTS,
    { title: "LuxeForge Module README", path: "modules/luxe/README.md", type: "readme", description: "Premium design services — intake, measurements, quotes" },
    { title: "LuxeForge Web README", path: "luxeforge_web/README.md", type: "readme", description: "LuxeForge designer portal" },
    { title: "Visual Mockup Engine Spec", path: "docs/VISUAL_MOCKUP_ENGINE_SPEC.md", type: "spec", description: "Photo-to-mockup visualization" },
    { title: "LeadForge Spec", path: "docs/LEADFORGE_SPEC.md", type: "spec", description: "AI lead generation for LuxeForge" },
    { title: "Zero to Hero Spec", path: "docs/ZERO_TO_HERO_SPEC.md", type: "spec", description: "Business automation specification" },
    { title: "Founders USB Products", path: "founders_usb_installer/docs/PRODUCTS.md", type: "guide", description: "13 bundled products list" },
    { title: "Industry Templates", path: "docs/INDUSTRY_TEMPLATES.md", type: "guide", description: "Custom industry templates (drapery)" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // SOCIALFORGE
  // ═══════════════════════════════════════════════
  social: [
    { title: "EmpireBot Messenger Integration v7", path: "docs_EMPIREBOT_MESSENGER_INTEGRATION_Version7.md", type: "architecture", description: "EmpireBot messenger integration — Version 7" },
    { title: "SocialForge Module README", path: "modules/social/README.md", type: "readme", description: "Social media management & AI content generation" },
    { title: "Zero to Hero Spec", path: "docs/ZERO_TO_HERO_SPEC.md", type: "spec", description: "Business automation (social media section)" },
    { title: "EmpireBox Master Backup", path: "EMPIREBOX_MASTER_BACKUP_2026-02-19_Version7.md", type: "report", description: "Version 7 backup with SocialForge status" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "Desk architecture for social desk" },
  ],

  // ═══════════════════════════════════════════════
  // OPENCLAW
  // ═══════════════════════════════════════════════
  openclaw: [
    { title: "OpenClaw Module README", path: "modules/openclaw/README.md", type: "readme", description: "Local AI assistant powered by Ollama" },
    { title: "MAX Brain Spec", path: "docs/MAX_BRAIN_SPEC.md", type: "spec", description: "Persistent AI memory system (Ollama)" },
    { title: "EmpireBox System README", path: "EMPIREBOX_SYSTEM_README.md", type: "readme", description: "Hybrid AI system with routing" },
    { title: "EmpireBox Master Backup", path: "EMPIREBOX_MASTER_BACKUP_2026-02-19_Version7.md", type: "report", description: "Version 7 backup" },
    { title: "CLAUDE.md", path: "CLAUDE.md", type: "guide", description: "Development guidance (Ollama section)" },
    { title: "Product Decisions", path: "docs/PRODUCT_DECISIONS.md", type: "plan", description: "Key product decisions" },
    { title: "Founders USB Architecture", path: "founders_usb_installer/docs/ARCHITECTURE.md", type: "architecture", description: "System architecture with Ollama" },
    { title: "Founders USB Products", path: "founders_usb_installer/docs/PRODUCTS.md", type: "guide", description: "13 bundled products" },
    { title: "Architecture Map", path: "~/Empire/data/architecture_map.md", type: "architecture", description: "Full architecture map with OpenClaw" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
  ],

  // ═══════════════════════════════════════════════
  // RECOVERYFORGE
  // ═══════════════════════════════════════════════
  recovery: [
    ...SHARED_CONTEXT_FILES,
    ...SHARED_RECOVERED_MOCKUPS,
    ...SHARED_MERMAID_DIAGRAMS,
    { title: "RecoveryForge Module README", path: "modules/recovery/README.md", type: "readme", description: "Business recovery and continuity planning" },
    { title: "Crash Recovery Runbook", path: "docs/CRASH_RECOVERY_RUNBOOK.md", type: "guide", description: "Recovery procedures after system freeze" },
    { title: "Beelink Stability Guide", path: "docs/BEELINK_STABILITY_GUIDE.md", type: "guide", description: "Hardware stability guide" },
    { title: "Known Issues", path: "docs/KNOWN_ISSUES.md", type: "report", description: "Known bugs & workarounds" },
    { title: "VA App Telehealth Spec", path: "docs/VA_APP_TELEHEALTH.md", type: "spec", description: "Virtual assistant telehealth app spec" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "Recovery desk in delegation plan" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
  ],

  // ═══════════════════════════════════════════════
  // MARKETFORGE
  // ═══════════════════════════════════════════════
  market: [
    ...SHARED_ARCHITECTURE,
    ...MARKET_PRESENTATION,
    ...SHARED_REPORTS,
    { title: "MarketForge Module README", path: "modules/market/README.md", type: "readme", description: "Multi-marketplace e-commerce management" },
    { title: "MarketForge Ad Cost Study", path: "docs/MARKETFORGE_AD_STUDY.md", type: "report", description: "MarketForge advertising cost analysis" },
    { title: "MarketForge Marketplace Integration", path: "docs/salvaged/MARKETFORGE_MARKETPLACE_INTEGRATION.md", type: "architecture", description: "Marketplace integration guide — salvaged" },
    { title: "MarketForge MVP Overview", path: "docs/salvaged/MARKETFORGE_MVP_PROJECT_OVERVIEW.md", type: "plan", description: "MarketForge MVP project overview — salvaged" },
    { title: "MarketForge Security Fixes", path: "docs/salvaged/MARKETFORGE_SECURITY_FIXES.md", type: "audit", description: "Security vulnerability fixes — MarketForge" },
    { title: "MarketForge Setup Guide", path: "docs/salvaged/MARKETFORGE_SETUP_GUIDE.md", type: "guide", description: "MarketForge setup guide — salvaged" },
    { title: "MarketForge App Flow", path: "market_forge_app/APP_FLOW.md", type: "architecture", description: "MarketForge app flow diagram" },
    { title: "MarketForge Implementation", path: "market_forge_app/IMPLEMENTATION_SUMMARY.md", type: "report", description: "MarketForge Flutter app implementation" },
    { title: "MarketForge Completion Report", path: "market_forge_app/COMPLETION_REPORT.md", type: "report", description: "MarketForge Flutter app completion report" },
    { title: "Market Forge README (Root)", path: "market_forge_README.md", type: "readme", description: "Market Forge mobile app documentation" },
    { title: "MarketF Overview", path: "docs/MARKETF_OVERVIEW.md", type: "business", description: "MarketF peer-to-peer marketplace (8% fees)" },
    { title: "MarketF Seller Guide", path: "docs/MARKETF_SELLER_GUIDE.md", type: "guide", description: "Seller documentation" },
    { title: "MarketF Fees", path: "docs/MARKETF_FEES.md", type: "business", description: "Fee structure documentation" },
    { title: "MarketF API", path: "docs/MARKETF_API.md", type: "api", description: "MarketF API reference" },
    { title: "MarketF Amazon Spec", path: "docs/MARKETF_AMAZON_SPEC.md", type: "spec", description: "Amazon SP-API integration" },
    { title: "Amazon Compliance", path: "docs/AMAZON_COMPLIANCE_CHECKLIST.md", type: "legal", description: "Amazon seller compliance checklist" },
    { title: "README MarketF", path: "README_MARKETF.md", type: "readme", description: "MarketF marketplace documentation" },
    { title: "Market Forge App README", path: "market_forge_app/README.md", type: "readme", description: "Market Forge app documentation" },
    { title: "Deployment Guide", path: "DEPLOYMENT.md", type: "guide", description: "MarketForge deployment (Vercel/Railway)" },
    { title: "Security Status", path: "SECURITY.md", type: "legal", description: "Security status and vulnerability fixes" },
    { title: "Security Updates", path: "SECURITY_UPDATE.md", type: "legal", description: "Dependency security updates" },
    { title: "Security Fix Summary", path: "SECURITY_FIX_SUMMARY.md", type: "legal", description: "Security fixes overview" },
    { title: "Messaging System", path: "MESSAGING_SYSTEM_README.md", type: "readme", description: "Unified messaging implementation" },
    { title: "Messaging Features", path: "MESSAGING_FEATURES.md", type: "spec", description: "Messaging feature specification" },
    { title: "Stripe Compliance", path: "docs/STRIPE_COMPLIANCE_CHECKLIST.md", type: "legal", description: "Stripe merchant requirements" },
    { title: "Shipping Integration", path: "docs/SHIPPING_INTEGRATION.md", type: "guide", description: "EasyPost shipping" },
    { title: "Backend README", path: "backend/README.md", type: "readme", description: "FastAPI backend with marketplace endpoints" },
    { title: "Backend Implementation", path: "backend/IMPLEMENTATION_SUMMARY.md", type: "report", description: "MarketForge backend implementation" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Legal Compliance", path: "docs/LEGAL_COMPLIANCE_AUDIT.md", type: "legal", description: "Legal compliance audit" },
    { title: "Implementation Summary", path: "IMPLEMENTATION_SUMMARY.md", type: "report", description: "EmpireBox implementation overview" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
    { title: "Economic Intelligence", path: "docs/ECONOMIC_INTELLIGENCE.md", type: "spec", description: "Financial tracking for marketplace" },
  ],

  // ═══════════════════════════════════════════════
  // CONTRACTORFORGE
  // ═══════════════════════════════════════════════
  contractor: [
    { title: "ContractorForge Module README", path: "modules/contractor/README.md", type: "readme", description: "Contractor and vendor management" },
    { title: "Quick Start (ContractorForge)", path: "QUICKSTART.md", type: "guide", description: "ContractorForge 5-minute Docker setup" },
    { title: "Project Summary", path: "PROJECT_SUMMARY.md", type: "report", description: "ContractorForge project structure" },
    { title: "Visual Mockup Engine", path: "docs/VISUAL_MOCKUP_ENGINE_SPEC.md", type: "spec", description: "Photo-to-product rendering for contractors" },
    { title: "Setup Guide", path: "docs/SETUP.md", type: "guide", description: "ContractorForge setup prerequisites" },
    { title: "Deployment Guide", path: "docs/DEPLOYMENT.md", type: "guide", description: "ContractorForge deployment (Docker, Cloud, AWS)" },
    { title: "API Reference", path: "docs/API.md", type: "api", description: "ContractorForge REST API documentation" },
    { title: "Industry Templates", path: "docs/INDUSTRY_TEMPLATES.md", type: "guide", description: "Industry templates (electrical, landscape)" },
    { title: "Zero to Hero Spec", path: "docs/ZERO_TO_HERO_SPEC.md", type: "spec", description: "Business automation for contractors" },
    { title: "SupportForge README", path: "SUPPORTFORGE_README.md", type: "readme", description: "Customer support for contractors" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // SUPPORTFORGE
  // ═══════════════════════════════════════════════
  support: [
    { title: "SupportForge Integration (Salvaged)", path: "docs/salvaged/SUPPORTFORGE_INTEGRATION.md", type: "architecture", description: "SupportForge integration guide — salvaged" },
    { title: "SupportForge Module README", path: "modules/support/README.md", type: "readme", description: "AI-powered ticket system with KB" },
    { title: "SupportForge README", path: "SUPPORTFORGE_README.md", type: "readme", description: "SupportForge customer support platform" },
    { title: "SupportForge Quick Start", path: "SUPPORTFORGE_QUICKSTART.md", type: "guide", description: "5-minute setup guide" },
    { title: "SupportForge Implementation", path: "SUPPORTFORGE_IMPLEMENTATION.md", type: "report", description: "Feature implementation details" },
    { title: "EmpireAssist Spec", path: "docs/EMPIRE_ASSIST_SPEC.md", type: "spec", description: "Messenger integration for support" },
    { title: "Messaging System", path: "MESSAGING_SYSTEM_README.md", type: "readme", description: "Unified messaging" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "Support desk in delegation plan" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Founders USB Products", path: "founders_usb_installer/docs/PRODUCTS.md", type: "guide", description: "13 bundled products" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // LEADFORGE
  // ═══════════════════════════════════════════════
  lead: [
    { title: "LeadForge Module README", path: "modules/lead/README.md", type: "readme", description: "Lead generation and sales pipeline" },
    { title: "LeadForge Spec", path: "docs/LEADFORGE_SPEC.md", type: "spec", description: "AI lead generation for ContractorForge/LuxeForge" },
    { title: "Messaging Features", path: "MESSAGING_FEATURES.md", type: "spec", description: "Messaging features for lead capture" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // SHIPFORGE
  // ═══════════════════════════════════════════════
  ship: [
    { title: "ShipForge Module README", path: "modules/ship/README.md", type: "readme", description: "Shipping rates, labels, tracking" },
    { title: "Shipping Integration", path: "docs/SHIPPING_INTEGRATION.md", type: "guide", description: "EasyPost shipping integration" },
    { title: "Market Forge App README", path: "market_forge_app/README.md", type: "readme", description: "Marketplace with shipping features" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // FORGECRM
  // ═══════════════════════════════════════════════
  crm: [
    { title: "ForgeCRM Module README", path: "modules/crm/README.md", type: "readme", description: "Customer relationship management" },
    { title: "SupportForge Implementation", path: "SUPPORTFORGE_IMPLEMENTATION.md", type: "report", description: "Customer management shared with SupportForge" },
    { title: "SupportForge Quick Start", path: "SUPPORTFORGE_QUICKSTART.md", type: "guide", description: "Customer support setup" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // RELISTAPP
  // ═══════════════════════════════════════════════
  relist: [
    { title: "RelistApp Module README", path: "modules/relist/README.md", type: "readme", description: "Cross-platform product relisting" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // LLCFACTORY
  // ═══════════════════════════════════════════════
  llc: [
    { title: "LLCFactory Module README", path: "modules/llc/README.md", type: "readme", description: "Business entity formation & compliance" },
    { title: "Zero to Hero Spec", path: "docs/ZERO_TO_HERO_SPEC.md", type: "spec", description: "Business automation (LLC section)" },
    { title: "Zero to Hero v7", path: "ZERO_TO_HERO_SPECIFICATION_Version7.md", type: "spec", description: "Full automation specification" },
    { title: "EmpireBox System README", path: "EMPIREBOX_SYSTEM_README.md", type: "readme", description: "System with LLC factory" },
    { title: "Legal Compliance Audit", path: "docs/LEGAL_COMPLIANCE_AUDIT.md", type: "legal", description: "Legal compliance & IP" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // APOSTAPP
  // ═══════════════════════════════════════════════
  apost: [
    { title: "ApostApp Module README", path: "modules/apost/README.md", type: "readme", description: "Document apostille & authentication" },
    { title: "ApostApp API", path: "backend/app/routers/apostapp.py", type: "code", description: "Apostille service backend with 14 endpoints" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // EMPIREASSIST
  // ═══════════════════════════════════════════════
  assist: [
    ...SHARED_CONTEXT_FILES,
    { title: "MAX Redesign Mockup", path: "docs/recovered/mockups/MAX_Command_Center_Redesign_Mockup_2026-03-07.html", type: "mockup", description: "MAX command center redesign mockup" },
    { title: "EmpireAssist Module README", path: "modules/assist/README.md", type: "readme", description: "AI-powered virtual assistant" },
    { title: "EmpireAssist Spec", path: "docs/EMPIRE_ASSIST_SPEC.md", type: "spec", description: "Messenger integration (Telegram/WhatsApp/SMS)" },
    { title: "MAX Brain Spec", path: "docs/MAX_BRAIN_SPEC.md", type: "spec", description: "Persistent AI memory for assistant" },
    { title: "MAX Response Canvas", path: "docs/MAX_RESPONSE_CANVAS_SPEC.md", type: "spec", description: "MAX interface canvas" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "Desk delegation architecture" },
    { title: "Desk Consolidation Plan", path: "docs/DESK_CONSOLIDATION_PLAN.md", type: "plan", description: "Systems consolidation" },
    { title: "Desks & Task Engine", path: "docs/EMPIRE_DESKS_AND_TASK_ENGINE_PLAN.md", type: "plan", description: "Desk & agent consolidation" },
    { title: "Economic Intelligence", path: "docs/ECONOMIC_INTELLIGENCE.md", type: "spec", description: "Financial tracking for assistant" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
    { title: "Empire Box Agents README", path: "empire_box_agents/README.md", type: "readme", description: "AI agents documentation" },
  ],

  // ═══════════════════════════════════════════════
  // EMPIREPAY
  // ═══════════════════════════════════════════════
  pay: [
    { title: "QB Replacement Audit", path: "docs/QB_REPLACEMENT_AUDIT_2026-03-08.md", type: "audit", description: "QuickBooks replacement — full backend/frontend audit" },
    { title: "EmpirePay Module README", path: "modules/pay/README.md", type: "readme", description: "Payment processing — crypto, invoicing" },
    { title: "Crypto Payments Spec", path: "docs/CRYPTO_PAYMENTS_SPEC.md", type: "spec", description: "Crypto payment integration (SOL, BNB, ADA, ETH)" },
    { title: "Empire Token Spec", path: "docs/EMPIRE_TOKEN_SPEC.md", type: "spec", description: "EMPIRE token (Solana SPL)" },
    { title: "Empire License NFT Spec", path: "docs/EMPIRE_LICENSE_NFT_SPEC.md", type: "spec", description: "NFT license specifications" },
    { title: "Stripe Compliance", path: "docs/STRIPE_COMPLIANCE_CHECKLIST.md", type: "legal", description: "Stripe merchant requirements" },
    { title: "Solana Partnership", path: "docs/SOLANA_PARTNERSHIP.md", type: "business", description: "Solana Seeker phone bundling proposal" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // AMP
  // ═══════════════════════════════════════════════
  amp: [
    { title: "AMP README", path: "amp/README.md", type: "readme", description: "AMP getting started guide" },
    { title: "AMP Module README", path: "modules/amp/README.md", type: "readme", description: "Wellness platform — affirmations, journal, mood" },
    { title: "AMP Build Prompt", path: "docs/AMP_BUILD_PROMPT.md", type: "spec", description: "Build prompt for AMP project" },
    { title: "AI Desk Delegation Plan", path: "docs/AI_DESK_DELEGATION_PLAN.md", type: "plan", description: "AMP desk in delegation plan" },
    { title: "Desk Consolidation Plan", path: "docs/DESK_CONSOLIDATION_PLAN.md", type: "plan", description: "Systems consolidation with AMP" },
    { title: "Implementation Summary", path: "IMPLEMENTATION_SUMMARY.md", type: "report", description: "EmpireBox implementation with AMP" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
  ],

  // ═══════════════════════════════════════════════
  // PLATFORMFORGE
  // ═══════════════════════════════════════════════
  platform: [
    ...SHARED_ARCHITECTURE,
    ...SHARED_SESSION_REPORTS,
    ...SHARED_MOCKUPS,
    ...SHARED_GENESIS,
    ...SHARED_CHAT_ARCHIVES,
    ...SHARED_MERMAID_DIAGRAMS,
    ...SHARED_RECOVERED_MOCKUPS,
    ...SHARED_CONTEXT_FILES,
    ...SHARED_REPORTS,
    { title: "Command Center README", path: "empire-command-center/README.md", type: "readme", description: "Empire Command Center getting started" },
    { title: "EmpireBot Messenger Integration v7", path: "docs_EMPIREBOT_MESSENGER_INTEGRATION_Version7.md", type: "architecture", description: "EmpireBot messenger integration — Version 7" },
    { title: "Tasks & Project Plan v7", path: "docs_TASKS_AND_PROJECT_PLAN_Version7.md", type: "plan", description: "EmpireBox project tasks, research & reminders — Version 7" },
    { title: "Tasks & Project Plan (docs)", path: "docs/tasks_and_project_plan_version7.md", type: "plan", description: "Project tasks and plan — Version 7 (docs copy)" },
    { title: "Empire Box Agents Capabilities", path: "empire_box_agents/CAPABILITIES.md", type: "architecture", description: "Empire Box agents capabilities documentation" },
    { title: "Website Next.js README", path: "website/nextjs/README.md", type: "readme", description: "EmpireBox website — Next.js" },
    { title: "Framer Build Checklist", path: "website/docs/FRAMER_BUILD_CHECKLIST.md", type: "guide", description: "Framer build checklist" },
    { title: "Website Complete Package", path: "website/docs/WEBSITE_COMPLETE_PACKAGE.md", type: "guide", description: "EmpireBox website complete package" },
    { title: "Website URLs & Hosting", path: "website/docs/WEBSITE_URLS.md", type: "guide", description: "Website URLs and hosting info" },
    { title: "Website Security Update", path: "website/SECURITY_UPDATE.md", type: "audit", description: "Security update — Feb 17, 2026" },
    { title: "Website Verification", path: "website/VERIFICATION.md", type: "audit", description: "Website verification summary" },
    { title: "MAX Tasks Feb 23", path: "logs/MAX_TASKS_20260223.md", type: "plan", description: "MAX tasks — February 23, 2026" },
    { title: "PlatformForge Module README", path: "modules/platform/README.md", type: "readme", description: "Infrastructure — Docker, Ollama, module health" },
    { title: "EmpireBox System README", path: "EMPIREBOX_SYSTEM_README.md", type: "readme", description: "Hybrid AI system" },
    { title: "EmpireBox Master Backup", path: "EMPIREBOX_MASTER_BACKUP_2026-02-19_Version7.md", type: "report", description: "Version 7 backup" },
    { title: "Empire Token Spec", path: "docs/EMPIRE_TOKEN_SPEC.md", type: "spec", description: "EMPIRE token" },
    { title: "Empire License NFT", path: "docs/EMPIRE_LICENSE_NFT_SPEC.md", type: "spec", description: "NFT license" },
    { title: "Crypto Payments Spec", path: "docs/CRYPTO_PAYMENTS_SPEC.md", type: "spec", description: "Crypto integration" },
    { title: "EmpireAssist Spec", path: "docs/EMPIRE_ASSIST_SPEC.md", type: "spec", description: "Messenger integration" },
    { title: "MarketF Amazon Spec", path: "docs/MARKETF_AMAZON_SPEC.md", type: "spec", description: "Amazon SP-API" },
    { title: "Zero to Hero Spec", path: "docs/ZERO_TO_HERO_SPEC.md", type: "spec", description: "Business automation" },
    { title: "Zero to Hero v7", path: "ZERO_TO_HERO_SPECIFICATION_Version7.md", type: "spec", description: "Full automation v7" },
    { title: "Economic Implementation", path: "ECONOMIC_IMPLEMENTATION_COMPLETE.md", type: "report", description: "Economic system completion" },
    { title: "API Economic", path: "docs/API_ECONOMIC.md", type: "api", description: "Economic Intelligence API" },
    { title: "Brand Guidelines", path: "docs/BRAND_GUIDELINES.md", type: "guide", description: "Brand colors, typography" },
    { title: "Stripe Compliance", path: "docs/STRIPE_COMPLIANCE_CHECKLIST.md", type: "legal", description: "Stripe requirements" },
    { title: "Legal Compliance", path: "docs/LEGAL_COMPLIANCE_AUDIT.md", type: "legal", description: "Legal audit" },
    { title: "Product Decisions", path: "docs/PRODUCT_DECISIONS.md", type: "plan", description: "Key decisions log" },
    { title: "Website README", path: "website/README.md", type: "readme", description: "Website documentation" },
    { title: "Founders USB Installer", path: "founders_usb_installer/README.md", type: "readme", description: "USB installer overview" },
    { title: "Founders USB Architecture", path: "founders_usb_installer/docs/ARCHITECTURE.md", type: "architecture", description: "System architecture" },
    { title: "EmpireBox Setup", path: "empirebox_setup/README.md", type: "readme", description: "Setup overview" },
    { title: "Enterprise Deploy", path: "empirebox_setup/docs/ENTERPRISE_DEPLOY.md", type: "guide", description: "Bulk deployment guide" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
    { title: "Memory v4", path: "~/Downloads/memory_v4.md", type: "report", description: "MAX brain v4.0" },
    { title: "Architecture Map", path: "~/Empire/data/architecture_map.md", type: "architecture", description: "Full architecture map" },
    { title: "Third Party Licenses", path: "THIRD_PARTY_LICENSES.md", type: "legal", description: "Open source dependencies" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // HARDWARE
  // ═══════════════════════════════════════════════
  hardware: [
    ...SHARED_ARCHITECTURE,
    ...SHARED_GENESIS,
    ...SHARED_MERMAID_DIAGRAMS,
    { title: "Hardware Module README", path: "modules/hardware/README.md", type: "readme", description: "Hardware asset tracking" },
    { title: "Hardware README", path: "hardware/README.md", type: "readme", description: "Hardware documentation" },
    { title: "EmpireBox Hardware Spec", path: "docs/EMPIRE_BOX_HARDWARE_SPEC.md", type: "spec", description: "Physical device specifications" },
    { title: "Hardware Bundles", path: "docs/HARDWARE_BUNDLES.md", type: "business", description: "Three bundle specs ($349-$899)" },
    { title: "Hardware Spec v7", path: "docs_HARDWARE_SPEC_Version7.md", type: "spec", description: "EmpireBox hardware specification — Version 7" },
    { title: "Assembly Guide", path: "hardware/ASSEMBLY_GUIDE.md", type: "guide", description: "Hardware assembly instructions" },
    { title: "Bill of Materials", path: "hardware/BILL_OF_MATERIALS.md", type: "business", description: "Hardware bill of materials" },
    { title: "BIOS Settings", path: "hardware/configs/bios-settings.md", type: "config", description: "Recommended BIOS settings" },
    { title: "Ubuntu Install Guide", path: "hardware/configs/ubuntu-install.md", type: "guide", description: "Ubuntu 24.04 LTS installation guide" },
    { title: "Network Topology", path: "hardware/diagrams/network-topology.md", type: "diagram", description: "Network topology diagram" },
    { title: "Business Build ($599)", path: "hardware/specs/business-build.md", type: "spec", description: "Business build specification — ~$599" },
    { title: "Enterprise Build ($1,299)", path: "hardware/specs/enterprise-build.md", type: "spec", description: "Enterprise build specification — ~$1,299" },
    { title: "Starter Build ($299)", path: "hardware/specs/starter-build.md", type: "spec", description: "Starter build specification — ~$299" },
    { title: "Mini PC Options", path: "hardware/specs/mini-pc-options.md", type: "spec", description: "Recommended mini PCs" },
    { title: "Networking Specs", path: "hardware/specs/networking.md", type: "spec", description: "Networking requirements" },
    { title: "Peripherals", path: "hardware/specs/peripherals.md", type: "spec", description: "Recommended peripherals" },
    { title: "Storage Recommendations", path: "hardware/specs/storage.md", type: "spec", description: "Storage configuration guide" },
    { title: "Quick Start — Founders Unit", path: "founders_usb_installer/QUICK_START.md", type: "guide", description: "Quick start guide for EmpireBox Founders Unit" },
    { title: "Beelink Stability Guide", path: "docs/BEELINK_STABILITY_GUIDE.md", type: "guide", description: "Hardware stability" },
    { title: "Founders USB Installer", path: "founders_usb_installer/README.md", type: "readme", description: "USB installer" },
    { title: "Founders Architecture", path: "founders_usb_installer/docs/ARCHITECTURE.md", type: "architecture", description: "System architecture (Beelink EQR5)" },
    { title: "Founders Security", path: "founders_usb_installer/docs/SECURITY.md", type: "legal", description: "Security documentation" },
    { title: "Voice Setup", path: "founders_usb_installer/docs/VOICE_SETUP.md", type: "guide", description: "Voice interface setup" },
    { title: "Founders Troubleshooting", path: "founders_usb_installer/docs/TROUBLESHOOTING.md", type: "guide", description: "Common issue solutions" },
    { title: "EmpireBox Setup", path: "empirebox_setup/README.md", type: "readme", description: "Setup overview" },
    { title: "Headless Setup", path: "empirebox_setup/docs/HEADLESS_SETUP.md", type: "guide", description: "Headless installation" },
    { title: "USB Config", path: "empirebox_setup/docs/USB_CONFIG.md", type: "config", description: "USB configuration" },
    { title: "Solana Partnership", path: "docs/SOLANA_PARTNERSHIP.md", type: "business", description: "Seeker phone bundling" },
    { title: "Legal Compliance", path: "docs/LEGAL_COMPLIANCE_AUDIT.md", type: "legal", description: "Legal audit" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // SYSTEM
  // ═══════════════════════════════════════════════
  system: [
    ...SHARED_ARCHITECTURE,
    ...SHARED_SESSION_REPORTS,
    ...SHARED_MERMAID_DIAGRAMS,
    ...SHARED_REPORTS,
    { title: "System Module README", path: "modules/system/README.md", type: "readme", description: "System health monitoring" },
    { title: "EmpireBox System README", path: "EMPIREBOX_SYSTEM_README.md", type: "readme", description: "Hybrid AI system" },
    { title: "MAX Response Canvas", path: "docs/MAX_RESPONSE_CANVAS_SPEC.md", type: "spec", description: "MAX interface canvas" },
    { title: "Brand Guidelines", path: "docs/BRAND_GUIDELINES.md", type: "guide", description: "Brand colors, typography" },
    { title: "Known Issues", path: "docs/KNOWN_ISSUES.md", type: "report", description: "Known bugs & workarounds" },
    { title: "Crash Recovery Runbook", path: "docs/CRASH_RECOVERY_RUNBOOK.md", type: "guide", description: "Recovery procedures" },
    { title: "Legal Compliance", path: "docs/LEGAL_COMPLIANCE_AUDIT.md", type: "legal", description: "Legal audit" },
    { title: "Economic Intelligence", path: "docs/ECONOMIC_INTELLIGENCE.md", type: "spec", description: "Financial tracking" },
    { title: "Architecture Map", path: "~/Empire/data/architecture_map.md", type: "architecture", description: "Full architecture map" },
    { title: "Empire Box Agents", path: "empire_box_agents/README.md", type: "readme", description: "AI agents documentation" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // TOKENS & COSTS
  // ═══════════════════════════════════════════════
  tokens: [
    { title: "Tokens Module README", path: "modules/tokens/README.md", type: "readme", description: "AI token usage and cost analytics" },
    { title: "Empire Token Spec", path: "docs/EMPIRE_TOKEN_SPEC.md", type: "spec", description: "EMPIRE token (Solana SPL)" },
    { title: "Empire License NFT Spec", path: "docs/EMPIRE_LICENSE_NFT_SPEC.md", type: "spec", description: "NFT license specifications" },
    { title: "Crypto Payments Spec", path: "docs/CRYPTO_PAYMENTS_SPEC.md", type: "spec", description: "Crypto payment integration" },
    { title: "Economic Implementation", path: "ECONOMIC_IMPLEMENTATION_COMPLETE.md", type: "report", description: "Economic system completion" },
    { title: "API Economic", path: "docs/API_ECONOMIC.md", type: "api", description: "Economic Intelligence API docs" },
    { title: "Economic Intelligence", path: "docs/ECONOMIC_INTELLIGENCE.md", type: "spec", description: "Financial tracking system" },
    { title: "Economic Quick Start", path: "docs/ECONOMIC_QUICK_START.md", type: "guide", description: "Economic system quick start" },
    { title: "MAX Memory v3.1", path: "backend/data/max/memory.md", type: "report", description: "Token tracking data in memory" },
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Product Directory", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "30+ products listing" },
  ],

  // ═══════════════════════════════════════════════
  // VETFORGE
  // ═══════════════════════════════════════════════
  vetforge: [
    { title: "VA Telehealth Compliance", path: "docs/VA_APP_TELEHEALTH.md", type: "compliance", description: "HIPAA compliance framework for veteran telehealth evaluations" },
    { title: "VetForge P&T Presentation", path: "VetForge-PandT.pptx", type: "presentation", description: "Business plan and product overview for P&T disability services" },
    { title: "Product Decisions — VeteranForge", path: "docs/PRODUCT_DECISIONS.md", type: "plan", description: "Strategic decision to offer legal telehealth VA disability services" },
    { title: "Empire Product Directory — VeteranForge", path: "docs/EMPIRE_PRODUCT_DIRECTORY.md", type: "architecture", description: "VeteranForge product specification and compliance summary" },
    { title: "VetForge Module README", path: "modules/vetforge/README.md", type: "readme", description: "VetForge product documentation" },
    ...SHARED_ARCHITECTURE,
    ...SHARED_GENESIS,
    { title: "Ecosystem Directory", path: "docs/ECOSYSTEM.md", type: "architecture", description: "23+ products overview" },
    { title: "Revenue Model", path: "docs/REVENUE_MODEL.md", type: "business", description: "Revenue projections" },
  ],

  // ═══════════════════════════════════════════════
  // PETFORGE
  // ═══════════════════════════════════════════════
  petforge: [
    { title: "VetForge Module README", path: "modules/vetforge/README.md", type: "readme", description: "Veterinary practice management module overview" },
  ],

  // ═══════════════════════════════════════════════
  // VISION
  // ═══════════════════════════════════════════════
  vision: [
    { title: "AI Vision Service", path: "backend/app/services/max/inpaint_service.py", type: "code", description: "Inpainting and mockup generation service" },
    { title: "Vision Router", path: "backend/app/routers/vision.py", type: "code", description: "Vision API endpoints for photo analysis" },
    { title: "Photo Analysis Panel", path: "empire-command-center/app/components/business/vision/PhotoAnalysisPanel.tsx", type: "code", description: "Frontend photo analysis UI component" },
  ],
};

// Helper: get doc count per product
export function getDocCount(product: string): number {
  return DOCS_REGISTRY[product]?.length ?? 0;
}

// Helper: get all unique documents across all products
export function getAllUniqueDocs(): DocEntry[] {
  const seen = new Set<string>();
  const unique: DocEntry[] = [];
  for (const docs of Object.values(DOCS_REGISTRY)) {
    for (const doc of docs) {
      if (!seen.has(doc.path)) {
        seen.add(doc.path);
        unique.push(doc);
      }
    }
  }
  return unique;
}

// Type badge colors
export const DOC_TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  spec: { bg: '#eff6ff', text: '#2563eb' },
  readme: { bg: '#f0fdf4', text: '#16a34a' },
  guide: { bg: '#fefce8', text: '#ca8a04' },
  api: { bg: '#fdf4ff', text: '#a855f7' },
  plan: { bg: '#fff7ed', text: '#ea580c' },
  report: { bg: '#f0f9ff', text: '#0284c7' },
  config: { bg: '#f5f5f5', text: '#737373' },
  audit: { bg: '#fef2f2', text: '#dc2626' },
  session: { bg: '#f5f3ff', text: '#7c3aed' },
  architecture: { bg: '#ecfdf5', text: '#059669' },
  legal: { bg: '#fef2f2', text: '#b91c1c' },
  business: { bg: '#fffbeb', text: '#b45309' },
  pdf: { bg: '#fef2f2', text: '#dc2626' },
  image: { bg: '#f5f3ff', text: '#7c3aed' },
  presentation: { bg: '#fff7ed', text: '#ea580c' },
  mockup: { bg: '#fdf4ff', text: '#a855f7' },
  diagram: { bg: '#ecfdf5', text: '#059669' },
};
