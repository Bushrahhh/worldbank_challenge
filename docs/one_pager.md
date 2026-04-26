# UNMAPPED
## Open Skills Infrastructure for the AI Age

*World Bank Youth Summit Challenge 05 × MIT Club of Northern California × MIT Club of Germany*

---

### The Problem

**1.2 billion people** work in the informal economy across low- and middle-income countries.  
Their skills are real. Their experience is real. Their productivity is real.  
The formal economy cannot see any of it.

Not because the skills aren't there.  
**Because the infrastructure to make them visible doesn't exist.**

Meanwhile, automation is arriving — unevenly, faster in cities, slower in rural areas — and the workers most exposed have no way to know their risk, no pathway to pivot, and no credential that crosses a border or survives a platform shutdown.

---

### The Insight

The global skills recognition problem is not a product problem.  
LinkedIn exists. ILO credential frameworks exist. National training registries exist.

**The problem is a missing layer** — the way SMTP is a missing layer between email clients, or TCP/IP between applications. A standardized, portable, open packet format for human capability that works on any device, in any language, with or without connectivity.

---

### What UNMAPPED Builds

```
┌──────────────────────────────────────────────────────────────────┐
│                    SKILLS PASSPORT PACKET                        │
│                                                                  │
│  [AI Interview] → [Skill Receipts] → [Ed25519 Signed] → [QR]   │
│                                                                  │
│  Each receipt: skill · ESCO code · evidence type · confidence   │
│  Heritage tier: mobile money · repair mindset · community trust │
│                                                                  │
│  User-owned. Portable. Cross-border. Not locked to any platform. │
└──────────────────────────────────────────────────────────────────┘
         │                          │                    │
         ▼                          ▼                    ▼
┌─────────────────┐   ┌─────────────────────┐   ┌──────────────────┐
│  READINESS LENS │   │  HONEST MATCHING     │   │  POLICYMAKER     │
│                 │   │                      │   │  DASHBOARD       │
│ Frey-Osborne    │   │ Distance-aware:      │   │                  │
│ 89% → 12% GHA  │   │ "Solar tech — 3mo,   │   │ 47,000 workers.  │
│ Here's the math │   │  2.3× your income,   │   │ Reached: 2,300.  │
│                 │   │  47 openings near    │   │ Displaced: 12K.  │
│ Weather Report  │   │  you."               │   │ Cost: $73M USD.  │
│ ⛅ Partly cloudy │   │                      │   │                  │
│                 │   │ Wrong Job feature:   │   │ Not a dashboard  │
│ Time Machine    │   │ "This one is wrong   │   │ that reassures.  │
│ 2035: 4 panels  │   │  for you. Here's why"│   │ One that creates │
│ + regret panel  │   │                      │   │ urgency.         │
└─────────────────┘   └─────────────────────┘   └──────────────────┘
```

---

### The Differentiators

**01 — Heritage Skills tier.**  
Mobile money fluency. Repair-not-replace mindset. Community trust networks. Informal market trading. 20 curated competencies that ESCO, O*NET, and ISCO miss entirely — but LMIC employers value critically. This is a genuine intellectual contribution to the skills taxonomy literature.

**02 — Frey-Osborne calibration as a headline, not a footnote.**  
"Phone repair is 89% automatable." That is US data. In Accra, it is 12%. The calibration — infrastructure adjustment × informal task composition — is shown transparently with every number sourced to ILOSTAT, ILO task indices, and ITU. Not a black box. A traceable correction.

**03 — Country swap in one YAML file.**  
Ghana to Bangladesh: different currency, different language script, different education taxonomy, different calibration factors, different opportunity catalog. Zero code changes. This is not localizability as a slide. It is demonstrated live, in under 10 seconds.

**04 — Honest matching, not aspirational.**  
Every match shows the real distance: training months, income multiple, skill gap. The "Wrong Job" feature — deliberately surfacing one mismatch and explaining why — builds trust no aspirational tool can. A system willing to say no is trusted when it says yes.

**05 — User-sovereign credentials.**  
Skills Passports are signed with the holder's own Ed25519 keypair. They are not locked to UNMAPPED, not stored in a proprietary database, not controlled by an employer. The QR code travels with the worker, not with the platform.

---

### The Data Sources

Every number has a source. Every source has a citation.

| Data | Source | Used for |
|---|---|---|
| Automation probability | Frey & Osborne 2013/2017 | Readiness baseline |
| Infrastructure index | ITU Digital Development Index | Calibration factor |
| Task composition | ILO Future of Work indices | Calibration factor |
| Wage floors | ILOSTAT REST API | Matching econ signal |
| Sector growth | World Bank WDI REST API | Matching econ signal |
| Skills taxonomy | ESCO REST API + O*NET | Receipt coding |
| Education projections | Wittgenstein Centre 2025–2035 | Time Machine 2035 |
| Opportunity data | GOGLA, BGMEA, BoG, IRENA, WHO | Opportunity catalog |

Data gaps are disclosed in the UI — not hidden. The STEP data for Ghana ends in 2014. Informal wages are estimated. Projection uncertainty is ±40% at district level. **Honesty is a feature, not an admission of failure.**

---

### The Cost

| Stage | Monthly cost | Covers |
|---|---|---|
| Demo | $0 | Groq free tier, SQLite, local hosting |
| NGO pilot (1 country, 1,000 users) | ~$5–20 | Groq API, Railway/Render hosting |
| Scale (10 countries, 100K users) | ~$200–500 | Groq API, managed Postgres, CDN |

No proprietary hardware. No per-user licensing. No data lock-in. The stack is entirely open-source and API-based. A country with one developer can deploy a full instance in one afternoon.

---

### The Ask

Not funding. Not a pilot. **Recognition of the infrastructure gap.**

The World Bank, ILO, and MIT have the convening power to make UNMAPPED the reference implementation of an open skills packet standard — the way IETF publishes RFC specifications that any implementer can adopt.

The alternative is another cohort of products that reach the already-visible and miss the 1.2 billion who are not.

---

*Apache 2.0 · github.com/[repo] · Built in 72 hours*  
*FastAPI · Groq Llama 3.1 70B + Whisper · ESCO · ILOSTAT · World Bank WDI · Wittgenstein Centre*
