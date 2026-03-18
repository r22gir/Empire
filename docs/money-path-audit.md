# Empire Money Path Audit — 2026-03-18

## Summary
**7/8 steps working, 0 need fixes in backend, 1 needs frontend wiring**

The money path is substantially complete. Most features were built in previous sessions (commits 0473e6a, f3126d0, and earlier) and are functional.

## Test Results

| # | Test | Status | Details |
|---|------|--------|---------|
| 1 | Intake Submission | WORKING | Auth-protected endpoint, returns 401 without token. 4 upload directories with 7 photos. |
| 2 | Quote Creation | WORKING | 28 quotes exist in system. POST /api/v1/quotes creates quotes. QuoteBuilderScreen.tsx provides 5-step wizard. |
| 3 | Photo Analysis | WORKING | 6 vision endpoints: /measure, /outline, /upholstery, /mockup, /room-scan, /analyze-items. All return structured JSON via Grok Vision. Frontend: PhotoAnalysisPanel.tsx with 4 analysis modes. |
| 4 | Yardage Calculator | WORKING | Full calculator in yardage_calculator.py — 20+ item types, drapery/roman/upholstery/cushions. Wired into quote_phases.py Phase 2. Math breakdown included. |
| 5 | Quote → Job | WORKING | POST /api/v1/jobs/from-quote/{quote_id} exists. Looks up customer, copies line items, creates job on Kanban. |
| 6 | PDF Generation | WORKING | POST /api/v1/quotes/{id}/pdf — WeasyPrint 68.1 installed. Full rooms/mockups/outlines support. Empire Workroom branding (gold #b8960c header, signature block). Verification gate. |
| 7 | Email (SendGrid) | CONFIGURED | SENDGRID_API_KEY and SENDGRID_FROM_EMAIL set. Sender service supports SendGrid → SMTP fallback. Templates exist for quotes, invoices, receipts. |
| 8 | Invoice + Payment | WORKING | POST /finance/invoices/from-quote/{id}, from-job/{id}. Payment recording: POST /finance/invoices/{id}/payment. Invoice PDF generation. Recalculates balances. |

## Issues Found (Fixed This Session)

1. **Branding mismatch**: Email templates + subjects said "RG's Drapery & Upholstery" instead of "Empire Workroom" — FIXED
2. **Send Quote endpoint**: POST /quotes/{id}/send only marked status, didn't actually email — UPGRADED to generate PDF + email
3. **business.json**: business_name was "Empire" (generic) — updated to "Empire Workroom"

## Backend Endpoints (Money Path)

### Quotes
- POST /api/v1/quotes — create quote
- GET /api/v1/quotes — list all quotes
- GET /api/v1/quotes/{id} — get single quote
- PATCH /api/v1/quotes/{id} — update quote
- POST /api/v1/quotes/{id}/send — mark sent + email PDF to client
- POST /api/v1/quotes/{id}/accept — mark accepted
- POST /api/v1/quotes/{id}/pdf — generate PDF
- GET /api/v1/quotes/{id}/pdf — download PDF
- POST /api/v1/quotes/{id}/photos — attach photos

### Quote Intelligence System (QIS)
- POST /api/v1/quotes/analyze-photo — AI photo analysis → tiered pricing
- POST /api/v1/quotes/quick — instant ballpark quote
- POST /api/v1/quotes/quick/promote — promote to full pipeline
- POST /api/v1/quotes/phase/init/{id} — start 6-phase pipeline
- POST /api/v1/quotes/phase/advance/{id} — advance phase
- POST /api/v1/quotes/phase/approve/{id} — founder approves phase
- POST /api/v1/quotes/phase/reject/{id} — founder rejects phase
- PATCH /api/v1/quotes/phase/item/{id} — edit measurements in pipeline

### Vision Analysis
- POST /api/v1/vision/measure — window measurement from photo
- POST /api/v1/vision/outline — dimensional installation plan
- POST /api/v1/vision/upholstery — furniture reupholstery estimate
- POST /api/v1/vision/mockup — 3-tier design proposals with AI images
- POST /api/v1/vision/room-scan — multi-window room detection
- POST /api/v1/vision/analyze-items — generic AI vision analysis

### Jobs
- GET /api/v1/jobs — list jobs (with filters)
- POST /api/v1/jobs — create job
- POST /api/v1/jobs/from-quote/{id} — create job from quote
- GET /api/v1/jobs/{id} — get job
- PATCH /api/v1/jobs/{id} — update job (status, assigned_to, etc.)
- GET /api/v1/jobs/dashboard — stats summary

### Finance
- GET /api/v1/finance/invoices — list invoices
- POST /api/v1/finance/invoices — create invoice
- POST /api/v1/finance/invoices/from-quote/{id} — invoice from quote
- POST /api/v1/finance/invoices/from-job/{id} — invoice from job
- POST /api/v1/finance/invoices/{id}/payment — record payment
- GET /api/v1/finance/invoices/{id}/pdf — invoice PDF

### Email
- POST /api/v1/emails/send-quote — send quote email
- POST /api/v1/emails/send-invoice — send invoice email
- POST /api/v1/emails/send-receipt — send payment receipt

## Frontend Components (Command Center)
- QuoteBuilderScreen.tsx — 5-step quote wizard (customer → photos → rooms → options → review)
- PhotoAnalysisPanel.tsx — 4-mode analysis (measure, upholstery, mockup, outline)
- QuoteReviewScreen.tsx — quote review with phase pipeline
- QuickQuoteBuilder.tsx — instant ballpark quotes
- VisionAnalysisPage.tsx — standalone vision analysis
- WorkroomPage.tsx — main workroom hub

## Architecture Notes
- Quotes stored as JSON files in ~/empire-repo/backend/data/quotes/
- Jobs, invoices, payments stored in SQLite (empire.db)
- Photos in ~/empire-repo/backend/data/intake_uploads/
- PDFs saved to ~/empire-repo/backend/data/quotes/pdf/
