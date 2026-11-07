"""The scoring engine must be deterministic and respect the contract.

Run from backend/: ../.venv-backend/bin/python -m pytest  (or pytest with app importable).
"""
from app.config import SHORTLIST_MIN_SPACING_M, SHORTLIST_SIZE
from app.models import Brief
from app.scoring.engine import _haversine_m, analyze

BRIEF = Brief(business_type="cafe", budget="tight", customers=["students", "office_workers"])
# Golden shortlist for BRIEF against the committed cache. A surprise diff here
# means the ranking drifted; update only on a deliberate scoring change.
GOLDEN = ["r9c4", "r2c23", "r9c29", "r6c7", "r7c5"]


def test_live_mode():
    assert analyze(BRIEF).data_mode == "live"  # cache present => real data


def test_repeatable():
    a = [p.cell_id for p in analyze(BRIEF).shortlist]
    b = [p.cell_id for p in analyze(BRIEF).shortlist]
    assert a == b


def test_matches_golden():
    assert [p.cell_id for p in analyze(BRIEF).shortlist] == GOLDEN


def test_shortlist_invariants():
    a = analyze(BRIEF)
    sl = a.shortlist
    assert len(sl) == SHORTLIST_SIZE
    assert [p.rank for p in sl] == [1, 2, 3, 4, 5]
    assert len(a.cells) > 100  # every grid cell is returned for the map
    for i, p in enumerate(sl):
        assert 0 <= p.scores.total <= 100
        assert len(p.evidence) == 5  # contract: 5 evidence rows
        for j in range(i):
            d = _haversine_m(p.lng, p.lat, sl[j].lng, sl[j].lat)
            assert d >= SHORTLIST_MIN_SPACING_M


def test_budget_changes_ranking():
    tight = [p.cell_id for p in analyze(Brief(business_type="cafe", budget="tight", customers=["residents"])).shortlist]
    flex = [p.cell_id for p in analyze(Brief(business_type="cafe", budget="flexible", customers=["residents"])).shortlist]
    assert tight != flex
