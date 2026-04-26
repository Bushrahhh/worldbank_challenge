# UNMAPPED Protocol Specification v0.1
### Open Skills Infrastructure for the AI Age

*World Bank Youth Summit Challenge 05 — Technical Specification*

---

## 1. Design Philosophy: Why a Protocol, Not a Product

SMTP does not care which email client you use.  
TCP/IP does not care which application runs on top.  
HTTP does not care which browser renders the response.

**UNMAPPED does not care which NGO, government platform, employer marketplace, or training registry sits on top.**

The insight is that the global skills recognition problem is not a product problem. LinkedIn exists. SFIA exists. ILO credential frameworks exist. The problem is that none of them were designed for Amara — 22, outside Accra, secondary school certificate, five years of phone repair expertise, three languages, no CV, no LinkedIn, no verifiable credential of any kind.

The gap is not a missing app. The gap is a missing **layer** — a standardized, portable, open packet format for human capability that works on any device, in any country, in any language, with or without internet connectivity.

UNMAPPED is that layer.

---

## 2. The Skills Passport Packet

Every user interaction produces a **Skills Passport** — a signed, portable, self-sovereign data packet that the user owns and controls.

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNMAPPED SKILLS PASSPORT v0.1                │
├─────────────────────────────────────────────────────────────────┤
│  HEADER                                                         │
│  ┌─────────────────┬────────────────────────────────────────┐  │
│  │ schema_version  │ "unmapped/passport/v0.1"               │  │
│  │ issued_at       │ ISO 8601 timestamp                     │  │
│  │ issuing_system  │ "unmapped-oss"                         │  │
│  │ country_context │ "GHA" | "BGD" | ISO 3166-1 alpha-3    │  │
│  └─────────────────┴────────────────────────────────────────┘  │
│                                                                 │
│  HOLDER                                                         │
│  ┌─────────────────┬────────────────────────────────────────┐  │
│  │ holder_id       │ opaque UUID (not PII)                  │  │
│  │ public_key      │ Ed25519 public key (base64)            │  │
│  │ display_name    │ holder-chosen, optional                │  │
│  └─────────────────┴────────────────────────────────────────┘  │
│                                                                 │
│  SKILL RECEIPTS  (one per demonstrated competency)             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Receipt {                                              │   │
│  │    skill_label:      "Phone screen repair"              │   │
│  │    esco_uri:         "http://data.europa.eu/esco/..."   │   │
│  │    esco_code:        "S5.6.0"                           │   │
│  │    isco_code:        "7422"                             │   │
│  │    onet_soc:         "49-2022.00" (optional)            │   │
│  │    evidence_type:    self_report | peer_vouched |        │   │
│  │                      assessed | employer_verified        │   │
│  │    confidence:       0.0 – 1.0                          │   │
│  │    verified_by:      null | phone_hash | employer_id    │   │
│  │    is_heritage:      bool                               │   │
│  │    heritage_id:      "mobile_money" | null              │   │
│  │    evidence_text:    free-text (optional, holder-owned) │   │
│  │    timestamp:        ISO 8601                           │   │
│  │    receipt_hash:     SHA-256 of above fields            │   │
│  │  }                                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  CONTEXT (country-specific, from YAML config)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  automation_calibration: { baseline, infra_adj, ... }  │   │
│  │  data_gaps: [ { id, description, severity } ... ]      │   │
│  │  education_taxonomy: { levels, credential_map }        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  INTEGRITY                                                      │
│  ┌─────────────────┬────────────────────────────────────────┐  │
│  │ signature       │ Ed25519 sig over canonical JSON payload │  │
│  │ signed_at       │ ISO 8601                               │  │
│  │ signing_key_id  │ issuing system key identifier         │  │
│  └─────────────────┴────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Evidence Type Lifecycle

Evidence types form a one-way upgrade chain. Confidence can only increase.

```
self_report  ──vouch_confirmed──▶  peer_vouched
                                        │
                                 employer_review
                                        │
                                        ▼
                               employer_verified
                                        │
                               (highest trust tier)
```

No mechanism exists to downgrade evidence type. A receipt that has been employer-verified cannot revert to self-report. This is intentional — it creates a ratchet of trust.

### 2.2 Heritage Skill Receipt

