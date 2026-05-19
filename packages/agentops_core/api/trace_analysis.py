"""POST /trace-analyses — runs Trace Analyzer on an AnomalySignal."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from agentops_core.config import Settings, get_settings
from agentops_core.database import (
    get_langfuse_client,
    get_session,
)
from agentops_core.models.rca_finding import RCAFindingRead
from agentops_core.schemas import FailureCase
from agentops_core.services.langfuse_client import LangfuseTraceClient
from agentops_core.services.trace_analyzer.service import analyze_anomaly_signal

router = APIRouter(prefix="/trace-analyses", tags=["trace_analysis"])


class TraceAnalysisRequest(BaseModel):
    anomaly_signal_id: UUID


class TraceAnalysisResponse(BaseModel):
    rca_finding: RCAFindingRead
    failure_cases: list[FailureCase]


@router.post(
    "", response_model=TraceAnalysisResponse, status_code=status.HTTP_201_CREATED
)
def create_trace_analysis(
    payload: TraceAnalysisRequest,
    session: Session = Depends(get_session),
    langfuse_client: LangfuseTraceClient = Depends(get_langfuse_client),
    settings: Settings = Depends(get_settings),
) -> TraceAnalysisResponse:
    try:
        finding, failure_cases = analyze_anomaly_signal(
            anomaly_signal_id=payload.anomaly_signal_id,
            session=session,
            langfuse_client=langfuse_client,
            settings=settings,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg and "signal" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        if "current_skill_id" in msg or "no current_skill_id" in msg:
            raise HTTPException(status_code=400, detail=msg) from exc
        # Other ValueErrors (orphan agent etc.) → 404 by default
        raise HTTPException(status_code=404, detail=msg) from exc

    return TraceAnalysisResponse(
        rca_finding=RCAFindingRead.model_validate(finding.model_dump()),
        failure_cases=failure_cases,
    )
