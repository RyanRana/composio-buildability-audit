"""Structured output schema for the app-research pipeline.

Every app in the 100-app set is reduced to one AppFinding. The schema is the
contract shared by (a) the research agent, (b) the verification agent, and
(c) the HTML renderer, so all three speak the same language.
"""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

SelfServe = Literal[
    "self-serve-free",     # dev gets working creds themselves, free
    "self-serve-trial",    # creds available on a free trial / sandbox
    "gated-paid",          # needs a paid plan tier to get creds
    "gated-approval",      # needs app review / production-access approval
    "gated-partnership",   # needs contact-sales / partner program
    "no-public-api",       # no public API at all
]

Verdict = Literal[
    "buildable-now",            # could be an agent toolkit today
    "buildable-with-friction",  # possible, but auth/approval/rate friction
    "blocked",                  # partnership-only or no public API
]

Confidence = Literal["high", "medium", "low"]


class ApiSurface(BaseModel):
    type: str = Field(description="REST | GraphQL | REST+GraphQL | SOAP | gRPC | other")
    breadth: Literal["broad", "moderate", "narrow", "very broad"]
    has_mcp: bool = Field(description="Does an official / well-known MCP server exist?")
    notes: str = ""


class AppFinding(BaseModel):
    app: str
    category: str
    one_liner: str
    auth_methods: List[str]
    self_serve_status: SelfServe
    self_serve_notes: str
    api_surface: ApiSurface
    buildability_verdict: Verdict
    main_blocker: str
    confidence: Confidence
    evidence_urls: List[str]
    # Filled by the verification pass:
    verified: Optional[bool] = None
    verify_notes: Optional[str] = None
    verify_corrections: Optional[dict] = None


class VerifyResult(BaseModel):
    app: str
    agrees: bool = Field(description="Does independent research agree with the finding?")
    disagreements: List[str] = Field(default_factory=list)
    corrected_self_serve_status: Optional[str] = None
    corrected_verdict: Optional[str] = None
    notes: str = ""
    evidence_urls: List[str] = Field(default_factory=list)
