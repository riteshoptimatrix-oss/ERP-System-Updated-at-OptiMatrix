import io
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_active_user, require_permission
from app.database.mongodb import mongodb_manager
from app.models.user import ManufacturingUnit
from app.schemas.reports import ReportType, ExportFormat, GenericReportResponse
from app.repositories.reports_repository import ReportsRepository

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


def get_reports_repo() -> ReportsRepository:
    db = mongodb_manager.get_database()
    return ReportsRepository(db)


@router.get(
    "/{report_type}",
    response_model=GenericReportResponse,
    summary="Get Scoped Analytical Report",
)
async def get_report(
    report_type: ReportType,
    unit_id: Optional[str] = Query(None, description="Facility Unit_1, Unit_2, or BOTH"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    search: Optional[str] = Query(None, description="Text filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(require_permission("reports", "read")),
    repo: ReportsRepository = Depends(get_reports_repo),
) -> GenericReportResponse:
    """
    Returns filtered and reconciled report data across orders, inventory, production,
    QC, wastage, downtime, payroll, finance, and attendance.
    """
    return await repo.get_report_data(
        report_type=report_type,
        unit_id=unit_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{report_type}/export",
    summary="Export Analytical Report as CSV or Excel",
)
async def export_report(
    report_type: ReportType,
    export_format: ExportFormat = Query(ExportFormat.CSV, description="csv or xlsx"),
    unit_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(require_permission("reports", "export")),
    repo: ReportsRepository = Depends(get_reports_repo),
):
    """
    Exports full report data in CSV or Excel (.xlsx) format.
    Requires 'reports:export' permission.
    """
    # Fetch all records for export (page_size=10000)
    data = await repo.get_report_data(
        report_type=report_type,
        unit_id=unit_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=1,
        page_size=10000,
    )

    filename_base = f"RG_{report_type.value}_report_{unit_id or 'all'}"

    if export_format == ExportFormat.XLSX:
        file_bytes = repo.export_xlsx(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{filename_base}.xlsx"
    else:
        file_bytes = repo.export_csv(data)
        media_type = "text/csv"
        filename = f"{filename_base}.csv"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
