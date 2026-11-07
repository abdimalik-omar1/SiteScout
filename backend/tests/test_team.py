from app.agents import team
from app.data.sample import sample_analysis
from app.models import Brief

BRIEF = Brief(business_type="cafe", budget="tight", customers=["students", "office_workers"])


def fake_llm_ok(system, prompt, schema):
    props = schema.get("properties", {})
    if "findings" in props:
        return {"findings": [{"rank": r, "finding": "Looks solid."} for r in range(1, 6)]}
    if "challenges" in props:
        return {"challenges": [{"rank": r, "risks": ["Cost is a proxy."]} for r in range(1, 6)]}
    return {"verdicts": [{"rank": r, "verdict": "Good pick.", "risks": ["Cost is a proxy."]} for r in range(1, 6)]}


def test_no_key_is_data_only(monkeypatch):
    monkeypatch.setattr(team.gemini, "is_configured", lambda: False)
    out = team.explain(sample_analysis(BRIEF))
    assert out.ai_mode == "data-only" and len(out.verdicts) == 5


def test_full_pipeline_with_fake_llm():
    out = team.explain(sample_analysis(BRIEF), llm=fake_llm_ok)
    assert out.ai_mode == "gemini"
    assert [e.agent for e in out.agent_log] == [
        "demand", "competition", "access", "cost", "challenger", "reporter"
    ]
    assert all(e.status == "done" for e in out.agent_log)
    assert [v.rank for v in out.verdicts] == [1, 2, 3, 4, 5]


def test_invented_numbers_are_swapped():
    def llm(system, prompt, schema):
        if "verdicts" in schema.get("properties", {}):
            return {"verdicts": [
                {"rank": r, "verdict": "Rent is about €2,400 a month.", "risks": ["x"]}
                for r in range(1, 6)
            ]}
        return fake_llm_ok(system, prompt, schema)

    out = team.explain(sample_analysis(BRIEF), llm=llm)
    assert all("2,400" not in v.verdict for v in out.verdicts)
    assert "swapped" in out.agent_log[-1].summary


def test_all_failures_degrade_to_data_only():
    def boom(system, prompt, schema):
        raise RuntimeError("down")

    out = team.explain(sample_analysis(BRIEF), llm=boom)
    assert out.ai_mode == "data-only" and len(out.verdicts) == 5


def test_reporter_failure_keeps_response_valid():
    def llm(system, prompt, schema):
        if "verdicts" in schema.get("properties", {}):
            raise RuntimeError("down")
        return fake_llm_ok(system, prompt, schema)

    out = team.explain(sample_analysis(BRIEF), llm=llm)
    assert out.agent_log[-1].status == "error" and len(out.verdicts) == 5
