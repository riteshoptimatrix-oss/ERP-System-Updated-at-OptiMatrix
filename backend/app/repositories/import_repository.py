import csv
import io
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.models.user import ManufacturingUnit
from app.schemas.reports import (
    ImportEntityType,
    ImportBatchStatus,
    ImportDryRunResponse,
    ImportCommitResponse,
    RowErrorDetail,
    ImportBatchSummary,
)

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    openpyxl = None


# Canonical entity templates with column requirements and sample data
ENTITY_TEMPLATES = {
    ImportEntityType.CUSTOMERS: {
        "headers": ["Code", "Name", "GSTIN", "PAN", "Contact Person", "Phone", "Email", "Billing Address", "Shipping Address", "Credit Limit", "Payment Terms Days", "Facility"],
        "sample": ["CUST-001", "Acme Precision Tools", "24ABCDE1234F1Z5", "ABCDE1234F", "Rajesh Patel", "+919876543210", "sales@acmeprecision.com", "Plot 12, GIDC Vatva, Ahmedabad", "Plot 12, GIDC Vatva, Ahmedabad", 500000.0, 30, "BOTH"],
        "required": ["Code", "Name", "Facility"],
        "collection": "customers",
        "unique_key": "code",
    },
    ImportEntityType.VENDORS: {
        "headers": ["Code", "Name", "GSTIN", "PAN", "Contact Person", "Phone", "Email", "Address", "Payment Terms Days", "Facility"],
        "sample": ["VEND-001", "Gujarat Steel Suppliers", "24GSTEEL1234F1Z9", "GSTEEL1234F", "Kishore Shah", "+919825012345", "kishore@gujaratsteel.com", "Phase 2, Naroda GIDC, Ahmedabad", 45, "BOTH"],
        "required": ["Code", "Name", "Facility"],
        "collection": "vendors",
        "unique_key": "code",
    },
    ImportEntityType.RAW_MATERIALS: {
        "headers": ["Code", "Name", "UoM", "Category Code", "Reorder Level", "Unit Cost", "Facility"],
        "sample": ["RM-STEEL-001", "CRCA Sheet 1.2mm", "KG", "SHEET_METAL", 250.0, 85.5, "Unit_1"],
        "required": ["Code", "Name", "UoM", "Facility"],
        "collection": "raw_materials",
        "unique_key": "code",
    },
    ImportEntityType.FINISHED_PRODUCTS: {
        "headers": ["Code", "Name", "UoM", "Category Code", "Standard Selling Price", "Facility"],
        "sample": ["FP-ENFLOW-500", "Enflow 500 Machine Tool", "NOS", "MACHINERY", 125000.0, "Unit_1"],
        "required": ["Code", "Name", "UoM", "Facility"],
        "collection": "finished_products",
        "unique_key": "code",
    },
    ImportEntityType.EMPLOYEES: {
        "headers": ["Employee Code", "First Name", "Last Name", "Email", "Department", "Designation", "Employment Type", "Basic Salary", "Facility"],
        "sample": ["EMP-001", "Amit", "Sharma", "amit.sharma@RG.com", "PRODUCTION", "CNC Operator", "FULL_TIME", 28000.0, "Unit_1"],
        "required": ["Employee Code", "First Name", "Last Name", "Department", "Facility"],
        "collection": "employees",
        "unique_key": "employee_code",
    },
    ImportEntityType.WAREHOUSES: {
        "headers": ["Code", "Name", "Location Description", "Facility"],
        "sample": ["WH-RM-01", "Raw Material Warehouse Unit 1", "Shed 1, Ground Floor", "Unit_1"],
        "required": ["Code", "Name", "Facility"],
        "collection": "warehouses",
        "unique_key": "code",
    },
    ImportEntityType.CATEGORIES: {
        "headers": ["Code", "Name", "Description", "Facility"],
        "sample": ["SHEET_METAL", "Sheet Metal & Plates", "Raw materials sheet category", "BOTH"],
        "required": ["Code", "Name", "Facility"],
        "collection": "categories",
        "unique_key": "code",
    },
    ImportEntityType.UOMS: {
        "headers": ["Code", "Name", "Description"],
        "sample": ["KG", "Kilogram", "Metric kilogram"],
        "required": ["Code", "Name"],
        "collection": "uoms",
        "unique_key": "code",
    },
    ImportEntityType.OPENING_STOCK: {
        "headers": ["Item Code", "Item Type", "Warehouse Code", "Quantity", "UoM", "Unit Cost", "Facility"],
        "sample": ["RM-STEEL-001", "RAW_MATERIAL", "WH-RM-01", 1500.0, "KG", 85.5, "Unit_1"],
        "required": ["Item Code", "Item Type", "Warehouse Code", "Quantity", "UoM", "Facility"],
        "collection": "stock_balances",
        "unique_key": "item_code",
    },
}


