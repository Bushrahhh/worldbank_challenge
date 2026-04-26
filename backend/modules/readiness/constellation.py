"""
Readiness Lens — Skills Constellation Map

Visualizes the passport holder's skills as a star map:
  - Bright gold stars   = current Heritage Skills
  - Blue stars          = current technical/formal skills
  - Glowing ring        = reachable adjacent skills (within 6–12 months)
  - Dimming red stars   = skills with high automation risk

Returns JSON with (x, y, r) coordinates for SVG rendering in the browser.
The layout uses a deterministic polar coordinate system — same passport
always produces the same map.
"""

import hashlib
import math
from backend.modules.readiness.frey_calibrator import _ADJACENT_ISCO, get_calibration

# SVG viewport
_CX = 300
_CY = 300
_R_CORE = 90      # radius for core (current) skills
_R_ADJACENT = 190  # radius for adjacent/reachable skills
_R_DISTANT = 260  # radius for distant but visible skills

# Node size by evidence quality
_EVIDENCE_RADIUS = {
    "employer_verified": 14,
    "peer_vouched": 11,
    "self_report": 8,
    "assessed": 13,
}

# Node color by skill type
_COLOR_HERITAGE = "#f0b429"
_COLOR_TECHNICAL = "#58a6ff"
_COLOR_SOCIAL = "#3fb950"
_COLOR_DIGITAL = "#bc8cff"
_COLOR_ADJACENT = "#2a3f5a"
_COLOR_AT_RISK = "#f85149"


def _stable_angle(seed: str, index: int, total: int) -> float:
    """Deterministic angle placement using skill label hash + index."""
    h = int(hashlib.sha256(f"{seed}{index}".encode()).hexdigest()[:8], 16)
    base_angle = (2 * math.pi * index / max(total, 1))
    jitter = (h % 100 - 50) / 100 * (math.pi / max(total, 3))
    return base_angle + jitter


def _skill_color(skill: dict) -> str:
    if skill.get("is_heritage_skill"):
        return _COLOR_HERITAGE
    label = (skill.get("skill_label") or "").lower()
    if any(w in label for w in ("code", "digital", "software", "app", "computer", "data")):
        return _COLOR_DIGITAL
    if any(w in label for w in ("community", "trust", "network", "social", "customer", "service")):
        return _COLOR_SOCIAL
    return _COLOR_TECHNICAL


def build_constellation(receipts: list[dict]) -> dict:
    """
    Build the star map data from a list of skill receipts.
    Returns {nodes: [...], edges: [...], viewport: {...}}.
    """
    if not receipts:
        return {"nodes": [], "edges": [], "viewport": {"width": 600, "height": 600, "cx": _CX, "cy": _CY}}

    nodes = []
    edges = []
    seen_isco = set()
    adjacent_added = set()

    # Place current skills in the core ring
    total = len(receipts)
    for i, skill in enumerate(receipts):
        angle = _stable_angle(skill.get("skill_label", str(i)), i, total)
        # Vary radius slightly so overlapping skills don't stack
        r_jitter = _R_CORE + (i % 3) * 18
        x = round(_CX + r_jitter * math.cos(angle), 1)
        y = round(_CY + r_jitter * math.sin(angle), 1)

        isco = skill.get("isco_code") or "7422"
        cal = get_calibration(isco)
        risk = cal["calibrated_score"]

        # High-risk skills dim (desaturate)
        color = _skill_color(skill)
        if risk > 0.65:
            color = _COLOR_AT_RISK
            opacity = 0.6
        elif risk > 0.45:
            opacity = 0.8
        else:
            opacity = 1.0

        node_r = _EVIDENCE_RADIUS.get(skill.get("evidence_type", "self_report"), 8)
        if skill.get("is_heritage_skill"):
            node_r += 3  # Heritage skills glow larger

        node_id = f"skill_{i}"
        nodes.append({
            "id": node_id,
            "type": "current",
            "label": skill.get("skill_label", "Unknown"),
            "x": x,
            "y": y,
            "r": node_r,
            "color": color,
            "opacity": opacity,
            "isco_code": isco,
            "risk_pct": cal["calibrated_pct"],
            "is_heritage": skill.get("is_heritage_skill", False),
            "evidence_type": skill.get("evidence_type", "self_report"),
            "glow": skill.get("is_heritage_skill", False),
        })
        seen_isco.add(isco)

    # Place adjacent/reachable skills in the outer ring
    for i, skill in enumerate(receipts[:6]):  # top 6 skills drive adjacency
        isco = skill.get("isco_code") or "7422"
        major = str(isco)[0]
        adjacent_list = _ADJACENT_ISCO.get(major, [])

        for j, (adj_isco, adj_label, adj_risk) in enumerate(adjacent_list[:3]):
            key = f"{adj_isco}"
            if key in adjacent_added:
                continue
            adjacent_added.add(key)

            angle = _stable_angle(adj_label, i * 10 + j, len(receipts) * 3)
            x = round(_CX + _R_ADJACENT * math.cos(angle), 1)
            y = round(_CY + _R_ADJACENT * math.sin(angle), 1)

            adj_cal = get_calibration(adj_isco)
            node_id = f"adj_{adj_isco}_{j}"

            nodes.append({
                "id": node_id,
                "type": "adjacent",
                "label": adj_label,
                "x": x,
                "y": y,
                "r": 6,
                "color": _COLOR_ADJACENT,
                "opacity": 0.7,
                "isco_code": adj_isco,
                "risk_pct": adj_cal["calibrated_pct"],
                "is_heritage": False,
                "evidence_type": None,
                "glow": False,
                "learning_time": "3–9 months",
                "source_skill_id": f"skill_{i}",
            })

            # Edge from source skill to adjacent
            edges.append({
                "from": f"skill_{i}",
                "to": node_id,
                "type": "pathway",
                "color": "#2a3f5a",
                "opacity": 0.4,
                "dashed": True,
            })

    # Draw edges between related core skills (same ISCO major group)
    for i, n1 in enumerate(nodes):
        if n1["type"] != "current":
            continue
        for j, n2 in enumerate(nodes):
            if j <= i or n2["type"] != "current":
                continue
            if str(n1.get("isco_code", "0"))[0] == str(n2.get("isco_code", "1"))[0]:
                edges.append({
                    "from": n1["id"],
                    "to": n2["id"],
                    "type": "related",
                    "color": "#2a3f5a",
                    "opacity": 0.25,
                    "dashed": False,
                })

    # Summary stats
    core_nodes = [n for n in nodes if n["type"] == "current"]
    at_risk = sum(1 for n in core_nodes if n["color"] == _COLOR_AT_RISK)
    durable = sum(1 for n in core_nodes if n["risk_pct"] < 30)
    heritage_count = sum(1 for n in core_nodes if n["is_heritage"])

    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"width": 600, "height": 600, "cx": _CX, "cy": _CY},
        "summary": {
            "total_skills": len(core_nodes),
            "at_risk_count": at_risk,
            "durable_count": durable,
            "heritage_count": heritage_count,
            "adjacent_pathways": len(adjacent_added),
        },
        "legend": [
            {"color": _COLOR_HERITAGE,  "label": "Heritage Skill"},
            {"color": _COLOR_TECHNICAL, "label": "Technical Skill"},
            {"color": _COLOR_SOCIAL,    "label": "Social/Community Skill"},
            {"color": _COLOR_DIGITAL,   "label": "Digital Skill"},
            {"color": _COLOR_AT_RISK,   "label": "High Automation Risk"},
            {"color": _COLOR_ADJACENT,  "label": "Adjacent — reachable"},
        ],
    }
