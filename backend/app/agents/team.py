"""Gemini agent team. Owner: agents.

Contract: docs/api-contract.md (POST /api/explain).
TODO: run demand/competition/access/cost specialists in parallel on the top 5,
then the challenger, then the reporter, using GEMINI_API_KEY. Agents may only
use numbers present in the Analysis. Keep the data-only fallback below.
"""
import os

from app.models import AgentEvent, Analysis, Explanation, Verdict

SPECIALISTS = ["demand", "competition", "access", "cost"]


def explain(analysis: Analysis) -> Explanation:
    # Placeholder: data-only fallback. Use Gemini when os.getenv("GEMINI_API_KEY") is set.
    _ = os.getenv("GEMINI_API_KEY")
    verdicts = [
        Verdict(
            rank=p.rank,
            verdict=(
                f"Pick {p.rank} scores {p.scores.total}/100 overall "
                f"(demand {p.scores.demand}, competition {p.scores.competition}, "
                f"access {p.scores.access}, cost {p.scores.cost})."
            ),
            risks=["Cost is a proxy based on distance from the centre."],
        )
        for p in analysis.shortlist
    ]
    log = [
        AgentEvent(agent=a, status="done", summary="Data-only mode.")
        for a in [*SPECIALISTS, "challenger", "reporter"]
    ]
    return Explanation(ai_mode="data-only", agent_log=log, verdicts=verdicts)