class ExcelImportRepository:
    """
    Enterprise Migration & Upload Repository for Opti Matrix.
    Performs parsing, dry-run validations, duplicate detection, row-level error breakdown,
    and auditable idempotent commits.
    """

    def __init__(self, db):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. Template Generation
    # -------------------------------------------------------------------------
    def generate_template_xlsx(self, entity_type: ImportEntityType) -> bytes:
        cfg = ENTITY_TEMPLATES.get(entity_type)
        if not cfg:
            raise ValueError(f"No template defined for entity: {entity_type}")

        if not openpyxl:
            # Fallback to CSV if openpyxl not installed
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(cfg["headers"])
            writer.writerow(cfg["sample"])
            return output.getvalue().encode("utf-8")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Template_{entity_type.value}"

        # Instruction row
        ws.append([f"Opti Matrix - IMPORT TEMPLATE FOR {entity_type.value.upper()}"])
        ws.append(["Note: Do not rename column headers. Required columns are marked in Blue."])
        ws.append([])

        # Header row
        ws.append(cfg["headers"])
        header_row_idx = ws.max_row

        header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")

        for col_idx in range(1, len(cfg["headers"]) + 1):
            cell = ws.cell(row=header_row_idx, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Sample row
        ws.append(cfg["sample"])
        sample_row_idx = ws.max_row
        sample_font = Font(name="Arial", size=10, italic=True, color="4B5563")
        for col_idx in range(1, len(cfg["sample"]) + 1):
            ws.cell(row=sample_row_idx, column=col_idx).font = sample_font

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream.getvalue()

    # -------------------------------------------------------------------------
    # 2. File Parsing (Supports .xlsx and .csv)
    # -------------------------------------------------------------------------
    def parse_file(self, file_content: bytes, filename: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        if filename.endswith(".xlsx") or filename.endswith(".xlsm"):
            if not openpyxl:
                raise ValueError("Excel parsing (.xlsx) requires openpyxl.")
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
            ws = wb.active

            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return [], []

            # Find header row (first non-empty row or row matching template keywords)
            header_idx = 0
            for idx, r in enumerate(rows):
                if any(r):
                    # Check if this row looks like header
                    non_nulls = [str(c).strip() for c in r if c is not None]
                    if len(non_nulls) >= 2 and not non_nulls[0].startswith("RG"):
                        header_idx = idx
                        break

            headers = [str(c).strip() if c is not None else f"Column_{i}" for i, c in enumerate(rows[header_idx])]
            data_rows = []
            for row in rows[header_idx + 1:]:
                if not any(row):
                    continue
                row_dict = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = val
                data_rows.append(row_dict)
            return headers, data_rows

        else:
            # Assume CSV
            decoded = file_content.decode("utf-8-sig", errors="replace")
            reader = csv.reader(io.StringIO(decoded))
            rows = list(reader)
            if not rows:
                return [], []

            header_idx = 0
            for idx, r in enumerate(rows):
                if any(r):
                    non_nulls = [c.strip() for c in r if c]
                    if len(non_nulls) >= 2 and not non_nulls[0].startswith("RG"):
                        header_idx = idx
                        break

            headers = [c.strip() for c in rows[header_idx]]
            data_rows = []
            for r in rows[header_idx + 1:]:
                if not any(r):
                    continue
                row_dict = {}
                for i, val in enumerate(r):
                    if i < len(headers):
                        row_dict[headers[i]] = val.strip()
                data_rows.append(row_dict)
            return headers, data_rows

    # -------------------------------------------------------------------------
    # 3. Dry-Run Validation Engine
    # -------------------------------------------------------------------------
    async def dry_run_import(
        self,
        entity_type: ImportEntityType,
        file_content: bytes,
        filename: str,
        user_email: str,
    ) -> ImportDryRunResponse:
        cfg = ENTITY_TEMPLATES.get(entity_type)
        if not cfg:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        headers, rows = self.parse_file(file_content, filename)
        if not rows:
            return ImportDryRunResponse(
                batch_token="",
                entity_type=entity_type,
                filename=filename,
                total_rows=0,
                valid_rows_count=0,
                error_rows_count=0,
                duplicate_rows_count=0,
                can_commit=False,
                errors=[RowErrorDetail(row_number=1, error_message="Uploaded file has no data rows.")],
                preview_rows=[],
                validation_summary="File contains no readable rows.",
            )

        errors: List[RowErrorDetail] = []
        valid_rows: List[Dict[str, Any]] = []
        seen_in_batch = set()
        duplicate_count = 0

        # Normalization mapping for headers (case-insensitive & whitespace trimmed)
        normalized_headers = {re.sub(r'[^a-zA-Z0-9]', '', h.lower()): h for h in headers}

        def get_field_val(row_dict, target_header_name):
            target_norm = re.sub(r'[^a-zA-Z0-9]', '', target_header_name.lower())
            actual_header = normalized_headers.get(target_norm)
            if actual_header and actual_header in row_dict:
                return row_dict[actual_header]
            return None

        # Fetch existing keys from MongoDB to detect duplicates
        unique_key = cfg["unique_key"]
        collection_name = cfg["collection"]
        existing_keys = set()
        if unique_key:
            cursor = self.db[collection_name].find({}, {unique_key: 1})
            async for doc in cursor:
                val = doc.get(unique_key)
                if val:
                    existing_keys.add(str(val).strip().upper())

        for idx, row in enumerate(rows, start=1):
            row_has_error = False

            # Check required fields
            for req in cfg["required"]:
                val = get_field_val(row, req)
                if val is None or str(val).strip() == "":
                    errors.append(
                        RowErrorDetail(
                            row_number=idx,
                            column=req,
                            value=val,
                            error_message=f"Missing required field '{req}'",
                            is_duplicate=False,
                        )
                    )
                    row_has_error = True

            # Check unique key duplicates
            key_header = cfg["headers"][0]  # E.g. Code or Employee Code
            key_val = get_field_val(row, key_header)
            if key_val is not None and str(key_val).strip() != "":
                norm_key = str(key_val).strip().upper()
                if norm_key in seen_in_batch:
                    errors.append(
                        RowErrorDetail(
                            row_number=idx,
                            column=key_header,
                            value=key_val,
                            error_message=f"Duplicate value '{norm_key}' within the uploaded file.",
                            is_duplicate=True,
                        )
                    )
                    row_has_error = True
                    duplicate_count += 1
                elif norm_key in existing_keys:
                    errors.append(
                        RowErrorDetail(
                            row_number=idx,
                            column=key_header,
                            value=key_val,
                            error_message=f"Duplicate value '{norm_key}' already exists in production database.",
                            is_duplicate=True,
                        )
                    )
                    row_has_error = True
                    duplicate_count += 1
                else:
                    seen_in_batch.add(norm_key)

            # Check Facility / Unit validation
            facility_val = get_field_val(row, "Facility")
            if facility_val:
                fac_str = str(facility_val).strip().upper()
                if fac_str not in ["UNIT_1", "UNIT_2", "BOTH"]:
                    errors.append(
                        RowErrorDetail(
                            row_number=idx,
                            column="Facility",
                            value=facility_val,
                            error_message="Invalid Facility. Must be Unit_1, Unit_2, or BOTH.",
                            is_duplicate=False,
                        )
                    )
                    row_has_error = True

            if not row_has_error:
                valid_rows.append(row)

        batch_token = str(uuid.uuid4())
        total_rows = len(rows)
        error_rows_count = len({e.row_number for e in errors})
        valid_rows_count = len(valid_rows)
        can_commit = (error_rows_count == 0) and (valid_rows_count > 0)

        # Cache the dry-run state in MongoDB `import_batches`
        now = datetime.now(timezone.utc)
        batch_doc = {
            "batch_token": batch_token,
            "entity_type": entity_type.value,
            "filename": filename,
            "total_rows": total_rows,
            "valid_rows_count": valid_rows_count,
            "error_rows_count": error_rows_count,
            "duplicate_rows_count": duplicate_count,
            "status": ImportBatchStatus.DRY_RUN_PASSED.value if can_commit else ImportBatchStatus.DRY_RUN_FAILED.value,
            "errors": [e.model_dump() for e in errors[:50]],  # store up to 50 errors in log
            "valid_rows_data": valid_rows if can_commit else [],
            "created_by": user_email,
            "created_at": now,
        }
        await self.db["import_batches"].insert_one(batch_doc)

        summary_msg = (
            f"Validation passed: {valid_rows_count}/{total_rows} rows are valid and ready to commit."
            if can_commit
            else f"Validation failed: {error_rows_count} row errors found ({duplicate_count} duplicates). Please fix errors before committing."
        )

        return ImportDryRunResponse(
            batch_token=batch_token,
            entity_type=entity_type,
            filename=filename,
            total_rows=total_rows,
            valid_rows_count=valid_rows_count,
            error_rows_count=error_rows_count,
            duplicate_rows_count=duplicate_count,
            can_commit=can_commit,
            errors=errors[:100],  # Return first 100 errors for UI
            preview_rows=rows[:10],  # Return first 10 rows for preview table
            validation_summary=summary_msg,
        )

    # -------------------------------------------------------------------------
    # 4. Authorized Batch Commit
    # -------------------------------------------------------------------------
    async def commit_batch(
        self,
        batch_token: str,
        unit_id: ManufacturingUnit,
        user_email: str,
        notes: Optional[str] = None,
    ) -> ImportCommitResponse:
        batch_doc = await self.db["import_batches"].find_one({"batch_token": batch_token})
        if not batch_doc:
            raise ValueError("Invalid or expired batch token.")

        if batch_doc.get("status") == ImportBatchStatus.COMMITTED.value:
            # Idempotent response
            return ImportCommitResponse(
                batch_id=str(batch_doc["_id"]),
                entity_type=batch_doc["entity_type"],
                status=ImportBatchStatus.COMMITTED.value,
                inserted_count=batch_doc.get("inserted_count", 0),
                skipped_count=0,
                committed_by=batch_doc.get("committed_by", user_email),
                committed_at=batch_doc.get("committed_at", datetime.now(timezone.utc)),
                message="Batch was already committed (idempotent response).",
            )

        if batch_doc.get("status") != ImportBatchStatus.DRY_RUN_PASSED.value:
            raise ValueError("Only batches that passed dry-run validation can be committed.")

        valid_rows = batch_doc.get("valid_rows_data", [])
        if not valid_rows:
            raise ValueError("No valid rows available to commit in this batch.")

        entity_type_str = batch_doc["entity_type"]
        entity_type = ImportEntityType(entity_type_str)
        cfg = ENTITY_TEMPLATES[entity_type]
        collection_name = cfg["collection"]

        now = datetime.now(timezone.utc)
        docs_to_insert = []

        for row in valid_rows:
            # Convert row into proper schema document
            doc = self._format_doc_for_entity(entity_type, row, unit_id.value, user_email, now)
            docs_to_insert.append(doc)

        inserted_count = 0
        if docs_to_insert:
            res = await self.db[collection_name].insert_many(docs_to_insert)
            inserted_count = len(res.inserted_ids)

        # Update batch record to COMMITTED
        await self.db["import_batches"].update_one(
            {"_id": batch_doc["_id"]},
            {
                "$set": {
                    "status": ImportBatchStatus.COMMITTED.value,
                    "inserted_count": inserted_count,
                    "committed_by": user_email,
                    "committed_at": now,
                    "unit_id": unit_id.value,
                    "notes": notes,
                    "valid_rows_data": [],  # Clear cached data to save storage
                }
            },
        )

        return ImportCommitResponse(
            batch_id=str(batch_doc["_id"]),
            entity_type=entity_type_str,
            status=ImportBatchStatus.COMMITTED.value,
            inserted_count=inserted_count,
            skipped_count=0,
            committed_by=user_email,
            committed_at=now,
            message=f"Successfully imported {inserted_count} {entity_type_str} records into production database.",
        )

    # -------------------------------------------------------------------------
    # 5. List Import Batch History
    # -------------------------------------------------------------------------
    async def list_batches(self, page: int = 1, page_size: int = 20) -> Tuple[List[ImportBatchSummary], int]:
        total = await self.db["import_batches"].count_documents({})
        cursor = self.db["import_batches"].find({}).sort("created_at", -1)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        items = [
            ImportBatchSummary(
                id=str(d["_id"]),
                batch_id=str(d["_id"]),
                batch_token=d.get("batch_token", ""),
                entity_type=d.get("entity_type", ""),
                filename=d.get("filename", ""),
                unit_id=d.get("unit_id", "BOTH"),
                total_rows=d.get("total_rows", 0),
                valid_rows_count=d.get("valid_rows_count", 0),
                error_rows_count=d.get("error_rows_count", 0),
                status=d.get("status", ""),
                committed_by=d.get("committed_by"),
                committed_at=d.get("committed_at"),
                created_at=d.get("created_at", datetime.now(timezone.utc)),
                created_by=d.get("created_by", ""),
                errors_sample=[RowErrorDetail(**err) for err in d.get("errors", [])[:5]],
            )
            for d in docs
        ]
        return items, total

    # -------------------------------------------------------------------------
    # Helper to map imported row keys into DB collections
    # -------------------------------------------------------------------------
    def _format_doc_for_entity(
        self,
        entity_type: ImportEntityType,
        row: Dict[str, Any],
        unit_id: str,
        user_email: str,
        now: datetime,
    ) -> Dict[str, Any]:
        # Case insensitive finder
        normalized_row = {re.sub(r'[^a-zA-Z0-9]', '', k.lower()): v for k, v in row.items()}

        def val_of(name, default=None):
            norm = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
            res = normalized_row.get(norm, default)
            return res if res is not None else default

        doc = {
            "created_at": now,
            "created_by": user_email,
            "updated_at": now,
            "updated_by": user_email,
            "is_active": True,
        }

        if entity_type == ImportEntityType.CUSTOMERS:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "gstin": str(val_of("GSTIN", "")).strip() or None,
                "pan": str(val_of("PAN", "")).strip() or None,
                "contact_person": str(val_of("Contact Person", "")).strip() or None,
                "phone": str(val_of("Phone", "")).strip() or None,
                "email": str(val_of("Email", "")).strip() or None,
                "billing_address": str(val_of("Billing Address", "")).strip() or None,
                "shipping_address": str(val_of("Shipping Address", "")).strip() or None,
                "credit_limit": float(val_of("Credit Limit", 0.0) or 0.0),
                "payment_terms_days": int(val_of("Payment Terms Days", 30) or 30),
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.VENDORS:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "gstin": str(val_of("GSTIN", "")).strip() or None,
                "pan": str(val_of("PAN", "")).strip() or None,
                "contact_person": str(val_of("Contact Person", "")).strip() or None,
                "phone": str(val_of("Phone", "")).strip() or None,
                "email": str(val_of("Email", "")).strip() or None,
                "address": str(val_of("Address", "")).strip() or None,
                "payment_terms_days": int(val_of("Payment Terms Days", 45) or 45),
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.RAW_MATERIALS:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "uom": str(val_of("UoM", "KG")).strip().upper(),
                "category_code": str(val_of("Category Code", "")).strip().upper() or None,
                "reorder_level": float(val_of("Reorder Level", 0.0) or 0.0),
                "unit_cost": float(val_of("Unit Cost", 0.0) or 0.0),
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.FINISHED_PRODUCTS:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "uom": str(val_of("UoM", "NOS")).strip().upper(),
                "category_code": str(val_of("Category Code", "")).strip().upper() or None,
                "standard_selling_price": float(val_of("Standard Selling Price", 0.0) or 0.0),
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.EMPLOYEES:
            doc.update({
                "employee_code": str(val_of("Employee Code", "")).strip().upper(),
                "first_name": str(val_of("First Name", "")).strip(),
                "last_name": str(val_of("Last Name", "")).strip(),
                "email": str(val_of("Email", "")).strip() or None,
                "department": str(val_of("Department", "PRODUCTION")).strip().upper(),
                "designation": str(val_of("Designation", "")).strip() or None,
                "employment_type": str(val_of("Employment Type", "FULL_TIME")).strip().upper(),
                "basic_salary": float(val_of("Basic Salary", 0.0) or 0.0),
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.WAREHOUSES:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "location_description": str(val_of("Location Description", "")).strip() or None,
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.CATEGORIES:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "description": str(val_of("Description", "")).strip() or None,
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })
        elif entity_type == ImportEntityType.UOMS:
            doc.update({
                "code": str(val_of("Code", "")).strip().upper(),
                "name": str(val_of("Name", "")).strip(),
                "description": str(val_of("Description", "")).strip() or None,
            })
        elif entity_type == ImportEntityType.OPENING_STOCK:
            doc.update({
                "item_code": str(val_of("Item Code", "")).strip().upper(),
                "item_type": str(val_of("Item Type", "RAW_MATERIAL")).strip().upper(),
                "warehouse_id": str(val_of("Warehouse Code", "")).strip().upper(),
                "quantity": float(val_of("Quantity", 0.0) or 0.0),
                "uom": str(val_of("UoM", "NOS")).strip().upper(),
                "unit_cost": float(val_of("Unit Cost", 0.0) or 0.0),
                "reorder_level": 0.0,
                "unit_id": str(val_of("Facility", unit_id)).strip().upper(),
            })

        return doc
