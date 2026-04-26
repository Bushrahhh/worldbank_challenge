# UNMAPPED — Pitch Deck
## 10 Slides · World Bank Publication Style
### World Bank Youth Summit Challenge 05

> **Design brief for the visual team:**
> World Bank publication aesthetic — restrained, data-forward, no gradients.
> Palette: white (#FFFFFF), navy (#003F87), slate (#4A5568), accent red (#C0392B).
> Typography: Noto Sans for body, Georgia for headlines. No stock photography.
> Every number on every slide carries a source citation in 8pt below.

---

## SLIDE 1 — Title

**UNMAPPED**

*Open Skills Infrastructure for the AI Age*

World Bank Youth Summit Challenge 05
MIT Club of Northern California × MIT Club of Germany

[Single image: a QR code — the Skills Passport. Clean. No decoration.]

---

## SLIDE 2 — The Person Behind the Statistic

**Meet Amara.**

22. Outside Accra. Secondary school certificate.
Running a phone repair business since age 17.
Speaks 3 languages. Taught herself coding from YouTube on a shared mobile connection.

The formal economy cannot see her.
Not because she isn't skilled.
**Because the infrastructure to make her visible doesn't exist.**

[Design note: plain text on white. No photo. Let the specificity do the work.]

---

## SLIDE 3 — The Scale

**1.2 billion workers.**
**Invisible to the formal economy.**

```
Informal employment share — selected countries
─────────────────────────────────────────────
Ghana          89%  ████████████████████████▏
Bangladesh     85%  ████████████████████████
India          80%  ██████████████████████
Nigeria        92%  █████████████████████████▌
Ethiopia       95%  ██████████████████████████▊
Sub-Saharan    86%  ████████████████████████
  Africa avg        (ILO, 2022)
```

By 2030, automation will displace **85 million jobs** in low- and middle-income countries.
The workers most exposed have no credential, no pathway, no warning.

*Sources: ILO World Employment and Social Outlook 2022; World Economic Forum Future of Jobs 2023*

---

## SLIDE 4 — The Diagnosis

**The problem is not missing products. It is missing infrastructure.**

| What exists | What it can't do |
|---|---|
| LinkedIn | Requires CV, internet, English, professional network |
| ILO credential frameworks | Taxonomies — they describe skills, don't assess or match |
| National training registries | Siloed by country, not portable, not worker-owned |
| NGO skills programs | Reach thousands. 1.2 billion need infrastructure, not programs |

**The gap is the layer between the worker and every system that should be able to see her.**

Like the missing layer before SMTP: email clients existed, mail servers existed — but without the protocol, they couldn't talk to each other.

UNMAPPED is the protocol.

---

## SLIDE 5 — What We Built

**Three modules. One open protocol.**

```
MODULE 1 — SKILLS SIGNAL ENGINE
AI interview (Groq Llama 3.1 70B) + voice input (Whisper)
→ Skills Receipts (ESCO + ISCO coded, confidence scored)
→ Heritage Skills (20 LMIC-specific competencies missed by global taxonomies)
→ Skills Passport (Ed25519 signed, QR, user-owned, portable)
→ Peer vouching via SMS

MODULE 2 — READINESS LENS
Frey-Osborne calibrated to LMIC context:
"89% automatable (US data) → 12% in Accra. Here's the math."
→ Automation Weather Report (Clear / Cloudy / Storm)
→ Time Machine 2035 (Wittgenstein Centre, 4 panels + regret)
→ Skills Constellation Map

MODULE 3 — OPPORTUNITY MATCHING
Honest matching with distance: training months · income multiple · skill gaps
→ "Wrong Job" feature: surfaces one mismatch and explains why
→ Blind employer view (skills visible, identity hidden until candidate approves)
→ Live ILOSTAT wage floor + World Bank WDI sector growth, source-cited
→ Policymaker dashboard: the uncomfortable numbers, not the comfortable ones
```

---

## SLIDE 6 — The Intellectual Contribution

**Two things no other submission has.**

**1. The calibration.**

Frey & Osborne say phone repair is 89% automatable.
That is a US number. In Accra, it is 12%.

The correction: infrastructure adjustment (ITU Index) × informal task composition (ILO).
Shown transparently. Every factor sourced.
Not a reassurance — a traceable correction.

**2. Heritage Skills.**

Mobile money fluency. Repair-not-replace mindset. Community trust networks. Oral instruction delivery. Cross-border informal trade.

These are real competencies. LMIC employers pay for them.
ESCO, O*NET, and ISCO do not formally recognize them.
UNMAPPED is the first system to issue a verifiable receipt for them.

*This is a genuine contribution to the skills taxonomy literature, not UI decoration.*

---

## SLIDE 7 — Country Swap: Protocol Not Product

**Adding a country = one YAML file. Zero code changes.**

```
ACTIVE_COUNTRY=ghana    → GHS · English · JHS/SHS taxonomy · 89% informal
ACTIVE_COUNTRY=bangladesh → BDT · Bengali · SSC/HSC/TVET taxonomy · 85% informal
```

Live demo: Ghana → Bangladesh in under 10 seconds.

Different at every dimension:
- Currency and language
- Education credential system
- Automation calibration factors
- Opportunity catalog
- Localized UI strings

**This is not localizability as a slide. This is localizability as running code.**

Incremental cost to add a third country: one developer, one afternoon.

---

## SLIDE 8 — The Numbers That Should Create Urgency

**Greater Accra Region — current state**

| Metric | Value | Source |
|---|---|---|
| Unmapped workers | 47,000 | ILO + World Bank STEP estimate |
| Reached by current programs | 2,300 (4.9%) | Government enrollment data |
| At automation risk by 2030 | 12,220 | Frey-Osborne calibrated |
| Cost of inaction (5 years) | $73M USD | World Bank productivity proxy |

Most dashboards show policymakers what they want to see.
**This dashboard shows what they need to act on.**

The slider is live. Judges can change the inputs. The methodology is in the repo.

---

## SLIDE 9 — Technical Reality

**Stack cost: $0 for the demo. ~$5–20/month for a real NGO deployment.**

```
COMPONENT          DEMO              PRODUCTION
─────────────────────────────────────────────────────
LLM (interview)    Groq free tier    Groq API / Ollama Mistral 7B
Voice STT          Groq Whisper      Groq Whisper / on-device
Bot channel        Telegram          Telegram (any phone, 2G)
Backend            FastAPI + SQLite  FastAPI + PostgreSQL
Hosting            Local             Railway / Render free tier
Data sources       All free REST APIs (ESCO, ILOSTAT, WDI)
License            Apache 2.0        Apache 2.0
```

Designed for: $30 Android phone · 2G connection · shared device · intermittent power.

If it doesn't work in those conditions, it doesn't ship.

---

## SLIDE 10 — The Ask

**Not funding. Not a pilot.**

**Recognition that the infrastructure gap is real — and that a protocol can close it.**

```
                    THE LADDER EVERY AMARA NEEDS
                    ─────────────────────────────

OPPORTUNITY         ████████████████████  ← exists
                         ↑
                    GAP — no ladder
                         ↓
AMARA'S SKILLS      ████████████████████  ← real, unrecognized

UNMAPPED is the ladder.
```

The World Bank, ILO, and MIT have the convening power to make UNMAPPED the reference implementation of an open skills packet standard — the way IETF RFCs define protocols any implementer can adopt.

**The alternative is another generation of workers who are unmapped.**

---

*UNMAPPED v0.1 · Apache 2.0 · Built for World Bank Youth Summit Challenge 05*
*FastAPI · Groq Llama 3.1 70B · Whisper · ESCO · ILOSTAT · World Bank WDI · Wittgenstein Centre*
*Stack cost: $0 demo · $5–20/month NGO deployment*