Heritage Skills are a first-class receipt type. They use the same structure but include a `heritage_id` that maps to the UNMAPPED Heritage Skills Registry.

The Registry v0.1 contains 20 entries, curated for Sub-Saharan Africa and South Asia. These are competencies that ESCO, O*NET, and ISCO either miss entirely or undervalue for informal LMIC contexts:

| heritage_id | Label | LMIC employer value | ESCO equivalent |
|---|---|---|---|
| `mobile_money` | Mobile money fluency | Critical | Partial: S4.1.1 |
| `repair_mindset` | Repair-not-replace mindset | High | None |
| `multilingual_service` | Multilingual customer service | High | Partial: S3.2.2 |
| `community_trust` | Community trust network | Critical | None |
| `informal_trading` | Informal market trading | High | Partial: S5.2.0 |
| `solar_maintenance` | Off-grid solar maintenance | High | None |
| `feature_phone_ops` | Feature phone operations fluency | Medium | None |
| `oral_instruction` | Oral instruction delivery | Medium | Partial |
| `supply_chain_nav` | Informal supply chain navigation | High | None |
| `peer_training` | Peer-to-peer skills training | Medium | Partial |
| `cash_float_mgmt` | Cash float management | High | None |
| `climate_adaptation` | Local climate adaptation knowledge | Medium | None |
| `cross_border_trade` | Cross-border informal trade | High | None |
| `agri_tech_basic` | Smallholder agri-tech adoption | Medium | None |
| `remittance_ops` | Remittance operations | Medium | None |
| `conflict_mediation` | Community conflict mediation | High | None |
| `digital_literacy_mobile` | Mobile-first digital literacy | High | Partial |
| `waste_sorting` | Waste sorting and material recovery | Medium | None |
| `market_price_intel` | Real-time market price intelligence | Medium | None |
| `shared_device_mgmt` | Shared device and account management | Low | None |

---

## 3. The Calibration Packet

Every automation risk score carries a full calibration chain. No number is presented without its derivation.

