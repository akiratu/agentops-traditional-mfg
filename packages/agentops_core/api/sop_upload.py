"""POST /factories/{factory_id}/sop-uploads — multipart upload that creates SOPSource."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from agentops_core.database import get_session, get_storage
from agentops_core.models.factory import Factory
from agentops_core.models.sop_source import (
    SOPSource,
    SOPSourceRead,
    SOPSourceType,
)
from agentops_core.services.storage import LocalStorage

router = APIRouter(tags=["sop_upload"])


@router.post(
    "/factories/{factory_id}/sop-uploads",
    response_model=SOPSourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_sop(
    factory_id: UUID,
    file: UploadFile = File(...),
    type: SOPSourceType = Form(...),
    session: Session = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
) -> SOPSourceRead:
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise HTTPException(status_code=404, detail="Factory not found")

    data = await file.read()
    safe_name = file.filename or "unnamed"
    relative_path = f"sop/{factory_id}/{uuid4()}-{safe_name}"
    storage.save(relative_path, data)

    sop = SOPSource(
        factory_id=factory_id,
        type=type,
        storage_ref=relative_path,
        metadata_={
            "original_filename": safe_name,
            "content_type": file.content_type,
            "size_bytes": len(data),
        },
    )
    session.add(sop)
    session.commit()
    session.refresh(sop)
    return SOPSourceRead.model_validate_sop(sop)
