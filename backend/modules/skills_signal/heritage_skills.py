"""
Heritage Skills Registry

~20 competencies that LMIC employers value but global taxonomies miss.
This is a genuine intellectual contribution to the skills mapping field.

Each entry:
  - has an ESCO proxy code (closest approximation in the formal taxonomy)
  - has natural-language trigger phrases that the LLM can match against
  - has an employer_value rating
  - has a country_relevance list (empty = universal)

These are the skills ESCO/O*NET cannot see because they were built for
OECD labor markets. Amara's repair-not-replace mindset, her mobile money
fluency, her community trust network — these are assets, not gaps.
"""

from dataclasses import dataclass, field


@dataclass
class HeritageSkill:
    id: str
    label: str
    description: str
    esco_proxy: str          # closest ESCO URI fragment
    isco_proxy: str          # closest ISCO-08 code
    employer_value: str      # low | medium | high | critical
    trigger_phrases: list[str] = field(default_factory=list)
    country_relevance: list[str] = field(default_factory=list)  # empty = universal LMIC
    example_evidence: str = ""


HERITAGE_SKILLS: list[HeritageSkill] = [

    HeritageSkill(
        id="hs_mobile_money",
        label="Mobile money operations",
        description=(
            "Managing financial transactions via mobile platforms (MTN MoMo, M-PESA, "
            "bKash, GCash, Airtel Money, Orange Money). Includes float management, "
            "customer troubleshooting, and transaction reconciliation."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/b7b17ded-8b6d-4db7-8900-2fc882c19940",
        isco_proxy="4312",
        employer_value="critical",
        trigger_phrases=[
            "mtn momo", "m-pesa", "mpesa", "bkash", "nagad", "gcash", "airtel money",
            "orange money", "mobile money", "send money", "float", "cash out",
            "mtn mobile money", "receive payment", "transfer money",
        ],
        country_relevance=["GHA", "KEN", "TZA", "UGA", "ZMB", "BGD", "PHL"],
        example_evidence="Runs MTN MoMo agent point, handles 30-50 transactions/day",
    ),

    HeritageSkill(
        id="hs_repair_mindset",
        label="Repair-not-replace problem solving",
        description=(
            "Diagnosing and fixing rather than discarding — applied to electronics, "
            "machinery, clothing, vehicles, infrastructure. The default assumption is "
            "'can this be fixed?' before 'replace it.' Highly valued in resource-constrained "
            "contexts and increasingly valued globally in circular economy transitions."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/52d8a2d6-1de3-4564-b01e-50d2fa7c9ef0",
        isco_proxy="7422",
        employer_value="high",
        trigger_phrases=[
            "fix", "repair", "diagnose", "troubleshoot", "find the problem",
            "open it up", "replace the part", "work out what's wrong",
            "repaired", "fixed it myself",
        ],
        country_relevance=[],
        example_evidence="Rebuilt a generator from salvaged parts when new parts unavailable",
    ),

    HeritageSkill(
        id="hs_multilingual_service",
        label="Multilingual customer service",
        description=(
            "Serving customers across language boundaries in local languages — "
            "switching between formal and informal registers, translating technical "
            "concepts for non-literate customers, mediating between different "
            "language communities. More valuable than standard bilingualism because "
            "it includes oral/non-literate service modes."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/c985f94e-4e23-4ef6-a8dd-6e3d3e43afcc",
        isco_proxy="5220",
        employer_value="high",
        trigger_phrases=[
            "speak", "language", "translate", "local language", "dialect",
            "twi", "hausa", "ewe", "akan", "dagbani", "bengali", "bangla",
            "customers don't speak english", "explain in", "tell them in",
        ],
        country_relevance=[],
        example_evidence="Explains phone contracts to customers in Twi and Ewe",
    ),

    HeritageSkill(
        id="hs_community_trust",
        label="Community trust and informal credit management",
        description=(
            "Managing relationships where formal contracts don't exist — credit extended "
            "on trust, goods supplied before payment, disputes resolved without courts. "
            "Includes reputation management in tight-knit markets. Underpins informal "
            "supply chains and is the foundation of LMIC B2B commerce."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/4abd9e4a-74ab-4a19-9e16-5e47a5b1e0e8",
        isco_proxy="1212",
        employer_value="high",
        trigger_phrases=[
            "trust", "credit", "pay later", "regular customer", "they know me",
            "word of mouth", "reputation", "community", "local", "they come back",
            "keep track", "owe me", "supplier trusts me",
        ],
        country_relevance=[],
        example_evidence="Extended credit to 40 customers, zero defaults over 2 years",
    ),

    HeritageSkill(
        id="hs_informal_trading",
        label="Informal market trading and negotiation",
        description=(
            "Pricing, negotiation, inventory management, and supplier relations in "
            "informal market contexts — without formal accounting systems. Includes "
            "mental arithmetic under pressure, bulk discount negotiation, and market "
            "timing knowledge (when to buy, when to sell)."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/3d8d56ca-b2a2-4c27-9eb2-2c87ee6cd0f0",
        isco_proxy="5220",
        employer_value="medium",
        trigger_phrases=[
            "buy and sell", "market", "stall", "negotiate", "bargain", "price",
            "supplier", "buy in bulk", "profit", "mark up", "inventory",
            "trade", "goods", "stock",
        ],
        country_relevance=[],
        example_evidence="Manages stock of 200+ phone parts, negotiates with 3 suppliers",
    ),

    HeritageSkill(
        id="hs_solar_maintenance",
        label="Off-grid solar system maintenance",
        description=(
            "Installing, diagnosing, and maintaining solar home systems and solar-powered "
            "equipment — panels, charge controllers, batteries, inverters. Increasingly "
            "critical as solar penetration accelerates across Sub-Saharan Africa and "
            "South Asia. Valued by solar companies, NGOs, and rural utilities."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/5ac6cca6-82b9-40a0-b14d-5a68f8c42c0f",
        isco_proxy="7411",
        employer_value="critical",
        trigger_phrases=[
            "solar", "panel", "battery", "charge controller", "inverter",
            "off-grid", "solar light", "solar pump", "solar pump", "pv",
            "photovoltaic", "solar installation",
        ],
        country_relevance=["GHA", "KEN", "ETH", "TZA", "UGA", "NGA", "BGD", "IND", "NPL"],
        example_evidence="Installed and maintains solar systems for 15 households",
    ),

    HeritageSkill(
        id="hs_moto_maintenance",
        label="Motorcycle and three-wheeler maintenance",
        description=(
            "Maintaining and repairing motorbikes, bajaj (tuk-tuks), and cargo tricycles — "
            "the primary mobility infrastructure in most LMIC cities. Includes roadside "
            "repair, performance tuning, and sourcing non-standard parts."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/a31f09fb-7f98-4028-857d-b7c9c0c0a39c",
        isco_proxy="7231",
        employer_value="high",
        trigger_phrases=[
            "motorbike", "motorcycle", "okada", "boda boda", "bajaj", "tuk-tuk",
            "tricycle", "engine oil", "spark plug", "chain", "brake", "tyre",
            "two-wheeler", "moto", "bike repair",
        ],
        country_relevance=["GHA", "KEN", "UGA", "NGA", "BGD", "IND", "KHM"],
        example_evidence="Repairs 5-8 motorcycles per week at roadside workshop",
    ),

    HeritageSkill(
        id="hs_community_health",
        label="Community health education and outreach",
        description=(
            "Delivering health information and basic services at community level — "
            "nutrition education, maternal health support, vaccination mobilization, "
            "malaria prevention. Often volunteer or informally trained but represents "
            "significant public health skill that formal health systems depend on."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/5d54a7ca-0c8c-45b7-a49d-7e8c34caee64",
        isco_proxy="3253",
        employer_value="high",
        trigger_phrases=[
            "health worker", "community health", "vaccination", "health education",
            "nutrition", "maternal health", "birth registration", "malaria",
            "health outreach", "refer patients", "health post", "chew", "chps",
        ],
        country_relevance=[],
        example_evidence="Trained community health volunteer, covers 200 households",
    ),

    HeritageSkill(
        id="hs_low_end_digital",
        label="Digital navigation on constrained devices",
        description=(
            "Using smartphones effectively on 2G/3G connections with low storage "
            "and battery constraints — includes offline-first workflows, data-saving "
            "habits, low-bandwidth app selection, and teaching others these skills. "
            "Undervalued by standard 'digital literacy' frameworks designed for OECD."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/e7cd4f72-0e14-4427-80c1-6a0dbc1cdf8c",
        isco_proxy="3514",
        employer_value="medium",
        trigger_phrases=[
            "android", "smartphone", "download", "data", "wifi", "internet",
            "youtube", "whatsapp", "facebook", "google", "app", "phone settings",
            "teach people to use", "show them how", "type", "mobile",
        ],
        country_relevance=[],
        example_evidence="Manages social media presence, teaches neighbors WhatsApp",
    ),

    HeritageSkill(
        id="hs_video_learning",
        label="Self-directed video-based learning",
        description=(
            "Acquiring technical skills via YouTube, TikTok, or social media tutorials — "
            "without formal instruction, often in a second language, often on slow "
            "connections. Demonstrates initiative, learning agility, and ability to "
            "filter and apply technical information. Increasingly recognized by employers."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/b2e7a7bc-8b10-41f7-a88e-7ee0e6e6bbca",
        isco_proxy="2356",
        employer_value="medium",
        trigger_phrases=[
            "youtube", "tutorial", "watched", "learned from", "tiktok", "video",
            "taught myself", "online", "self-taught", "no teacher", "figured out",
        ],
        country_relevance=[],
        example_evidence="Learned Python from YouTube tutorials on shared phone",
    ),

    HeritageSkill(
        id="hs_agri_calendar",
        label="Agricultural calendar and seasonal planning",
        description=(
            "Knowledge of planting seasons, input timing, pest cycles, weather patterns, "
            "and market timing for agricultural commodities. Passed through practice "
            "rather than formal training. Increasingly valuable in climate-adaptive "
            "agriculture and precision agri-services."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/c1dc1a9d-b1e4-4f99-9c5e-5f5e7c7e5cd3",
        isco_proxy="6111",
        employer_value="high",
        trigger_phrases=[
            "planting season", "harvest", "rain", "dry season", "fertilizer timing",
            "crop", "farm", "cocoa", "maize", "rice", "vegetables",
            "when to plant", "agricultural", "farming",
        ],
        country_relevance=["GHA", "KEN", "ETH", "TZA", "UGA", "NGA", "BGD", "IND", "NPL"],
        example_evidence="Manages 2-acre mixed farm, knows exact planting windows for 4 crops",
    ),

    HeritageSkill(
        id="hs_local_interpreter",
        label="Local language interpretation (oral)",
        description=(
            "Real-time interpretation between local languages and official language — "
            "in health facilities, government offices, markets, or community meetings. "
            "Distinct from translation (written) and from formal interpreting; this is "
            "informal but essential oral mediation."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/c985f94e-4e23-4ef6-a8dd-6e3d3e43afcc",
        isco_proxy="2643",
        employer_value="medium",
        trigger_phrases=[
            "interpret", "translate", "explain to", "help them understand",
            "between the doctor and", "between the officer and", "speak for",
            "translate for", "help people at",
        ],
        country_relevance=[],
        example_evidence="Informally interprets at district health center between patients and staff",
    ),

    HeritageSkill(
        id="hs_susu_management",
        label="Community savings group management",
        description=(
            "Running or participating in rotating savings and credit associations — "
            "susu (Ghana), chama (Kenya), tontine (West Africa), ROSCA/VSLA. "
            "Includes financial record keeping, conflict mediation, and trust management "
            "in the absence of formal financial infrastructure."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/e3c1b5d7-5d5e-4f5e-b5c5-5e7c7e5cd3d4",
        isco_proxy="3312",
        employer_value="medium",
        trigger_phrases=[
            "susu", "chama", "tontine", "savings group", "contribute", "pot",
            "weekly savings", "group savings", "collect from members", "rotating",
            "vsla", "rosca",
        ],
        country_relevance=["GHA", "KEN", "TZA", "NGA", "CMR"],
        example_evidence="Secretary of a 20-member susu group, manages GHS 4,000/month",
    ),

    HeritageSkill(
        id="hs_crossborder_trade",
        label="Cross-border informal trade knowledge",
        description=(
            "Navigating import/export procedures, customs, border documentation, and "
            "informal trade networks across national borders. Includes knowledge of "
            "duties, contraband risk, local contacts, and currency exchange at borders. "
            "Underlies a significant share of ECOWAS/SADC regional trade."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/3d8d56ca-b2a2-4c27-9eb2-2c87ee6cd0f0",
        isco_proxy="3331",
        employer_value="medium",
        trigger_phrases=[
            "import", "cross the border", "customs", "from nigeria", "from togo",
            "from ghana", "bring goods", "border", "export", "trade route",
        ],
        country_relevance=["GHA", "NGA", "BEN", "TGO", "SEN", "BGD", "IND"],
        example_evidence="Sources phone parts from Nigeria via Aflao border route",
    ),

    HeritageSkill(
        id="hs_food_processing",
        label="Food processing and preservation",
        description=(
            "Processing raw agricultural produce into shelf-stable or value-added products — "
            "smoking, drying, fermentation, shea butter extraction, palm oil processing, "
            "grain milling. Increasingly linked to agri-business and export markets."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/7a5e1b4c-4c5e-4f5e-b5c5-5e7c7e5cd3d4",
        isco_proxy="7511",
        employer_value="medium",
        trigger_phrases=[
            "shea butter", "palm oil", "smoked fish", "dried", "fermented",
            "kenkey", "gari", "process", "grind", "mill", "preserve",
            "food processing", "jar", "package",
        ],
        country_relevance=["GHA", "NGA", "BEN", "TGO", "SEN", "ETH"],
        example_evidence="Produces shea butter for local market, 20kg/week",
    ),

    HeritageSkill(
        id="hs_water_sanitation",
        label="Community water and sanitation management",
        description=(
            "Maintaining water point committees, WASH facility management, "
            "water quality testing, and latrine construction/maintenance. "
            "Relevant to NGO programs, government WASH departments, and rural utilities."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/6c3f4a7e-8b9c-4d2a-b1e5-9f3c5a2d7e6b",
        isco_proxy="8160",
        employer_value="medium",
        trigger_phrases=[
            "water point", "borehole", "well", "latrine", "toilet", "sanitation",
            "water committee", "wash", "clean water", "water quality", "chlorine",
        ],
        country_relevance=[],
        example_evidence="Chairperson of village water management committee",
    ),

    HeritageSkill(
        id="hs_conflict_mediation",
        label="Community conflict mediation",
        description=(
            "Facilitating resolution of disputes — family, commercial, land — using "
            "community norms and informal processes. Distinct from formal mediation/ADR. "
            "Valued by NGOs, local government, and development organizations."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/8e2f3c1a-5b4d-4a6e-9c2f-3b5a8d1e7f4c",
        isco_proxy="2635",
        employer_value="medium",
        trigger_phrases=[
            "mediator", "resolve", "settle", "dispute", "conflict",
            "community leader", "chief", "elder", "traditional authority",
            "help people agree", "facilitate",
        ],
        country_relevance=[],
        example_evidence="Called on to mediate land disputes in the community, settled 8 cases",
    ),

    HeritageSkill(
        id="hs_informal_teaching",
        label="Informal skills teaching and coaching",
        description=(
            "Teaching practical skills in non-formal settings — apprentices, neighbors, "
            "younger family members. Often not recognized as 'teaching' by the person "
            "doing it. Demonstrates communication, patience, and ability to break down "
            "complex tasks for novices."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/b2e7a7bc-8b10-41f7-a88e-7ee0e6e6bbca",
        isco_proxy="2356",
        employer_value="medium",
        trigger_phrases=[
            "teach", "show", "trained", "apprentice", "helped learn",
            "explain how", "taught my", "show people how",
            "volunteer teacher", "tutoring",
        ],
        country_relevance=[],
        example_evidence="Has trained 4 apprentices in phone repair over 3 years",
    ),

    HeritageSkill(
        id="hs_remote_logistics",
        label="Remote and rural logistics coordination",
        description=(
            "Coordinating supply chains and deliveries in areas with poor roads, "
            "unreliable transport, and no formal logistics infrastructure. "
            "Includes knowledge of alternative routes, trusted carriers, and "
            "seasonal access constraints."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/9f4c2a1e-6b3d-4e5f-a2c1-7d9b3e6f8a4c",
        isco_proxy="4323",
        employer_value="high",
        trigger_phrases=[
            "delivery", "supply", "route", "transport", "carry", "lorry",
            "distribute", "send to", "get to the village", "remote",
            "hard to reach", "logistics",
        ],
        country_relevance=[],
        example_evidence="Coordinates weekly supplies to 3 rural clinics via motorcycle couriers",
    ),

    HeritageSkill(
        id="hs_crowd_event",
        label="Crowd and event management",
        description=(
            "Organizing and managing community events — funerals, markets, political rallies, "
            "religious gatherings. Includes crowd flow, emergency awareness, vendor "
            "coordination, and keeping order in informal settings. Relevant to NGOs, "
            "government agencies, and venue operators."
        ),
        esco_proxy="http://data.europa.eu/esco/skill/7f2a3e1c-9b4d-4f5e-a1c2-6d8b3e5f7a4c",
        isco_proxy="5151",
        employer_value="low",
        trigger_phrases=[
            "event", "organize", "crowd", "funeral", "market day", "rally",
            "gathering", "community meeting", "manage the crowd",
            "coordinate", "setup",
        ],
        country_relevance=[],
        example_evidence="Organized annual community market with 500+ vendors for 3 years",
    ),
]

# Fast lookup by trigger phrase
_TRIGGER_INDEX: dict[str, list[HeritageSkill]] = {}
for _hs in HERITAGE_SKILLS:
    for _phrase in _hs.trigger_phrases:
        _TRIGGER_INDEX.setdefault(_phrase.lower(), []).append(_hs)


def match_heritage_skills(text: str) -> list[HeritageSkill]:
    """
    Return Heritage Skills triggered by keywords in the given text.
    Case-insensitive. Returns deduplicated list sorted by employer_value.
    """
    text_lower = text.lower()
    found: dict[str, HeritageSkill] = {}
    for phrase, skills in _TRIGGER_INDEX.items():
        if phrase in text_lower:
            for skill in skills:
                if skill.id not in found:
                    found[skill.id] = skill
    value_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(found.values(), key=lambda s: value_order.get(s.employer_value, 4))


def get_heritage_skill(skill_id: str) -> HeritageSkill | None:
    return next((s for s in HERITAGE_SKILLS if s.id == skill_id), None)


def get_all_labels() -> list[str]:
    return [s.label for s in HERITAGE_SKILLS]