```
┌─────────────────────────────────────────────────────────────────┐
│              UNMAPPED CALIBRATION PACKET v0.1                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT                                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  isco_code:          "7422"                            │    │
│  │  occupation_label:   "Electronics mechanics"           │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  STEP 1 — Frey-Osborne Baseline                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  fo_probability:     0.89                              │    │
│  │  source:             "Frey & Osborne 2013/2017"        │    │
│  │  geography:          "United States"                   │    │
│  │  note:               "US occupational task composition"│    │
│  └────────────────────────────────────────────────────────┘    │
│              ×                                                  │
│  STEP 2 — Infrastructure Adjustment                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  factor:             0.70  (Ghana) | 0.65 (Bangladesh) │    │
│  │  source:             "ITU Digital Development Index"   │    │
│  │  rationale:          "Lower digital infrastructure     │    │
│  │                       → lower realized automation rate"│    │
│  └────────────────────────────────────────────────────────┘    │
│              ×                                                  │
│  STEP 3 — Informal Economy Adjustment                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  factor:             0.60  (Ghana) | 0.55 (Bangladesh) │    │
│  │  source:             "ILO Future of Work task indices" │    │
│  │  rationale:          "Informal task bundles differ from│    │
│  │                       formal equivalents — more manual,│    │
│  │                       more relational, less routine"   │    │
│  └────────────────────────────────────────────────────────┘    │
│              =                                                  │
│  OUTPUT                                                         │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  calibrated_risk:    0.89 × 0.70 × 0.60 = 0.37 (GHA) │    │
│  │                      0.89 × 0.65 × 0.55 = 0.32 (BGD) │    │
│  │  risk_tier:          "medium"                          │    │
│  │  weather_icon:       "⛅ Partly cloudy"               │    │
│  │  horizon_years:      "5–10 years"                     │    │
│  │  data_gap_ids:       ["ghana/step_outdated", ...]      │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**The headline demo moment:**
> "Frey-Osborne says 89%. In Accra, it's 37%. Here's the math."

This is not a reassurance. It is a correction with a traceable source chain. Judges who want to verify can follow every factor to its primary source.

---

## 4. The Match Packet

Every opportunity match carries the full distance — training months, income multiple, skill gaps — so the user can make an informed decision.

```
┌─────────────────────────────────────────────────────────────────┐
│                 UNMAPPED MATCH PACKET v0.1                     │
├─────────────────────────────────────────────────────────────────┤
│  OPPORTUNITY                                                    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  id:                   "opp_solar_tech_gh"             │    │
│  │  title:                "Solar Installation Technician" │    │
│  │  isco_code:            "7411"                          │    │
│  │  sector:               "renewable_energy"              │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  HONEST DISTANCE METRICS                                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  skill_overlap_pct:    36%   ← always shown            │    │
│  │  training_gap_months:  3     ← always shown            │    │
│  │  training_source:      "NVTI Ghana 3-month certificate"│    │
│  │  income_multiple:      2.3×  ← always shown            │    │
│  │  income_month:         1800 GHS                        │    │
│  │  income_source:        "GOGLA Ghana Solar Survey 2023" │    │
│  │  openings_estimate:    320                             │    │
│  │  openings_source:      "GOGLA market assessment 2023"  │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  SKILL GAPS (what still needs to close)                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  [ { skill: "Electrical installation basics",          │    │
│  │      importance: 0.9 },                                │    │
│  │    { skill: "Hazardous material awareness",            │    │
│  │      importance: 0.7 } ]                               │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ECONOMETRIC SIGNALS (live, cited)                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  wage_floor:           1,800 GHS/month                 │    │
│  │  wage_floor_source:    "ILOSTAT 2023"                  │    │
│  │  sector_growth_pct:    +34%/year                       │    │
│  │  sector_growth_source: "IRENA Jobs in RE 2023"         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  HONEST CONTEXT                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  why_good:   "Phone repair troubleshooting transfers   │    │
│  │               directly. Diagnosis mindset is the same."│    │
│  │  wrong_if:   "Remote rural (>80km) faces parts         │    │
│  │               availability challenges."                │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  MATCH SCORE DECOMPOSITION                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  skill_overlap × 0.50  =  0.36 × 0.50  =  0.180       │    │
│  │  income_score  × 0.30  =  0.80 × 0.30  =  0.240       │    │
│  │  entry_speed   × 0.20  =  0.70 × 0.20  =  0.140       │    │
│  │  heritage_bonus         =  0.15 (heritage skills)      │    │
│  │  ─────────────────────────────────────────────         │    │
│  │  total_score            =  0.720                       │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. The Blind Profile Packet

Employers receive a de-identified view until the candidate explicitly approves reveal.

```
┌─────────────────────────────────────────────────────────────────┐
│              UNMAPPED BLIND PROFILE PACKET v0.1                │
├─────────────────────────────────────────────────────────────────┤
│  VISIBLE TO EMPLOYER (before reveal)                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  opaque_handle:        "Candidate #FD8A45"             │    │
│  │  country_iso:          "GHA"                           │    │
│  │  education_level:      "secondary_complete"            │    │
│  │  overall_evidence_tier: "Peer-vouched"                 │    │
│  │  profile_strength:     72 / 100                        │    │
│  │  heritage_skills_count: 3                              │    │
│  │  isco_group_labels:    ["Trades & Craft",              │    │
│  │                          "Service & Sales"]            │    │
│  │  skills_by_tier: {                                     │    │
│  │    "Peer-vouched": [                                   │    │
│  │      { label: "Phone screen repair",                   │    │
│  │        esco_code: "S5.6.0", confidence: 0.9 }         │    │
│  │    ],                                                  │    │
│  │    "Self-reported": [                                  │    │
│  │      { label: "Mobile money operations",               │    │
│  │        is_heritage: true }                             │    │
│  │    ]                                                   │    │
│  │  }                                                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  HIDDEN UNTIL REVEAL APPROVED                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  name, age, gender, phone, photo, exact location       │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  REVEAL MECHANISM                                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Employer calls POST /matching/reveal/request        │    │
│  │  2. Candidate receives Telegram/SMS notification       │    │
│  │  3. Candidate approves (or ignores — implicit deny)    │    │
│  │  4. Reveal token becomes valid (48h TTL)               │    │
│  │  5. Employer calls POST /matching/reveal/verify        │    │
│  │  6. Full profile returned — name + contact only        │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Country Configuration Packet

Every deployment context is a YAML file. No code changes required to add a country.

```yaml
# Minimum viable country config — adds a new country to UNMAPPED
country:
  iso_code: XXX          # ISO 3166-1 alpha-3
  name: "Country Name"
  currency: XXX          # ISO 4217

