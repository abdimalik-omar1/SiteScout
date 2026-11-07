import json

import pytest

from app.agents import roles
from app.data.sample import sample_analysis
from app.models import Brief, Verdict

BRIEF = Brief(business_type="cafe", budget="tight", customers=["students", "office_workers"])


@pytest.fixture
def analysis():
    return sample_analysis(BRIEF)


def _recorder(response):
    calls = []

    def llm(system, prompt, schema):
        calls.append((system, prompt, schema))
        return response(prompt) if callable(response) else response

    return llm, calls


def _findings(analysis):
    return {"findings": [{"rank": p.rank, "finding": f"f{p.rank}"} for p in analysis.shortlist]}


def _check_schema(s):
    assert s["type"] == "object"
    assert "$ref" not in json.dumps(s)
    assert "additionalProperties" not in json.dumps(s)
    assert s["required"] and set(s["required"]) <= set(s["properties"])


def test_specialists_list():
    assert roles.SPECIALISTS == ["demand", "competition", "access", "cost"]


def test_demand_prompt(analysis):
    llm, calls = _recorder(_findings(analysis))
    out = roles.run_specialist("demand", analysis, llm)
    assert out == _findings(analysis)
    system, prompt, schema = calls[0]
    assert len(calls) == 1
    assert system == roles.SYSTEM_RULES
    assert "residents_600m" in prompt and "offices_500m" in prompt
    assert "Cork median 920" in prompt
    assert "students" in prompt
    assert "bus_stops_400m" not in prompt
    assert "competitors_400m" not in prompt
    assert "distance_centre_km" not in prompt
    _check_schema(schema)


def test_competition_prompt(analysis):
    llm, calls = _recorder(_findings(analysis))
    roles.run_specialist("competition", analysis, llm)
    prompt = calls[0][1]
    assert "competitors_400m" in prompt
    assert "Sample Competitor A" in prompt and "m away" in prompt
    assert "residents_600m" not in prompt and "bus_stops_400m" not in prompt
    assert "distance_centre_km" not in prompt


def test_access_prompt(analysis):
    llm, calls = _recorder(_findings(analysis))
    roles.run_specialist("access", analysis, llm)
    prompt = calls[0][1]
    assert "bus_stops_400m" in prompt
    assert "residents_600m" not in prompt and "offices_500m" not in prompt
    assert "competitors_400m" not in prompt


def test_cost_prompt(analysis):
    llm, calls = _recorder(_findings(analysis))
    roles.run_specialist("cost", analysis, llm)
    prompt = calls[0][1]
    assert "distance_centre_km" in prompt
    assert "proxy" in prompt and "tight" in prompt
    assert "residents_600m" not in prompt and "offices_500m" not in prompt
    assert "bus_stops_400m" not in prompt and "competitors_400m" not in prompt
    assert "Sample Competitor" not in prompt


def test_unknown_specialist(analysis):
    with pytest.raises(ValueError):
        roles.run_specialist("nope", analysis, lambda *a: {})


def test_challenger(analysis):
    spec = {n: _findings(analysis) for n in roles.SPECIALISTS}
    resp = {"challenges": [{"rank": 1, "risks": ["r"]}]}
    llm, calls = _recorder(resp)
    assert roles.run_challenger(analysis, spec, llm) == resp
    _, prompt, schema = calls[0]
    for m in ("residents_600m", "bus_stops_400m", "competitors_400m", "distance_centre_km"):
        assert m in prompt
    assert "f1" in prompt
    _check_schema(schema)


def _verdicts(ranks):
    return {"verdicts": [{"rank": r, "verdict": f"v{r}", "risks": ["x"]} for r in ranks]}


def test_reporter_ok(analysis):
    llm, calls = _recorder(_verdicts(range(1, 6)))
    out = roles.run_reporter(analysis, {}, {"challenges": []}, llm)
    assert len(out) == 5 and all(isinstance(v, Verdict) for v in out)
    assert [v.rank for v in out] == [1, 2, 3, 4, 5]
    _check_schema(calls[0][2])


def test_reporter_missing_rank(analysis):
    llm, _ = _recorder(_verdicts([1, 2, 3, 4]))
    with pytest.raises(ValueError):
        roles.run_reporter(analysis, {}, {"challenges": []}, llm)


def test_one_line(analysis):
    assert len(roles.one_line("demand", _findings(analysis))) <= 160
    long = {"findings": [{"rank": 1, "finding": "x" * 500}]}
    assert len(roles.one_line("demand", long)) <= 160
    assert len(roles.one_line("challenger", {"challenges": [{"rank": 1, "risks": ["a", "b"]}]})) <= 160
    vs = [Verdict(rank=1, verdict="y" * 400, risks=[])]
    assert len(roles.one_line("reporter", vs)) <= 160
    assert roles.one_line("reporter", None)
