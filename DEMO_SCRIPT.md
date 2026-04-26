# UNMAPPED — 5-Minute Demo Script
### World Bank Youth Summit Challenge 05 × MIT Club of Northern California × MIT Club of Germany

> **Read this once before the demo. Then put it down. The demo lives or dies on authenticity, not polish.**

---

## THE ONE SENTENCE

"We built the layer that makes invisible skills visible — on the worker's terms, not the system's."

---

## SETUP (before judges enter)

- Backend running: `ACTIVE_COUNTRY=ghana uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Telegram bot running: `python telegram_bot/bot.py`
- Browser tab 1: Telegram Web or Telegram Desktop, open to the UNMAPPED bot
- Browser tab 2: `http://localhost:8000/dashboard` (policymaker view)
- Browser tab 3: `http://localhost:8000/docs` (API — for the technical judges)
- Terminal visible with server logs (shows data gap warnings — leave them, they're a feature)
- Frey-Osborne stat ready: "89% → 12%" for phone repair in Ghana

---

## THE SCRIPT

### BEAT 1 — Meet Amara (30 seconds)

> "Meet Amara. 22. Lives outside Accra. Secondary school certificate. She's been running a phone repair business since she was 17. She speaks three languages. She taught herself coding from YouTube — on a shared mobile connection.
>
> The formal economy cannot see her. Not because she isn't skilled. Because the infrastructure to make her visible doesn't exist.
>
> We built that infrastructure. It's called UNMAPPED."

---

### BEAT 2 — AI Skills Interview, live (60 seconds)

**[Open Telegram bot. Type /interview or press the button.]**

> "UNMAPPED doesn't give Amara a form to fill in. It interviews her."

**[Show the first question from the bot — e.g., "Walk me through fixing a phone screen."]**

> "Conversational, behavioral questions. Powered by Groq Llama 3.1 — running on a $30 Android phone over 2G if needed."

**[Type a one-sentence response like: "I open the phone, check the digitizer, replace the screen, test the touch sensitivity."]**

> "The system extracts competencies from lived experience — not from checkboxes. Watch what happens."

**[Show the extracted skill tags: electronics troubleshooting, diagnostic reasoning, hardware repair.]**

> "And notice this — [point to Heritage Skills appearing] — mobile money fluency, repair-not-replace mindset. Skills that global taxonomies miss entirely. We call these Heritage Skills. They're real. They're valued by LMIC employers. UNMAPPED is the first system to formally recognize them."

---

### BEAT 3 — Skills Passport reveal + QR (30 seconds)

**[Type /passport or navigate to the passport view.]**

> "The output is a Skills Passport. JSON-structured, Ed25519 signed, portable across borders. The QR code links to a verifiable profile that Amara owns — not us, not a government, not an employer. Her."

**[Show the QR code on screen. Scan it if time allows.]**

> "Every skill has a receipt: the evidence type, the confidence score, whether it's been peer-vouched. Amara's customers can text a short code to verify they've seen her work. That's social proof as credential — the metaphor her market already uses."

---

### BEAT 4 — Frey-Osborne calibration (45 seconds)

**[Navigate to the Readiness view, or call GET /readiness/calibration/7422 in the docs.]**

> "Now the headline moment."

**[Read this verbatim:]**

> "Frey and Osborne say phone repair is 89% likely to be automated. That is US data. In Accra, the calibrated risk is 12%. Here's why."

**[Point to the calibration breakdown on screen.]**

> "Ghana's digital infrastructure score is 0.70 of the US level. The informal economy task composition is 0.60. When you apply those corrections to the Frey-Osborne baseline — transparently, not as a black box — you get 12%."

> "Every number you see has a source tooltip. [Hover one.] ILOSTAT. World Bank WDI. ITU. This is not vibes. This is traceable math."

---

### BEAT 5 — Time Machine 2035 (45 seconds)

**[Show the Time Machine panel — readiness view or /readiness/time_machine API response.]**

> "Four panels. Amara today. Amara in 2035 if she does nothing — Wittgenstein Centre SSP3 projection. Amara in 2035 if she adds solar installation skills — SSP2. Amara in 2035 if she takes the fastest path — SSP1."

**[Point to the fourth panel — the regret panel.]**

> "And this panel. Amara in 2035 if this system had existed in 2020. The cost of the missing five years. We put this here deliberately. Urgency should be visible."

---

### BEAT 6 — Honest matching + Wrong Job + econ signals (60 seconds)

**[Show the matching results — either via Telegram bot or POST /matching/match/{uuid} in docs.]**

> "Now we match her to opportunities. Not aspirationally. Honestly."

**[Read the top match:]**

> "Mobile Money Agent Supervisor. One month training. 2.6 times her estimated current income. 450 openings. And right here — [point to econ signals] — the ILOSTAT wage floor for this occupation in Ghana: 1,800 GHS per month. The World Bank WDI says the mobile finance sector grew 22% last year. Source cited. In plain language."

> "But here's what no other tool does."

**[Show the Wrong Job result.]**

> "This one — Digital Marketing Assistant — we deliberately set aside. 6 months training, requires a portfolio that takes another 3-6 months to build. We tell her that. Explicitly. A system that's willing to say 'no' is trusted when it says 'yes.'"

> "And employers see this — [flip to blind match view] — no name, no gender, no age. Candidate #FD8A45. Skills, evidence tiers, ISCO groups. They request reveal. She approves. Then and only then does her identity appear."

---

### BEAT 7 — Policymaker Cost of Inaction view (30 seconds)

**[Switch to browser tab 2: http://localhost:8000/dashboard]**

> "This is the policymaker view. Most dashboards reassure. This one creates urgency."

**[Read the headline numbers out loud:]**

> "47,000 workers in Greater Accra who are invisible to the formal economy. Current programs reach 2,300 — 4.9% coverage. At current automation trajectory, 12,220 will be displaced by 2030 with no pathway visible. Cost: $73 million USD in lost productivity over five years."

**[Move the Cost of Inaction sliders — show the number change live.]**

> "Every number has a source. Every gap is disclosed. [Point to the data gaps panel.] This is not a comfortable dashboard. It is a true one."

---

### BEAT 8 — LIVE country swap to Bangladesh (30 seconds) — the mic-drop moment

**[This is the technical centerpiece. Practice it twice before the demo.]**

> "Everything you've seen is configured for Ghana. I'm going to swap to Bangladesh. No code changes. One environment variable."

**[In terminal, visible to judges:]**
```
ACTIVE_COUNTRY=bangladesh uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

**[Switch to the dashboard on port 8001 — Bangladesh preset auto-loads.]**

> "Bangladesh. 85% informal sector share. Bengali as primary language. Different education taxonomy — JSC, SSC, HSC, TVET — not Ghana's structure. Different calibration factors for rural agricultural context. Different opportunity catalog — garments QC, solar home systems, bKash agent network."

> "Same infrastructure. New YAML file. That's the entire migration cost for a new country."

> "We're not building a product for Ghana. We're building SMTP for human capability."

---

### BEAT 9 — Close: protocol-not-product (30 seconds)

> "LinkedIn is a product. It works for people who already have credentials, already have networks, already have visibility.
>
> UNMAPPED is a protocol. Like SMTP doesn't care which email client you use, UNMAPPED doesn't care which employer platform, which NGO database, which government registry sits on top.
>
> Amara's Skills Passport is hers. It travels with her across borders, across platforms, across the lifetime of whatever company builds on top of this.
>
> Total demo stack cost: zero dollars. Real NGO deployment: $5 to $20 per month. Infrastructure that reaches 47,000 people in a single district.
>
> UNMAPPED."

---

## LIKELY JUDGE QUESTIONS — HONEST ANSWERS

**"Is the Frey-Osborne calibration validated?"**
> "The baseline paper is peer-reviewed (Frey & Osborne 2013/2017). The LMIC adjustment factors come from ILO task-composition indices and World Bank STEP. Our combined calibration is a model, not ground truth — we disclose that in the UI. The value is in making the adjustment visible and disputable, not in claiming precision."

**"How does it work without internet?"**
> "Groq API requires connectivity for the LLM interview and Whisper STT. The Skills Passport and matching work offline after a sync. In production, we'd document a local Ollama Mistral 7B fallback — the architecture is documented for that swap."

**"What's the business model?"**
> "We're not pitching a business. We're pitching a protocol. NGO/government deployment at cost. Open source. The monetization layer is someone else's problem — the infrastructure layer is ours."

**"How is this different from LinkedIn / SFIA / ILO credentials?"**
> "LinkedIn requires connectivity, an email, a professional network, English fluency, and a CV. It was not built for Amara. SFIA and ILO frameworks are taxonomies — they describe skills, they don't interview, assess, or match. UNMAPPED is the layer between the taxonomy and the person."

**"Why should we trust the skill assessment?"**
> "We shouldn't — not yet. The self-report tier is clearly labeled. The peer-vouch tier requires a real person to confirm. The employer-verified tier requires verified employment. The receipt system makes trust levels explicit rather than hiding them. Honesty about confidence is the feature."

---

## WHAT NOT TO SAY

- ~~"This could change the world"~~ → Say what it does, specifically.
- ~~"It's like LinkedIn but for informal workers"~~ → LinkedIn is the product UNMAPPED is not.
- ~~"The algorithm matches skills"~~ → Say "the system calculates skill overlap from ISCO codes and labeled competencies."
- ~~"It's very accurate"~~ → Say "it shows its confidence level and data sources."
- ~~"We can onboard any country"~~ → Say "adding a country requires a YAML config file — we showed that live."

---

## TIMING GUIDE

| Beat | Target | Hard max |
|------|--------|----------|
| 1 — Amara | 30s | 40s |
| 2 — Interview | 60s | 75s |
| 3 — Passport + QR | 30s | 40s |
| 4 — Frey calibration | 45s | 55s |
| 5 — Time Machine | 45s | 55s |
| 6 — Matching + Wrong Job + econ | 60s | 70s |
| 7 — Policymaker dashboard | 30s | 40s |
| 8 — Country swap | 30s | 35s |
| 9 — Close | 30s | 35s |
| **Total** | **5:00** | **5:45** |

If running long: cut Beat 5 (Time Machine) to 20 seconds — just name the four panels.
If running short: spend extra time in Beat 6 (Matching) hovering source tooltips.

---

## TECHNICAL FALLBACK (if Groq API fails mid-demo)

1. `GET /skills/heritage` — shows Heritage Skills list without LLM
2. Pre-load a completed passport UUID in `.env` as `DEMO_PASSPORT_UUID`
3. Show the static `/docs` API page — all endpoints are visible and self-documenting
4. Run `/matching/catalog` — returns full opportunity list without a passport

The architecture stands on its own even without the LLM.

---

*Built for World Bank Youth Summit Challenge 05.*
*Stack: FastAPI · Groq Llama 3.1 70B · Whisper · ESCO · ILOSTAT · World Bank WDI · Wittgenstein Centre · SQLite · Telegram Bot API*
*Cost: $0 demo. ~$5–20/month real NGO deployment.*