language:
  primary: xx            # BCP 47 language tag
  secondary: []
  ui_strings_path: locales/xx/

labor_market:
  wage_source: ilostat
  informal_sector_share: 0.00   # 0.0 – 1.0, source required
  youth_unemployment_rate: 0.00

education_taxonomy:
  levels:                        # country credential system
    - { id: none, label: "...", years: 0, isced: 0 }
    - { id: primary, label: "...", years: 6, isced: 1 }
    # ...

automation_calibration:
  baseline: frey_osborne
  infrastructure_adjustment: 0.00   # ITU ICT Dev Index fraction
  informal_economy_adjustment: 0.00  # ILO task composition fraction
  source: "cite your source"

data_gaps:
  - id: "xx/gap_name"
    description: "What data is missing and why"
    severity: high | medium | low
    affects: "which features this affects"
```

**Migration cost for a new country: one YAML file + one locales directory.**  
Zero code changes. Zero deployment changes. Zero database changes.

---

## 7. Data Flow: End-to-End

```
USER INPUT (voice/text, any language)
        │
        ▼
  Groq Whisper STT           ← transcribes voice to text
        │
        ▼
  AI Skills Interview        ← Groq Llama 3.1 70B
  (conversational, not form) ← behavioral question generation
        │
        ▼
  Skills Extraction          ← confidence-scored competency list
        │
        ├──▶ ESCO Mapper      ← ESCO REST API + ISCO fallback
        │         │
        │         ▼
        │    Heritage Skills  ← 20-entry LMIC registry match
        │
        ▼
  Skills Receipts             ← {skill, esco, isco, evidence,
  (one per competency)           confidence, timestamp, hash}
        │
        ├──▶ Peer Vouch       ← SMS token → evidence upgrade
        │
        ▼
  Skills Passport Assembly    ← Ed25519 signing
  + QR Generation             ← portable, user-owned
        │
        ├──▶ Readiness Lens
        │       ├── Frey-Osborne Calibration
        │       ├── Automation Weather Report
        │       ├── Time Machine 2035 (Wittgenstein)
        │       └── Skills Constellation (SVG)
        │
        └──▶ Opportunity Matching
                ├── Honest Matcher (scored, distance-aware)
                ├── Wrong Job (deliberate mismatch)
                ├── Blind Profile (employer view)
                └── Econ Signals (ILOSTAT + WDI, live)
```

---

## 8. Open Standard Declaration

UNMAPPED is submitted to the public domain under Apache 2.0.

Any NGO, government, training provider, or employer platform may:
- Implement the Skills Passport packet format
- Issue or verify Skills Receipts
- Extend the Heritage Skills Registry
- Add country configuration files
- Build any application layer on top

No permission required. No licensing fee. No API key required for the core packet format.

The UNMAPPED infrastructure is intentionally designed to be forkable, localisable, and replaceable. If a better system emerges, the passport format should survive the transition. Holder data is signed by the holder's own Ed25519 key — not locked to any vendor.

---

## 9. Known Limitations and Honest Disclosures

| Limitation | Status | Mitigation |
|---|---|---|
| Frey-Osborne is US-derived | Disclosed in every calibration output | Country adjustment factors applied and cited |
| STEP data for Ghana ends 2014 | Disclosed in UI data gap panel | SSA regional proxy used; explicitly labeled |
| Informal wage floors are estimated | Disclosed in every wage display | GLSS household survey + CPI adjustment, cited |
| Geographic opportunity counts are modeled | Disclosed | Sector employment density model, not live vacancies |
| LLM skill extraction has error rate | Disclosed via confidence scores | Peer vouch mechanism upgrades unreliable self-reports |
| Wittgenstein projections carry ±40% uncertainty | Disclosed in time machine view | Scenario range shown; not point estimates |

---

*UNMAPPED Protocol Specification v0.1*  
*Built for World Bank Youth Summit Challenge 05*  
*Apache 2.0 — public domain infrastructure*
