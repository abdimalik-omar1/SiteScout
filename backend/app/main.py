from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.team import explain
from app.models import Analysis, Brief, Explanation
from app.scoring.engine import analyze

app = FastAPI(title="SiteScout API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/analyze", response_model=Analysis)
def analyze_route(brief: Brief) -> Analysis:
    return analyze(brief)


@app.post("/api/explain", response_model=Explanation)
def explain_route(analysis: Analysis) -> Explanation:
    return explain(analysis)
