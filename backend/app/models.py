"""Pydantic models implementing docs/api-contract.md. Change the contract doc first."""
from typing import Literal

from pydantic import BaseModel, Field

BusinessType = Literal["cafe", "barber", "gym", "restaurant", "convenience"]
Budget = Literal["tight", "moderate", "flexible"]
Customer = Literal["students", "office_workers", "residents", "visitors"]


class Brief(BaseModel):
    business_type: BusinessType
    budget: Budget
    customers: list[Customer] = Field(default_factory=list)
    city: Literal["Cork"] = "Cork"


class Scores(BaseModel):
    demand: int
    competition: int
    access: int
    cost: int
    total: int


class Cell(BaseModel):
    id: str
    lat: float
    lng: float
    scores: Scores


class EvidenceRow(BaseModel):
    metric: str
    label: str
    value: float
    cork_median: float


class Competitor(BaseModel):
    name: str
    distance_m: int


class Pick(BaseModel):
    rank: int
    cell_id: str
    lat: float
    lng: float
    scores: Scores
    evidence: list[EvidenceRow]
    nearest_competitors: list[Competitor]


class Analysis(BaseModel):
    data_mode: Literal["live", "sample"]
    brief: Brief
    cells: list[Cell]
    shortlist: list[Pick]


AgentName = Literal[
    "demand", "competition", "access", "cost", "challenger", "reporter"
]


class AgentEvent(BaseModel):
    agent: AgentName
    status: Literal["running", "done", "error"]
    summary: str = ""


class Verdict(BaseModel):
    rank: int
    verdict: str
    risks: list[str]


class Explanation(BaseModel):
    ai_mode: Literal["gemini", "data-only"]
    agent_log: list[AgentEvent]
    verdicts: list[Verdict]
