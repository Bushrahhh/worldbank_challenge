# UNMAPPED — Architecture

## The Core Claim: Protocol, Not Product

UNMAPPED is designed like SMTP, not LinkedIn. The data model, API contract, and skills taxonomy are the standard. Country-specific economic reality is a configuration file. A ministry in Dhaka and an NGO in Accra deploy the same binary; they write different YAML files.

This is the difference between building a tool and building infrastructure.

---

## The Skills Passport Packet

A Skills Passport is a portable, verifiable JSON document. It is designed like a network packet: fixed header with identity/provenance metadata, variable payload of skill receipts, integrity checksum. It can travel by QR code, shareable link, WhatsApp forward, or printed paper with a scannable code.

```
┌─────────────────────────────────────────────────────────┐
│                   SKILLS PASSPORT PACKET                │
├─────────────────────────────────────────────────────────┤
│  HEADER                                                 │
│  ├── passport_id    : UUID v4                           │
│  ├── issued_at      : ISO 8601 timestamp                │
│  ├── issuer         : "unmapped/v1"                     │
│  ├── country_iso    : "GHA" | "BGD" | ...               │
│  ├── schema_version : "1.0"                             │
│  └── holder_key     : base64(ed25519 public key)        │
├─────────────────────────────────────────────────────────┤
│  SKILLS PAYLOAD  (array of Skill Receipts)              │
│  Each receipt:                                          │
│  ├── skill_label    : human-readable name               │
│  ├── esco_code      : e.g. "S4.11.2" or "heritage:M1"  │
│  ├── isco_unit      : 4-digit ISCO-08 code              │
│  ├── evidence_type  : "self_report" | "peer_vouched"    │
│  │                    | "employer_verified" | "assessed" │
│  ├── verified_by    : null | phone_hash | employer_id   │
│  ├── confidence     : 0.0–1.0 (LLM extraction score)   │
│  └── timestamp      : ISO 8601                          │
├─────────────────────────────────────────────────────────┤
│  CONTEXT BLOCK                                          │
│  ├── education_level : country-mapped credential level  │
│  ├── country_iso     : matches header                   │
│  └── languages       : ["en", "tw", ...]                │
├─────────────────────────────────────────────────────────┤
│  INTEGRITY                                              │
│  └── signature : base64(ed25519 sig over header+payload)│
└─────────────────────────────────────────────────────────┘
```

---

## System Architecture

```
                        ┌──────────────┐
                        │  YAML Config │  ← the only country-specific file
                        │  ghana.yaml  │
                        │ bangladesh.  │
                        │   yaml       │
                        └──────┬───────┘
                               │ config_loader.py
                               ▼
┌──────────┐         ┌─────────────────┐         ┌──────────────────┐
│ Telegram │◄───────►│                 │◄────────►│   Data Adapters  │
│   Bot    │         │   FastAPI App   │         │  ┌─ ILOSTAT       │
│          │         │                 │         │  ├─ World Bank WDI│
│ Voice in │         │  Module 1:      │         │  ├─ ESCO          │
│ Text in  │         │  Skills Signal  │         │  ├─ O*NET         │
│          │         │                 │         │  └─ Wittgenstein  │
│ Passport │         │  Module 2:      │         └──────────────────┘
│  view    │         │  Readiness Lens │
└──────────┘         │                 │         ┌──────────────────┐
                     │  Module 3:      │◄────────►│   Groq API       │
┌──────────┐         │  Matching       │         │  Llama 3.1 70B   │
│Policy    │◄───────►│                 │         │  Whisper STT     │
│Dashboard │         └────────┬────────┘         └──────────────────┘
│ React    │                  │
└──────────┘         ┌────────▼────────┐
                     │   SQLite DB     │
                     │  (Postgres in   │
                     │   production)   │
                     └─────────────────┘
```

---

## The Country Config Layer — How It Works

Every piece of country-specific knowledge lives in one place:

```
ACTIVE_COUNTRY=ghana → loads configs/ghana.yaml
ACTIVE_COUNTRY=bangladesh → loads configs/bangladesh.yaml
```

The `config_loader.py` singleton reads the YAML at startup and exposes it globally. No module ever contains a country name, currency, or credential level in its source code.

This means:

