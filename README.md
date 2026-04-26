# UNMAPPED
### Open Skills Infrastructure for the AI Age

> A World Bank Youth Summit Challenge 05 submission  
> In collaboration with MIT Club of Northern California & MIT Club of Germany

---

Amara is 22. She lives outside Accra. She has a secondary school certificate, has run a phone repair business since age 17, speaks three languages, and taught herself to code from YouTube on a shared mobile connection.

**The formal economy cannot see her.**

UNMAPPED is the infrastructure layer that makes her visible — on her own terms.

---

## Design Philosophy

These six principles are non-negotiable. Every line of code, every UI string, every data decision is held against them.

### 1. Honesty over optimism
This is not "find your dream job." This is "know exactly where you stand, and exactly what's reachable." We never tell a user they could be a software engineer in 6 months when the real answer is solar technician in 6 months.

### 2. Dignity test
Every screen, every string, every error message must pass the Amara test: would she feel respected reading this, or pitied? Never use the words "low-skilled," "vulnerable," "beneficiary," or "disadvantaged" in user-facing copy. She is unmapped, not unworthy.

### 3. Protocol, not product
Build it like SMTP, not LinkedIn. Country-specific parameters live in YAML config files, never hardcoded. A new country = a new YAML file, zero code changes.

### 4. Designed for constraint
Assume $30 Android phone, 2G connection, shared device, intermittent power, low literacy in some users. If it doesn't work in those conditions, it doesn't ship.

### 5. Show the data, cite the source
Every number on screen has a tooltip showing its source (e.g. "ILOSTAT 2024"). No magic. No black boxes.

### 6. Honest about limits
Where data is missing or imperfect, say so. The Frey-Osborne calibration layer is a feature, not a footnote.

---

## What UNMAPPED Does

Three modules, all functional, all integrated.

### Module 1 — Skills Signal Engine
A conversational AI interview (Telegram bot + web fallback) that extracts competencies from lived experience — not a form, a conversation. Maps to ESCO + ISCO-08 + O*NET. Outputs a portable **Skills Passport** the user owns, shareable via QR code. Includes a **Heritage Skills** tier for competencies LMIC employers value but global taxonomies miss.

### Module 2 — AI Readiness & Displacement Risk Lens
Honest automation risk assessment calibrated to local context. Frey-Osborne says Amara's phone repair work is 89% automatable — that's US data. In Accra, it's 12%. The calibration math is shown transparently. Includes the **Automation Weather Report**, the **Time Machine 2035** four-panel view, and the **Skills Constellation Map**.

### Module 3 — Opportunity Matching & Econometric Dashboard
Distance-aware matching that shows every opportunity with honest tradeoffs: training time, income multiple, openings within 30km. Includes the **Wrong Job** feature (trust-building), **blind matching** for employers (discrimination-reducing), and live ILOSTAT + World Bank WDI econometric signals. Dual interface: youth view and a policymaker view designed to create urgency, not comfort.

---

## The Key Demo Moment

```
$ ACTIVE_COUNTRY=ghana python backend/main.py   # demo starts
$ ACTIVE_COUNTRY=bangladesh python backend/main.py   # live swap, zero code changes
```

New country = new YAML. That's the whole infrastructure claim.

---

## Stack

| Layer | Demo | Production |
|-------|------|------------|
| Backend | FastAPI (Python 3.11) | Same |
| LLM | Groq API — Llama 3.1 70B | Ollama Mistral 7B (local) |
| Voice | Whisper via Groq | Whisper local |
| User channel | Telegram Bot | Same + USSD fallback |
| Storage | SQLite | PostgreSQL |
| Frontend | Telegram Web App + React | Same |
| Cost | $0 | ~$5–20/month for NGO deployment |

---

## Data Sources (all free, all cited in-UI)

- **ILO ILOSTAT REST API** — wage floors, employment by sector
- **World Bank WDI REST API** — sector growth, education returns
- **ESCO REST API** — skill taxonomy, occupation codes
- **O*NET REST API** — task-level occupation data
- **Frey & Osborne (2013/2017)** — baseline automation probability scores
- **Wittgenstein Centre 2025–2035 projections** — education-scenario forecasts
- **ITU Digital Development indicators** — infrastructure adjustment factors

---

## Quick Start

```bash
git clone <repo>
cd unmapped
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN

# Run with Ghana config (default)
ACTIVE_COUNTRY=ghana uvicorn backend.main:app --reload

# Swap to Bangladesh — no code changes
ACTIVE_COUNTRY=bangladesh uvicorn backend.main:app --reload
```

---

## Project Structure

```
unmapped/
├── configs/           country YAML configs — the only thing that changes per country
├── data/              cached datasets (Frey-Osborne, Wittgenstein, ESCO)
├── locales/           UI strings by country/language
├── backend/           FastAPI application
│   ├── modules/       three core modules
│   ├── adapters/      data source connectors (ILOSTAT, WDI, ESCO, O*NET)
│   ├── models/        Pydantic schemas
│   └── api/           REST endpoints
├── telegram_bot/      primary user channel
├── policymaker_dashboard/  React + Tailwind (the "uncomfortable" view)
├── tests/
└── docs/              one-pager, pitch deck, protocol spec
```

---

*UNMAPPED is a protocol, not a product. The goal is that any NGO, government ministry, or community navigator in any LMIC can deploy it with a YAML file and a $5/month server. The infrastructure for human capability should be open.*
