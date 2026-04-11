# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LeaseManager** (previously "Rent Control") is a comprehensive commercial lease management ERP system for Chile. The project consolidates requirements from 26 PRD iterations into a unified implementation plan.

### Core Purpose
Automate and centralize commercial property lease administration including:
- Rent calculation with UF conversion and property-code identification
- Automated notifications (Email/WhatsApp)
- Bank reconciliation via API (Banco de Chile)
- Electronic invoicing (direct SII integration)
- Full accounting with AI-powered tax optimization
- Automated property marketing (Yapo, Portal Inmobiliario)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.0 + Django Ninja |
| Database | PostgreSQL 16 + pgvector |
| Task Queue | Redis + Celery |
| Frontend | React 18 + TypeScript + Vite |
| State Management | TanStack Query + Zustand |
| UI | shadcn/ui + Tailwind CSS |
| Email | Gmail API |
| AI | LangChain/LlamaIndex + OpenAI/Claude/Gemini |

## Development Principles

### Absolute Rule: No Temporary Solutions
This principle is **non-negotiable** throughout all development:
- Never implement patches or quick fixes
- Build everything correctly from the start
- If it's not complete and correct, it doesn't ship
- No TODO/FIXME comments - code must be production-ready from commit 1

### Commits
- Frequent commits with descriptive messages
- Explain WHAT changed, WHY, and HOW it affects the system
- Each commit must be production-ready

## Key Business Rules

### Contracts
- Contracts only start on day 1 of a month, end on last day
- Minimum amount: $1,000 CLP absolute
- **Contracts EXTEND, never duplicate** - renewals add PeriodoContractual to existing contract
- Contract ID remains immutable for its entire lifecycle

### Rent Calculation (Critical Logic)
1. Get Monto Contractual Bruto from active PeriodoContractual
2. Convert to CLP using UF value from day 1 (sources: Banco Central → CMF → MiIndicador)
3. Apply any AjusteContrato adjustments
4. **Truncate** decimals (no rounding)
5. Replace last 3 digits with property code (001-999)
6. Result is `monto_calculado_clp` for reconciliation

### Property Codes
- Unique 3-digit code per bank account (001-999)
- Maximum 999 properties per bank account
- Code is embedded in final rent amount for automatic reconciliation

### Notifications
- 100% configurable per contract (day + channel)
- Default days: 1, 3, 5, 10, 15, 20, 25
- Channels: Email (Gmail API), WhatsApp (Twilio)

## Data Model Core Entities

- `Socio` - Partners with participation percentages
- `Empresa` - Companies (must have bank account, sum of socios = 100%)
- `Propiedad` - Properties (belong to Empresa OR Socio community at 100%)
- `Arrendatario` - Tenants (Persona Natural or Empresa)
- `Contrato` - Contracts with guarantee lifecycle
- `PeriodoContractual` - Contract periods with reajuste calculations
- `PagoMensual` - Monthly payment records
- `AjusteContrato` - Discounts/surcharges on rent

### Validation Rules
- Socio percentages in Empresa must sum to 100%
- If Property has no empresa_propietaria, Socio percentages must sum to 100%
- Only ONE active contract per property at a time
- `porcentaje_reajuste_maestro` stored as user-entered value (e.g., 3 for 3%), divided by 100 for calculations

## API Integrations

- **Bank**: Banco de Chile API only (no web scraping)
- **SII**: Direct API for invoicing, F29, F22, DDJJ
- **UF Value**: Banco Central → CMF → MiIndicador (fallback chain)
- **Portals**: Yapo, Portal Inmobiliario APIs (verify availability)
- **WhatsApp**: Twilio Business

## Development Phases

### Phase 1: MVP - Core Operations
- Complete CRUDs with all validations
- Dual Gmail system (per account or per company)
- Tenant flow: email → form → approval
- Contract: creation → PDF → approval → signature → notary
- PagoMensual calculation and configurable notifications
- Bank reconciliation (exact matches only)

### Phase 2: Intelligence & Automation
- AI-powered reconciliation
- Advanced contracts (extensions)
- SII electronic invoicing
- Full notification flexibility

### Phase 3: Advanced Features
- Automated property marketing
- Complete accounting
- Advanced debt management

### Phase 4: AI & Optimization
- Conversational AI agent
- Predictive analytics

### Phase 5: Intelligent Accounting
- Automated F29 (monthly) and F22 (annual)
- Regulatory AI monitoring SII changes
- Tax optimization

## Acceptance Criteria (All Features)

- Functions correctly in ALL cases
- Handles ALL possible errors
- Automated tests > 95% coverage
- Complete documentation
- Verified optimal performance
- Audited security
- Polished UX without exceptions

## Localization

- Language: Spanish (Chile)
- Date format: dd/mm/yyyy
- Timezone: America/Santiago
- Currency: CLP (Chilean Pesos) and UF (Unidad de Fomento)

## User Roles

- **Administrador Global**: Full access, creates all users
- **Contadora**: Read-only access to financial data (audit role after Phase 5)
- **Socio**: Read-only filtered view of own participations

## Environment Variables Required

```
# Database
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# Django
SECRET_KEY, ALLOWED_HOSTS, DEBUG

# Redis/Celery
REDIS_URL, CELERY_BROKER_URL

# Bank APIs
BANCO_CHILE_API_KEY, BANCO_CHILE_API_SECRET, BANCO_CHILE_CLIENT_ID

# Gmail
GMAIL_API_CLIENT_ID, GMAIL_API_CLIENT_SECRET, GMAIL_API_REFRESH_TOKEN

# UF APIs
API_UF_BANCO_CENTRAL, API_UF_CMF, API_UF_MIINDICADOR

# SII
SII_API_KEY, SII_API_SECRET, SII_CERT_PATH, SII_CERT_PASSWORD, SII_AMBIENTE

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM

# AI
OPENAI_API_KEY, CLAUDE_API_KEY, GEMINI_API_KEY

# Security
ENCRYPTION_SALT

# Storage
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME

# Timezone
TZ='America/Santiago'
```

## PRD Reference

The `analizar/` folder contains 26 PRD versions (prd1.txt through prd26.txt). The root `prd.txt` contains the consolidation methodology. Key references:
- **prd1.txt**: Original "Rent Control" specification with detailed data models
- **prd26.txt**: Most evolved "LeaseManager" with AI features and no-temp-solutions principle


