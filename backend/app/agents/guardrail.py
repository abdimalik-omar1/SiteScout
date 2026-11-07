"""Numeric guardrail: agent text may only quote numbers present in the input.

Enforced in code, not by prompt. Any verdict/risk containing a number that is
not (within rounding tolerance) one of the pick's own numbers is rejected and
replaced by a deterministic data-only verdict.
"""
import re

from app.models import Analysis, Pick, Verdict

# Methodology constants that may be mentioned without false-failing:
# cost weights, base weights, 0/100 score bounds, shortlist size, radii/grid.
_CONSTANTS = {30, 18, 8, 40, 25, 20, 100, 0, 5, 600, 400, 500, 300, 800, 1000, 350}

_NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def _pick_numbers(pick: Pick) -> set[float]:
    nums: set[float] = {float(pick.rank)}
    s = pick.scores
    nums.update(float(v) for v in (s.demand, s.competition, s.access, s.cost, s.total))
    for ev in pick.evidence:
        nums.add(float(ev.value))
        nums.add(float(ev.cork_median))
    for c in pick.nearest_competitors:
        nums.add(float(c.distance_m))
    nums.add(float(len(pick.nearest_competitors)))
    return nums


def allowed_numbers(analysis: Analysis, rank: int | None = None) -> set[float]:
    """All numbers an agent may cite for one pick (rank) or every pick (None)."""
    allowed = {float(c) for c in _CONSTANTS}
    for pick in analysis.shortlist:
        if rank is None or pick.rank == rank:
            allowed |= _pick_numbers(pick)
    return allowed


def extract_numbers(text: str) -> list[float]:
    """Pull numeric tokens from free text.

    Handles ints, decimals and comma thousands ('1,840' -> 1840). '%', '€',
    'm', 'km' are ignored but the number is kept ('62%' -> 62). '#1' and
    'pick 1' yield 1. Ordinals like '1st'/'14th' are kept as numbers (strict:
    deliberately not exempted so '14th' cannot smuggle in a figure). Signs are
    ignored ('-5' -> 5); ranges '2-3' give 2 and 3.
    """
    out: list[float] = []
    for m in _NUM_RE.finditer(text):
        out.append(float(m.group(0).replace(",", "")))
    return out


def numbers_supported(text: str, allowed: set[float], tol: float = 0.51) -> bool:
    """True iff every number in text is within tol of some allowed number."""
    return all(
        any(abs(n - a) <= tol for a in allowed) for n in extract_numbers(text)
    )


def _fmt(x: float) -> str:
    return f"{x:g}"


def fallback_verdict(pick: Pick) -> Verdict:
    """Deterministic verdict built only from the pick's own numbers."""
    s = pick.scores
    ev = {e.metric: e for e in pick.evidence}
    verdict = (
        f"Pick {pick.rank} scores {s.total}/100 overall "
        f"(demand {s.demand}, competition {s.competition}, "
        f"access {s.access}, cost {s.cost})."
    )
    strongest = max(
        (("demand", s.demand), ("competition", s.competition),
         ("access", s.access), ("cost", s.cost)),
        key=lambda kv: kv[1],
    )
    weakest = min(
        (("demand", s.demand), ("competition", s.competition),
         ("access", s.access), ("cost", s.cost)),
        key=lambda kv: kv[1],
    )
    verdict += f" Strongest factor: {strongest[0]} at {strongest[1]}."
    risks = [
        f"Weakest factor is {weakest[0]} at {weakest[1]} out of 100.",
        "Cost is a distance-from-centre proxy, not real rent data.",
    ]
    comp = ev.get("competitors_400m")
    if comp is not None:
        risks.append(
            f"{_fmt(comp.value)} competitors within 400 m "
            f"(Cork median {_fmt(comp.cork_median)})."
        )
    if pick.nearest_competitors:
        nearest = min(pick.nearest_competitors, key=lambda c: c.distance_m)
        risks.append(
            f"Nearest listed competitor is {nearest.distance_m} m away."
        )
    return Verdict(rank=pick.rank, verdict=verdict, risks=risks)


def check_verdict(verdict: Verdict, analysis: Analysis) -> Verdict:
    """Return verdict if all its numbers are supported, else the fallback."""
    allowed = allowed_numbers(analysis, verdict.rank)
    ok = numbers_supported(verdict.verdict, allowed) and all(
        numbers_supported(r, allowed) for r in verdict.risks
    )
    if ok:
        return verdict
    for pick in analysis.shortlist:
        if pick.rank == verdict.rank:
            return fallback_verdict(pick)
    # Unknown rank: nothing to build from; return a number-free stub.
    return Verdict(
        rank=verdict.rank,
        verdict="No data-backed verdict available for this pick.",
        risks=["Cost is a distance-from-centre proxy, not real rent data."],
    )
