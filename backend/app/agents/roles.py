"""Agent roles: specialists, challenger, reporter. Owner: agents.

The LLM is injected as ``llm(system, prompt, json_schema) -> dict`` so this
module never touches the network. Calls are synchronous (thread-pool safe).
"""
import json
from typing import Callable

from app.models import Analysis, Pick, Verdict

Llm = Callable[[str, str, dict], dict]

SPECIALISTS = ["demand", "competition", "access", "cost"]

SYSTEM_RULES = (
    "You are part of a small analyst team helping a first-time founder choose a "
    "shop location in Cork, Ireland.\n"
    "Rules:\n"
    "- Use ONLY numbers present in the supplied data. Never invent rents, "
    "footfall, prices or revenue.\n"
    "- Scores are relative to other Cork cells (0-100); they are not forecasts.\n"
    "- The cost score is a proxy based on distance from the city centre; there "
    "is no real rent data.\n"
    "- OpenStreetMap counts may be incomplete.\n"
    "- Be concise: 2-3 sentences per finding. Write in plain English for a "
    "first-time founder, no jargon.\n"
    "- Always compare a value with its Cork median when both are given."
)

_FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "finding": {"type": "string"},
                },
                "required": ["rank", "finding"],
            },
        }
    },
    "required": ["findings"],
}

_CHALLENGE_SCHEMA = {
    "type": "object",
    "properties": {
        "challenges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "risks": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["rank", "risks"],
            },
        }
    },
    "required": ["challenges"],
}

_VERDICTS_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "verdict": {"type": "string"},
                    "risks": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["rank", "verdict", "risks"],
            },
        }
    },
    "required": ["verdicts"],
}

# specialist -> (evidence metrics, score key, focus text)
_SLICES = {
    "demand": (
        ["residents_600m", "offices_500m"],
        "demand",
        "Assess customer demand: nearby residents and offices, and fit with the "
        "target customers.",
    ),
    "competition": (
        ["competitors_400m"],
        "competition",
        "Assess competition: how many rivals are nearby and how close the "
        "nearest ones are. A higher competition score means less pressure.",
    ),
    "access": (
        ["bus_stops_400m"],
        "access",
        "Assess accessibility using bus stops within 400 m.",
    ),
    "cost": (
        ["distance_centre_km"],
        "cost",
        "Assess likely affordability against the budget. IMPORTANT: cost is only "
        "a distance-from-centre proxy; there are no real rents. Do not quote "
        "any rent figure.",
    ),
}


def _brief_text(analysis: Analysis) -> str:
    b = analysis.brief
    return (
        f"Business: {b.business_type}; budget: {b.budget}; "
        f"target customers: {', '.join(b.customers) or 'not specified'}; city: {b.city}."
    )


def _ev_line(row) -> str:
    return f"{row.label} ({row.metric}): {row.value:g} (Cork median {row.cork_median:g})"


def _pick_slice(name: str, pick: Pick) -> str:
    metrics, score_key, _ = _SLICES[name]
    lines = [f"Pick rank {pick.rank} (cell {pick.cell_id}):"]
    for row in pick.evidence:
        if row.metric in metrics:
            lines.append("  - " + _ev_line(row))
    if name == "competition":
        for c in pick.nearest_competitors:
            lines.append(f"  - Nearest competitor: {c.name}, {c.distance_m} m away")
    lines.append(f"  - {score_key} score: {getattr(pick.scores, score_key)}/100")
    return "\n".join(lines)


def run_specialist(name: str, analysis: Analysis, llm: Llm) -> dict:
    """One LLM call covering every shortlist pick, using only this specialist's evidence."""
    if name not in _SLICES:
        raise ValueError(f"unknown specialist: {name}")
    focus = _SLICES[name][2]
    parts = [
        f"Role: {name} specialist. {focus}",
        _brief_text(analysis),
    ]
    if name == "demand":
        parts.append(
            "Target customers to consider: "
            + (", ".join(analysis.brief.customers) or "not specified")
        )
    if name == "cost":
        parts.append(f"Budget: {analysis.brief.budget}.")
    parts.append("Evidence per shortlisted pick:")
    parts.extend(_pick_slice(name, p) for p in analysis.shortlist)
    parts.append(
        "Return one finding (2-3 sentences) for EVERY pick rank listed above."
    )
    return llm(SYSTEM_RULES, "\n\n".join(parts), _FINDINGS_SCHEMA)


