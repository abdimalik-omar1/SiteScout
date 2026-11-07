from app.agents.guardrail import (
    allowed_numbers, check_verdict, extract_numbers, fallback_verdict,
    numbers_supported,
)
from app.data.sample import sample_analysis
from app.models import Brief, Verdict


def _analysis():
    return sample_analysis(Brief(business_type="cafe", budget="moderate", customers=["students"]))


def test_allowed_contains_evidence_and_scores():
    a = _analysis()
    allowed = allowed_numbers(a, 1)
    p = a.shortlist[0]
    for e in p.evidence:
        assert e.value in allowed and e.cork_median in allowed
    assert float(p.scores.total) in allowed
    assert float(p.nearest_competitors[0].distance_m) in allowed
    assert {30.0, 18.0, 8.0, 100.0, 600.0} <= allowed


def test_extract_numbers():
    assert extract_numbers("1,840 people, 62%, 1.2 km, #1") == [1840, 62, 1.2, 1]


def test_invented_numbers_fail():
    allowed = allowed_numbers(_analysis(), 1)
    assert not numbers_supported("Rent is about €2,400 a month", allowed)
    assert not numbers_supported("Expect footfall of 5,000", allowed)
    assert not numbers_supported("14 vs 9", {9.0})  # 14 unsupported


def test_honest_sentence_passes():
    a = _analysis()
    p = a.shortlist[0]
    res = next(e for e in p.evidence if e.metric == "residents_600m")
    text = f"{res.value:g} residents within 600 m vs a Cork median of {res.cork_median:g}; total {p.scores.total}/100."
    assert numbers_supported(text, allowed_numbers(a, 1))
    assert numbers_supported("1.2 vs", {1.24})


def test_fallback_always_passes():
    a = _analysis()
    for p in a.shortlist:
        v = fallback_verdict(p)
        allowed = allowed_numbers(a, p.rank)
        assert numbers_supported(v.verdict, allowed)
        assert all(numbers_supported(r, allowed) for r in v.risks)
        assert any("distance-from-centre proxy" in r for r in v.risks)


def test_check_verdict_swaps_bad_keeps_good():
    a = _analysis()
    bad = Verdict(rank=1, verdict="Great spot, rent €2,400 a month.", risks=[])
    out = check_verdict(bad, a)
    assert out == fallback_verdict(a.shortlist[0])
    bad_risk = Verdict(rank=2, verdict="Solid.", risks=["footfall of 5,000"])
    assert check_verdict(bad_risk, a) == fallback_verdict(a.shortlist[1])
    p = a.shortlist[0]
    good = Verdict(rank=1, verdict=f"Total {p.scores.total} out of 100.", risks=["Cost is a proxy."])
    assert check_verdict(good, a) is good