| What changes | Where it lives |
|---|---|
| Currency symbol | `country.currency` in YAML |
| Education credential names | `education_taxonomy.levels` in YAML |
| Automation calibration factors | `automation_calibration.*` in YAML |
| Language scripts | `language.secondary` in YAML |
| Informal sector share | `labor_market.informal_sector_share` in YAML |
| UI strings | `language.ui_strings_path` → `locales/{code}/` |
| Data gap disclosures | `data_gaps` list in YAML |

**Adding a new country takes one YAML file. Zero code changes.**

---

## Data Flow: Skills Interview → Skills Passport

```
User speaks/types
       │
       ▼
[Voice] Groq Whisper STT → transcript
       │
       ▼
[LLM Interview] Groq Llama 3.1 70B
  - behavioral questions
  - extracts competency claims
  - maps to ESCO taxonomy
  - scores confidence
       │
       ▼
[Heritage Skills Layer]
  - matches against ~20 curated LMIC-specific entries
  - mobile money fluency, repair-not-replace, community trust, etc.
       │
       ▼
[Skills Receipts Engine]
  - creates one receipt per skill claim
  - {skill, esco_code, evidence_type, confidence, timestamp}
       │
       ▼
[Peer Vouching] (async)
  - customer texts short code → SMS webhook
  - receipt evidence_type upgrades: self_report → peer_vouched
       │
       ▼
[Passport Assembly]
  - signs packet with ed25519 keypair
  - stores in SQLite
  - generates QR code
  - returns shareable link
```

---

## Data Flow: Skills Profile → Readiness Assessment

```
Skills Passport
       │
       ▼
[Frey-Osborne Lookup]
  - baseline automation probability from CSV
  - per ISCO-08 occupation code
       │
       ▼
[Calibration Layer] ← the headline contribution
  - infrastructure_adjustment (ITU digital dev index)
  - informal_economy_adjustment (ILO task indices)
  - country-specific factors from YAML
  - OUTPUT: "Frey-Osborne says 89%. In {country}, it's {calibrated}%."
       │
       ▼
[Wittgenstein Projector]
  - three paths: do nothing / path A / path B
  - uses 2025-2035 education-scenario data
  - adds regret panel: what if this existed in 2020?
       │
       ▼
[Constellation Generator]
  - current skills → lit stars
  - adjacent reachable skills → glowing nearby stars
  - automation-risk skills → dimming stars
  - outputs SVG data
```

---

## Data Flow: Profile → Opportunity Match

```
Skills Passport + Country Config
       │
       ▼
[Honest Matcher]
  - cosine similarity on ESCO skill vectors
  - distance scoring: training months, income multiple, geo proximity
  - never returns a match without showing the tradeoffs
       │
       ├──► [Wrong Job Filter]
       │     - 1 in 10 results flagged as "wrong for you"
       │     - LLM explains why
       │     - builds user trust
       │
       ├──► [Blind Match Layer]
       │     - employer view strips name/gender/age
       │     - reveal only on explicit employer request
       │
       └──► [Econ Signals]
             - ILOSTAT: live wage floor for occupation + country
             - World Bank WDI: sector employment growth %
             - both in local currency
             - both with source tooltip
```

---

## The Policymaker View

The policymaker dashboard is not designed to comfort. It is designed to create urgency.

```
┌─────────────────────────────────────────────────────────┐
│                  DISTRICT DASHBOARD                     │
│  [47,000 people in your district are Amara]             │
│  [Current policy reaches: 2,300]                        │
│  [Will be displaced by 2030 if nothing changes: 12,000] │
│  [Cost of inaction (est. lost GDP): $XXM]               │
│                                                         │
│  Most common skills gap: ████████████ solar tech        │
│  Fastest growing sector:  ██████ agri-services          │
│  Largest training gap:    ████████████████ digital lit  │
└─────────────────────────────────────────────────────────┘
```

Every number has a source citation. Every projection has a confidence interval. Every data gap is disclosed.

---

## What This Is Not

- Not a LinkedIn. Users do not build public profiles for employer browsing.
- Not a job board. Matching is skills-first, opportunity-second.
- Not a certificate repository. Paper credentials are not the signal; demonstrated competency is.
- Not a two-sided marketplace. Youth-side excellence now; employer-side is a future extension if the protocol succeeds.

---

## Protocol Spec

See [docs/protocol_spec.md](docs/protocol_spec.md) for the full UNMAPPED Skills Passport specification, including the canonical JSON schema, the signing algorithm, and the cross-border verification flow.