def _full_evidence(analysis: Analysis) -> str:
    out = []
    for p in analysis.shortlist:
        s = p.scores
        out.append(
            f"Pick rank {p.rank} (cell {p.cell_id}) scores: total {s.total}, "
            f"demand {s.demand}, competition {s.competition}, access {s.access}, cost {s.cost}"
        )
        out.extend("  - " + _ev_line(r) for r in p.evidence)
        for c in p.nearest_competitors:
            out.append(f"  - Nearest competitor: {c.name}, {c.distance_m} m away")
    return "\n".join(out)


def run_challenger(analysis: Analysis, specialist_outputs: dict[str, dict], llm: Llm) -> dict:
    prompt = "\n\n".join([
        "Role: challenger. Review the specialists' findings against the evidence. "
        "Flag any claim that is unsupported by the data or overreaches (e.g. "
        "treats scores as forecasts, or the cost proxy as real rent). For every "
        "pick rank give the main risks.",
        _brief_text(analysis),
        "Full evidence:\n" + _full_evidence(analysis),
        "Specialist findings (JSON):\n" + json.dumps(specialist_outputs, indent=1),
    ])
    return llm(SYSTEM_RULES, prompt, _CHALLENGE_SCHEMA)


def run_reporter(
    analysis: Analysis,
    specialist_outputs: dict[str, dict],
    challenge: dict,
    llm: Llm,
) -> list[Verdict]:
    prompt = "\n\n".join([
        "Role: reporter. For EVERY pick rank write a plain-English verdict "
        "(2-3 sentences) and a short list of risks, using the specialists' "
        "findings and the challenger's objections. Drop any claim the "
        "challenger showed to be unsupported.",
        _brief_text(analysis),
        "Scores and evidence:\n" + _full_evidence(analysis),
        "Specialist findings (JSON):\n" + json.dumps(specialist_outputs, indent=1),
        "Challenger (JSON):\n" + json.dumps(challenge, indent=1),
    ])
    result = llm(SYSTEM_RULES, prompt, _VERDICTS_SCHEMA)
    by_rank = {}
    for v in (result or {}).get("verdicts", []) or []:
        try:
            by_rank[int(v["rank"])] = v
        except (KeyError, TypeError, ValueError):
            continue
    verdicts: list[Verdict] = []
    for p in analysis.shortlist:
        v = by_rank.get(p.rank)
        if v is None:
            raise ValueError(f"reporter output missing rank {p.rank}")
        verdicts.append(
            Verdict(
                rank=p.rank,
                verdict=str(v.get("verdict", "")),
                risks=[str(r) for r in (v.get("risks") or [])],
            )
        )
    return verdicts


def _clip(text: str, n: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def one_line(role: str, output) -> str:
    """Short human summary (<= 160 chars) of a role's output for the UI agent_log."""
    try:
        if isinstance(output, list):  # reporter verdicts
            first = output[0].verdict if output else ""
            return _clip(f"Wrote {len(output)} verdicts. #1: {first}")
        if isinstance(output, dict):
            if "findings" in output:
                items = sorted(output["findings"], key=lambda f: f.get("rank", 99))
                first = items[0]["finding"] if items else ""
                return _clip(f"{len(items)} findings. #1: {first}")
            if "challenges" in output:
                items = output["challenges"]
                n = sum(len(c.get("risks", [])) for c in items)
                first = next((r for c in items for r in c.get("risks", [])), "")
                return _clip(f"Flagged {n} risks across {len(items)} picks. {first}")
        return _clip(f"{role}: done")
    except Exception:
        return _clip(f"{role}: done")
