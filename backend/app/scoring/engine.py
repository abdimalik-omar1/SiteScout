"""Deterministic scoring engine. Owner: data/scoring.

Contract: docs/api-contract.md (POST /api/analyze). No AI in this module.
TODO: build the ~350 m grid, pull CSO + OSM data, compute the four sub-scores
(weights: demand 40, competition 25, access 20, cost 30/18/8 by budget),
rescale to 100, and pick the top 5 cells at least 600 m apart.
"""
from app.data.sample import sample_analysis
from app.models import Analysis, Brief


def analyze(brief: Brief) -> Analysis:
    # Placeholder: swap for the real pipeline, falling back to sample on failure.
    return sample_analysis(brief)
