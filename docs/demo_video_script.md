# UNMAPPED — 90-Second Demo Video Script
### Async Submission · World Bank Youth Summit Challenge 05

---

## PRODUCTION NOTES

**Format:** Screen recording + voiceover. No face cam required.  
**Resolution:** 1920×1080 minimum.  
**Audio:** Voiceover only. No background music — this is a technical submission, not a pitch competition.  
**Pacing:** Read at 140 words per minute. Every beat has a visual counterpart ready.  
**Total words:** ~210 (90 seconds at 140 wpm)

---

## THE SCRIPT

*(timecode — action — voiceover)*

---

**[0:00–0:08] — TITLE CARD**

*Screen: Black background. "UNMAPPED" in white. Below: "Open Skills Infrastructure for the AI Age."*

> "Meet Amara. 22, outside Accra, five years of phone repair experience, three languages, no formal credential the economy recognizes. We built the layer that makes her visible — on her terms."

---

**[0:08–0:22] — AI SKILLS INTERVIEW**

*Screen: Telegram bot. Type /interview. Bot asks: "Walk me through fixing a phone screen." Type a one-line response. Watch skill tags appear.*

> "UNMAPPED doesn't give Amara a form. It interviews her. Groq Llama 3.1 — running on any phone over 2G. It extracts competencies from lived experience, maps them to ESCO and ISCO codes, and flags Heritage Skills — mobile money fluency, repair-mindset, community trust — competencies that global taxonomies miss but LMIC employers value."

---

**[0:22–0:33] — SKILLS PASSPORT**

*Screen: Passport view with skills receipts stacked. Zoom to QR code.*

> "The output is a Skills Passport. Ed25519 signed. QR-linked. User-owned. Every skill is a receipt — evidence type, confidence, source. Peer vouching via SMS upgrades self-reports to verified credentials. Amara owns this. No platform does."

---

**[0:33–0:48] — FREY-OSBORNE CALIBRATION**

*Screen: Readiness view. Large text: "89%" → arrow → "12%". Below: the calibration math visible.*

> "The headline moment. Frey and Osborne say phone repair is 89% automatable. That is US data. In Accra, calibrated for infrastructure and informal task composition, it is 12%. Every factor is sourced — ITU, ILO, World Bank. No black box. A traceable correction."

*Screen: Weather report appears — "Partly Cloudy. 5–10 year horizon."*

> "The risk becomes a weather report. Partly cloudy. Five to ten years. Here's your umbrella — three adjacent skills reachable in six months."

---

**[0:48–1:03] — HONEST MATCHING + WRONG JOB**

*Screen: Match results. Top result: "Mobile Money Agent Supervisor — 1 month training, 2.6× income, 450 openings. ILOSTAT: 1,800 GHS floor. WDI: +22% sector growth."*

> "Matching is honest, not aspirational. Every result shows the real distance — training months, income multiple, skill gaps — with live ILOSTAT wage floors and World Bank sector growth data, source-cited in the UI."

*Screen: Wrong Job panel slides in. Title: "This one is wrong for you — here's why."*

> "And the Wrong Job feature. One result we deliberately set aside, with an explanation. A system willing to say no is trusted when it says yes."

---

**[1:03–1:15] — POLICYMAKER DASHBOARD + COUNTRY SWAP**

*Screen: Dashboard — DistrictView. "47,000 workers. Reached: 2,300. Displaced by 2030: 12,220. Cost of inaction: $73M USD."*

> "The policymaker view shows the numbers that create urgency, not comfort. 47,000 unmapped workers. 4.9% coverage. $73 million in lost productivity if nothing changes."

*Screen: Terminal. Type ACTIVE_COUNTRY=bangladesh. Dashboard refreshes — BDT, Bengali, new catalog.*

> "And the country swap. Bangladesh. Different language, currency, education system, calibration. Zero code changes. One YAML file. That is the entire migration cost."

---

**[1:15–1:30] — CLOSE**

*Screen: The packet diagram from the protocol spec. Clean, minimal.*

> "UNMAPPED is not a product. It is a protocol — like SMTP for human capability. Open source, Apache 2.0, $0 demo stack, $5 to $20 per month for real NGO deployment. The infrastructure layer that makes Amara visible — on her terms, not the system's."

*Screen: Fade to UNMAPPED wordmark + "Apache 2.0 · World Bank Youth Summit Challenge 05"*

---

## SCREEN RECORDING CHECKLIST

Before hitting record, confirm:

- [ ] Backend running: `ACTIVE_COUNTRY=ghana uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- [ ] Telegram bot open and responsive
- [ ] Dashboard loaded at `http://localhost:8000/dashboard`
- [ ] Browser zoom at 100% — no text cut off
- [ ] Terminal window visible for the country swap beat
- [ ] System notifications turned off
- [ ] Clock/taskbar hidden or cropped in recording

**Pre-type the interview response** so you don't have a long pause at [0:08]. Something like:
> *"I check the digitizer first, then lift the screen with the spudger, replace the panel, test touch and brightness before closing."*

That response will generate a rich skills extraction.

---

## TIMING MAP

| Beat | In | Out | Duration |
|---|---|---|---|
| Title + Amara | 0:00 | 0:08 | 8s |
| AI Interview | 0:08 | 0:22 | 14s |
| Skills Passport | 0:22 | 0:33 | 11s |
| Frey calibration + weather | 0:33 | 0:48 | 15s |
| Matching + Wrong Job | 0:48 | 1:03 | 15s |
| Dashboard + swap | 1:03 | 1:15 | 12s |
| Close | 1:15 | 1:30 | 15s |
| **Total** | | | **1:30** |

If over 90 seconds: cut the weather report description (5 seconds saved).  
If under 90 seconds: hold on the calibration math for an extra beat.

---

*UNMAPPED · Apache 2.0 · World Bank Youth Summit Challenge 05*
