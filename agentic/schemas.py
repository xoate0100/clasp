"""Typed contracts for agent handoffs and run logging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChangeRecord(BaseModel):
    path: str
    action: Literal["create", "update", "delete"] = "update"
    summary: str = ""


class AgentRunRecord(BaseModel):
    """Common base contract for every agent role (Liskov substitution)."""

    agent: str
    ok: bool
    changes: list[ChangeRecord] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphRunRecord(BaseModel):
    run_id: str
    plan_id: str = ""
    phase_id: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    agents: list[AgentRunRecord] = Field(default_factory=list)
    outcome: Literal["clean", "findings", "needs_decision", "escalated", "fail"] = "fail"


class DecisionRow(BaseModel):
    decision_id: str
    status: Literal["proposed", "accepted", "deprecated", "superseded"]
    decision_basis: str
    supersedes: Optional[str] = None
    forbidden_resurrection_in: list[str]
    resurrection_trigger_keywords: list[str]
    reopen_requires: str = ""


class PostureSnapshot(BaseModel):
    phase_id: str = ""
    phase_name: str = ""
    active_decisions: list[DecisionRow] = Field(default_factory=list)
    open_decisions: list[str] = Field(default_factory=list)
    forbidden_keywords: list[str] = Field(default_factory=list)


class ChangeProposalSet(BaseModel):
    agent: str = "implementer"
    proposals: list[ChangeRecord] = Field(default_factory=list)
    ok: bool = True


class ValidatorResult(BaseModel):
    check: str
    ok: bool
    detail: str = ""


class ValidatorResultSet(BaseModel):
    agent: str = "validator"
    results: list[ValidatorResult] = Field(default_factory=list)
    ok: bool = True


class ReviewFinding(BaseModel):
    source: str
    id: str
    message: str
    severity: Literal["info", "warn", "block"] = "warn"


class ReviewReport(BaseModel):
    agent: str = "reviewer"
    findings: list[ReviewFinding] = Field(default_factory=list)
    ok: bool = True
    route: Literal["clean", "findings", "needs_decision"] = "clean"


class DecisionProposal(BaseModel):
    agent: str = "decision_proposer"
    row: DecisionRow
    ok: bool = True
