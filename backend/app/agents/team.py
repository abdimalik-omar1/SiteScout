"""Gemini agent team. Owner: agents.

Contract: docs/api-contract.md (POST /api/explain).

Flow: 4 specialists in parallel -> challenger -> reporter -> number guardrail.
Any failure degrades to data-only text for the affected part; explain() never raises.
"""
from concurrent.futures import ThreadPoolExecutor

from app.agents import gemini
from app.agents.guardrail import check_verdict, fallback_verdict
from app.agents.roles import (
    SPECIALISTS,
    Llm,
    one_line,
    run_challenger,
    run_reporter,
    run_specialist,
)
from app.models import AgentEvent, Analysis, Explanation, Verdict


def _data_only(analysis: Analysis, note: str = "Data-only mode.") -> Explanation:
    verdicts = [fallback_verdict(p) for p in analysis.shortlist]
    log = [
        AgentEvent(agent=a, status="done", summary=note)
        for a in [*SPECIALISTS, "challenger", "reporter"]
    ]
    return Explanation(ai_mode="data-only", agent_log=log, verdicts=verdicts)


def explain(analysis: Analysis, llm: Llm | None = None) -> Explanation:
    if llm is None:
        if not gemini.is_configured():
            return _data_only(analysis)
        llm = gemini.generate_json

    log: list[AgentEvent] = []

    # 1. Specialists, in parallel.
    outputs: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(SPECIALISTS)) as pool:
        futures = {n: pool.submit(run_specialist, n, analysis, llm) for n in SPECIALISTS}
        for name, fut in futures.items():
            try:
                outputs[name] = fut.result()
                log.append(AgentEvent(agent=name, status="done", summary=one_line(name, outputs[name])))
            except Exception as exc:  # noqa: BLE001 - degrade, never crash the demo
                log.append(AgentEvent(agent=name, status="error", summary=f"Failed: {exc}"[:160]))
    if not outputs:
        return _data_only(analysis, "AI unavailable; data-only.")

    # 2. Challenger.
    challenge: dict = {"challenges": []}
    try:
        challenge = run_challenger(analysis, outputs, llm)
        log.append(AgentEvent(agent="challenger", status="done", summary=one_line("challenger", challenge)))
    except Exception as exc:  # noqa: BLE001
        log.append(AgentEvent(agent="challenger", status="error", summary=f"Failed: {exc}"[:160]))

    # 3. Reporter, then the number guardrail on every verdict.
    verdicts: list[Verdict]
    try:
        raw = run_reporter(analysis, outputs, challenge, llm)
        verdicts = [check_verdict(v, analysis) for v in raw]
        swapped = sum(1 for a, b in zip(raw, verdicts) if a is not b)
        note = one_line("reporter", verdicts)
        if swapped:
            note = f"{note} ({swapped} swapped to data-only by number check)"[:160]
        log.append(AgentEvent(agent="reporter", status="done", summary=note))
    except Exception as exc:  # noqa: BLE001
        verdicts = [fallback_verdict(p) for p in analysis.shortlist]
        log.append(AgentEvent(agent="reporter", status="error", summary=f"Failed: {exc}"[:160]))

    verdicts.sort(key=lambda v: v.rank)
    return Explanation(ai_mode="gemini", agent_log=log, verdicts=verdicts)
