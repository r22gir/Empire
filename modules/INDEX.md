# Empire Ecosystem — Product Index

> Auto-generated inventory of all 23 ecosystem products.
> Backend: FastAPI (port 8000) | Frontend: Next.js Command Center (port 3009)

## Command

| Product | Status | Backend Router | Frontend Screen | Port |
|---------|--------|---------------|-----------------|------|
| [Owner's Desk](owner/) | Active | `max/router.py` (39 endpoints) | `ChatScreen.tsx`, `DesksScreen.tsx`, `InboxScreen.tsx` | 3009 |

## Businesses

| Product | Status | Backend Router | Frontend Screen | Port |
|---------|--------|---------------|-----------------|------|
| [Empire Workroom](workroom/) | Active | `quotes.py`, `jobs.py`, `finance.py`, `inventory.py` | `WorkroomPage.tsx` | 3009 |
| [WoodCraft](craft/) | Active | `craftforge.py` (15+ endpoints) | `CraftForgePage.tsx` | 3009 |
| [LuxeForge](luxe/) | Active | `intake_auth.py` (17 endpoints), `luxeforge_measurements.py` | `LuxeForgePage.tsx`, `/intake/*` | 3009 |

## Ecosystem

| Product | Status | Backend Router | Frontend Screen |
|---------|--------|---------------|-----------------|
| [SocialForge](social/) | Dev | `socialforge.py` (13+ endpoints) | `SocialForgePage.tsx` |
| [OpenClaw](openclaw/) | Active | — (standalone Ollama UI) | `ChatScreen.tsx` |
| [RecoveryForge](recovery/) | Active | — | `EcosystemProductPage.tsx` |
| [MarketForge](market/) | Dev | `marketplace/*.py`, `listings.py` | `EcosystemProductPage.tsx` |
| [ContractorForge](contractor/) | Dev | `contacts.py` | `EcosystemProductPage.tsx` |
| [SupportForge](support/) | Dev | `supportforge_*.py` (4 routers, 24+ endpoints) | `TicketsPage.tsx` |
| [LeadForge](lead/) | Dev | — | `EcosystemProductPage.tsx` |
| [ShipForge](ship/) | Dev | `shipping.py` | `ShippingPage.tsx` |
| [ForgeCRM](crm/) | Dev | `customer_mgmt.py` | `CustomerList.tsx`, `CustomerDetail.tsx` |
| [RelistApp](relist/) | Planned | `listings.py`, `preorders.py` | `EcosystemProductPage.tsx` |
| [LLCFactory](llc/) | Dev | — | `EcosystemProductPage.tsx` |
| [ApostApp](apost/) | Planned | — | `EcosystemProductPage.tsx` |
| [EmpireAssist](assist/) | Dev | — | `EcosystemProductPage.tsx` |
| [EmpirePay](pay/) | Dev | `crypto_payments.py` | `EcosystemProductPage.tsx` |
| [AMP](amp/) | Active | `amp.py` (JWT auth, SQLite) | `/amp/*` (landing, dashboard, auth) |

## Infrastructure

| Product | Status | Backend Router | Frontend Screen |
|---------|--------|---------------|-----------------|
| [PlatformForge](platform/) | Active | `docker_manager.py`, `ollama_manager.py` | `PlatformPage.tsx` |
| [Hardware](hardware/) | Dev | — | `EcosystemProductPage.tsx` |
| [System](system/) | Active | `system_monitor.py` | `SystemReportScreen.tsx` |
| [Tokens & Costs](tokens/) | Active | `costs.py` (6+ endpoints) | `CostTracker.tsx` |

## Stats

- **Total Products:** 23
- **Active:** 10 | **Dev:** 11 | **Planned:** 2
- **Backend Routers:** 47 files, 200+ endpoints
- **Frontend Screens:** 16 dedicated + generic fallback
