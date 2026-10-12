import io
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.database.mongodb import mongodb_manager
from app.models.user import ManufacturingUnit
from app.schemas.reports import (
    ImportEntityType,
    ImportDryRunResponse,
    ImportCommitRequest,
    ImportCommitResponse,
    ImportBatchSummary,
)
from app.repositories.import_repository import ExcelImportRepository
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/imports", tags=["Excel Migration & Imports"])


def get_import_repo() -> ExcelImportRepository:
    db = mongodb_manager.get_database()
    return ExcelImportRepository(db)


@router.get(
    "/templates/{entity_type}",
    summary="Download Standard Excel / CSV Import Template",
)
async def download_import_template(
    entity_type: ImportEntityType,
    current_user: Dict[str, Any] = Depends(require_permission("master", "read")),
    repo: ExcelImportRepository = Depends(get_import_repo),
):
    """
    Downloads pre-formatted Excel template with headers, sample row, and cell formatting.
    """
    try:
        content = repo.generate_template_xlsx(entity_type)
        filename = f"RG_template_{entity_type.value}.xlsx"
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/dry-run",
    response_model=ImportDryRunResponse,
    summary="Upload & Dry-Run Validate Import File",
)
async def dry_run_import_file(
    entity_type: ImportEntityType = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("master", "create")),
    repo: ExcelImportRepository = Depends(get_import_repo),
) -> ImportDryRunResponse:
    """
    Parses workbook, detects duplicates, validates mandatory columns and enums,
    and returns a preview with row-level error logs without writing to production.
    """
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".csv")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx or .csv files are supported.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        return await repo.dry_run_import(
            entity_type=entity_type,
            file_content=content,
            filename=file.filename,
            user_email=current_user.get("email", "USER"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dry-run failed: {str(e)}")


@router.post(
    "/commit",
    response_model=ImportCommitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Commit Validated Batch to Production Database",
)
async def commit_import_batch(
    commit_req: ImportCommitRequest,
    _: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_permission("master", "create")),
    repo: ExcelImportRepository = Depends(get_import_repo),
) -> ImportCommitResponse:
    """
    Commits previously validated rows into live collections.
    Enforces idempotency and logs an immutable audit batch record.
    """
    try:
        return await repo.commit_batch(
            batch_token=commit_req.batch_token,
            unit_id=commit_req.unit_id,
            user_email=current_user.get("email", "USER"),
            notes=commit_req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Commit failed: {str(e)}")


@router.get(
    "/batches",
    response_model=PaginatedResponse[ImportBatchSummary],
    summary="List Past Import Batches & Audit Logs",
)
async def list_import_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_permission("master", "read")),
    repo: ExcelImportRepository = Depends(get_import_repo),
) -> PaginatedResponse[ImportBatchSummary]:
    """
    Returns history of import batches, validation errors, and committed records.
    """
    items, total = await repo.list_batches(page=page, page_size=page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )
