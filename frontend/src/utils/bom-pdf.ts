import { BOM, MaterialRequirementCalculation } from '@/types/bom';

/**
 * Generates and triggers browser print-to-PDF dialog for an individual Bill of Materials.
 */
export function printBOMToPdf(bom: BOM) {
  const printWindow = window.open('', '_blank', 'width=950,height=1000');
  if (!printWindow) {
    alert('Please allow popups to download or print the Bill of Materials PDF.');
    return;
  }

  const generatedDate = new Date().toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const facilityName =
    bom.unit_id === 'Unit_1'
      ? 'Unit 1 — Heavy Machining, Boring & Milling'
      : bom.unit_id === 'Unit_2'
      ? 'Unit 2 — Sub-Assembly, QC & Finishing'
      : 'All Manufacturing Facilities';

  const rowsHtml = (bom.components || [])
    .map((c, index) => {
      const lineCost = c.estimated_cost ?? (c.gross_quantity || c.net_quantity || 0) * (c.unit_cost || 0);
      return `
        <tr>
          <td style="text-align: center; color: #64748B;">${index + 1}</td>
          <td style="font-weight: 700; color: #0F172A;">${c.material_code || c.material_id}</td>
          <td>
            <div style="font-weight: 600; color: #1E293B;">${c.material_name || c.material_code || 'Raw Material Component'}</div>
            <div style="font-size: 11px; color: #64748B;">${c.notes || 'Standard manufacturing issue'}</div>
          </td>
          <td style="text-align: center; font-weight: 600;">${c.uom || 'PCS'}</td>
          <td style="text-align: right; font-weight: 600;">${(c.net_quantity || 0).toLocaleString()}</td>
          <td style="text-align: center; color: #D97706; font-weight: 600;">${c.scrap_percentage || 0}%</td>
          <td style="text-align: right; font-weight: 700; color: #0F172A;">${(c.gross_quantity || c.net_quantity || 0).toLocaleString()}</td>
          <td style="text-align: right;">₹${(c.unit_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          <td style="text-align: right; font-weight: 700; color: #0F172A;">₹${lineCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        </tr>
      `;
    })
    .join('');

  const htmlContent = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>BOM_${bom.bom_number}_${bom.revision_no}</title>
      <style>
        @page {
          size: A4 portrait;
          margin: 12mm 15mm;
        }
        * {
          box-sizing: border-box;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          margin: 0;
          padding: 24px;
          color: #0F172A;
          background-color: #FFFFFF;
          font-size: 13px;
          line-height: 1.5;
        }
        .header-bar {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          border-bottom: 3px solid #315C45;
          padding-bottom: 16px;
          margin-bottom: 20px;
        }
        .company-title {
          font-size: 22px;
          font-weight: 800;
          color: #315C45;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .company-sub {
          font-size: 12px;
          color: #64748B;
          margin-top: 2px;
        }
        .doc-badge {
          text-align: right;
        }
        .doc-title {
          font-size: 16px;
          font-weight: 800;
          color: #0F172A;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .doc-number {
          font-size: 14px;
          font-family: monospace;
          font-weight: 700;
          color: #315C45;
          margin-top: 4px;
        }
        .meta-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          background-color: #F8FAFC;
          border: 1px solid #E2E8F0;
          border-radius: 8px;
          padding: 14px;
          margin-bottom: 20px;
        }
        .meta-item {
          display: flex;
          flex-direction: column;
        }
        .meta-label {
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          color: #64748B;
          letter-spacing: 0.5px;
        }
        .meta-value {
          font-size: 13px;
          font-weight: 700;
          color: #0F172A;
          margin-top: 2px;
        }
        .product-card {
          border: 1px solid #E2E8F0;
          border-left: 4px solid #315C45;
          border-radius: 6px;
          padding: 12px 16px;
          margin-bottom: 20px;
          background-color: #FFFFFF;
        }
        .table-container {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 20px;
        }
        .table-container th {
          background-color: #F1F5F9;
          color: #475569;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          padding: 10px 12px;
          border-top: 1px solid #CBD5E1;
          border-bottom: 2px solid #CBD5E1;
          letter-spacing: 0.4px;
        }
        .table-container td {
          padding: 10px 12px;
          border-bottom: 1px solid #E2E8F0;
          font-size: 12px;
        }
        .totals-card {
          display: flex;
          justify-content: flex-end;
          margin-bottom: 30px;
        }
        .totals-table {
          width: 320px;
          border-collapse: collapse;
        }
        .totals-table td {
          padding: 6px 12px;
          font-size: 12px;
        }
        .totals-table tr.grand-total td {
          border-top: 2px solid #0F172A;
          font-size: 15px;
          font-weight: 800;
          color: #315C45;
          padding-top: 10px;
        }
        .signoff-section {
          margin-top: 40px;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
          border-top: 1px dashed #CBD5E1;
          padding-top: 20px;
        }
        .sign-box {
          text-align: center;
        }
        .sign-line {
          border-bottom: 1px solid #94A3B8;
          height: 35px;
          margin-bottom: 6px;
        }
        .sign-label {
          font-size: 11px;
          font-weight: 700;
          color: #64748B;
          text-transform: uppercase;
        }
        .action-bar {
          background: #0F172A;
          color: #FFFFFF;
          padding: 12px 24px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: sticky;
          top: 0;
          margin: -24px -24px 24px -24px;
          z-index: 999;
          box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        @media print {
          .action-bar {
            display: none !important;
          }
          body {
            padding: 0;
          }
        }
        .btn {
          background: #315C45;
          color: white;
          border: none;
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 600;
          border-radius: 6px;
          cursor: pointer;
        }
        .btn-outline {
          background: transparent;
          color: #E2E8F0;
          border: 1px solid #475569;
          margin-left: 8px;
        }
      </style>
    </head>
    <body>
      <div class="action-bar">
        <div><strong>Print Preview:</strong> ${bom.bom_number} (${bom.revision_no})</div>
        <div>
          <button class="btn" onclick="window.print()">Save as PDF / Print</button>
          <button class="btn btn-outline" onclick="window.close()">Close Window</button>
        </div>
      </div>

      <div class="header-bar">
        <div>
          <div class="company-title">Opti Matrix Inc.</div>
          <div class="company-sub">Industrial Machinery & Engineering Operations ERP</div>
          <div style="font-size: 11px; color: #64748B; margin-top: 4px;">${facilityName}</div>
        </div>
        <div class="doc-badge">
          <div class="doc-title">Bill of Materials (BOM)</div>
          <div class="doc-number">${bom.bom_number}</div>
          <div style="font-size: 11px; font-weight: 700; color: #059669; margin-top: 4px;">STATUS: ${bom.status}</div>
        </div>
      </div>

      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Revision No</span>
          <span class="meta-value">${bom.revision_no} ${bom.is_active ? '(Active Line Spec)' : ''}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Facility</span>
          <span class="meta-value">${bom.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : 'Unit 2 (Assembly & QC)'}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Base Output Yield</span>
          <span class="meta-value">${bom.base_quantity} ${bom.product_uom || 'SET'}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Document Date</span>
          <span class="meta-value">${generatedDate}</span>
        </div>
      </div>

      <div class="product-card">
        <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Finished Product Specification</div>
        <div style="font-size: 16px; font-weight: 800; color: #0F172A; margin-top: 2px;">
          ${bom.product_code} — ${bom.product_name}
        </div>
        <div style="font-size: 12px; color: #475569; margin-top: 4px;">
          ${bom.description || 'Standard manufacturing assembly routing and multi-level component formulation.'}
        </div>
      </div>

      <table class="table-container">
        <thead>
          <tr>
            <th style="width: 35px; text-align: center;">#</th>
            <th style="width: 130px;">Item Code</th>
            <th>Component Description & Notes</th>
            <th style="width: 50px; text-align: center;">UoM</th>
            <th style="width: 75px; text-align: right;">Net Qty</th>
            <th style="width: 65px; text-align: center;">Scrap %</th>
            <th style="width: 80px; text-align: right;">Gross Qty</th>
            <th style="width: 90px; text-align: right;">Rate (INR)</th>
            <th style="width: 105px; text-align: right;">Line Total (INR)</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>

      <div class="totals-card">
        <table class="totals-table">
          <tr>
            <td style="color: #64748B;">Total Components:</td>
            <td style="text-align: right; font-weight: 700;">${(bom.components || []).length} Items</td>
          </tr>
          <tr>
            <td style="color: #64748B;">Standard Base Quantity:</td>
            <td style="text-align: right; font-weight: 700;">${bom.base_quantity} ${bom.product_uom || 'SET'}</td>
          </tr>
          <tr class="grand-total">
            <td>Estimated Unit Cost:</td>
            <td style="text-align: right;">₹${(bom.total_estimated_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          </tr>
        </table>
      </div>

      <div class="signoff-section">
        <div class="sign-box">
          <div class="sign-line"></div>
          <div class="sign-label">Prepared By (Design Eng.)</div>
        </div>
        <div class="sign-box">
          <div class="sign-line"></div>
          <div class="sign-label">Quality Assured (QC Head)</div>
        </div>
        <div class="sign-box">
          <div class="sign-line"></div>
          <div class="sign-label">Approved By (Works Manager)</div>
        </div>
      </div>

      <script>
        window.onload = function() {
          setTimeout(function() {
            window.print();
          }, 400);
        };
      </script>
    </body>
    </html>
  `;

  printWindow.document.open();
  printWindow.document.write(htmlContent);
  printWindow.document.close();
}

/**
 * Generates and triggers browser print-to-PDF dialog for batch material explosion calculations.
 */
export function printExplosionToPdf(calc: MaterialRequirementCalculation) {
  const printWindow = window.open('', '_blank', 'width=950,height=1000');
  if (!printWindow) {
    alert('Please allow popups to download or print the Material Explosion PDF.');
    return;
  }

  const generatedDate = new Date().toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const rowsHtml = (calc.requirements || [])
    .map((r, index) => {
      const shortageBadge = r.is_shortage
        ? `<span style="color: #E11D48; font-weight: 700;">-${r.shortage_quantity} ${r.uom}</span>`
        : `<span style="color: #059669; font-weight: 600;">Covered</span>`;

      return `
        <tr>
          <td style="text-align: center; color: #64748B;">${index + 1}</td>
          <td style="font-weight: 700; color: #0F172A;">${r.material_code}</td>
          <td style="font-weight: 600; color: #1E293B;">${r.material_name}</td>
          <td style="text-align: right; font-weight: 600;">${r.net_required_quantity} ${r.uom}</td>
          <td style="text-align: center; color: #D97706;">${r.scrap_percentage}%</td>
          <td style="text-align: right; font-weight: 700; color: #0F172A;">${r.gross_required_quantity} ${r.uom}</td>
          <td style="text-align: right; font-weight: 600; color: #334155;">${r.quantity_available} ${r.uom}</td>
          <td style="text-align: center;">${shortageBadge}</td>
          <td style="text-align: right; font-weight: 700;">₹${(r.total_estimated_cost || 0).toLocaleString()}</td>
        </tr>
      `;
    })
    .join('');

  const htmlContent = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Explosion_${calc.product_code}_${calc.production_quantity}Units</title>
      <style>
        @page {
          size: A4 portrait;
          margin: 12mm 15mm;
        }
        * {
          box-sizing: border-box;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          margin: 0;
          padding: 24px;
          color: #0F172A;
          background-color: #FFFFFF;
          font-size: 13px;
          line-height: 1.5;
        }
        .header-bar {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          border-bottom: 3px solid #315C45;
          padding-bottom: 16px;
          margin-bottom: 20px;
        }
        .company-title {
          font-size: 22px;
          font-weight: 800;
          color: #315C45;
          text-transform: uppercase;
        }
        .company-sub {
          font-size: 12px;
          color: #64748B;
        }
        .meta-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          background-color: #F8FAFC;
          border: 1px solid #E2E8F0;
          border-radius: 8px;
          padding: 14px;
          margin-bottom: 20px;
        }
        .meta-label {
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          color: #64748B;
        }
        .meta-value {
          font-size: 13px;
          font-weight: 700;
          color: #0F172A;
          margin-top: 2px;
        }
        .table-container {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 20px;
        }
        .table-container th {
          background-color: #F1F5F9;
          color: #475569;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          padding: 10px 12px;
          border-top: 1px solid #CBD5E1;
          border-bottom: 2px solid #CBD5E1;
        }
        .table-container td {
          padding: 10px 12px;
          border-bottom: 1px solid #E2E8F0;
          font-size: 12px;
        }
        .action-bar {
          background: #0F172A;
          color: #FFFFFF;
          padding: 12px 24px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: sticky;
          top: 0;
          margin: -24px -24px 24px -24px;
          z-index: 999;
        }
        @media print {
          .action-bar {
            display: none !important;
          }
        }
        .btn {
          background: #315C45;
          color: white;
          border: none;
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 600;
          border-radius: 6px;
          cursor: pointer;
        }
        .btn-outline {
          background: transparent;
          color: #E2E8F0;
          border: 1px solid #475569;
          margin-left: 8px;
        }
      </style>
    </head>
    <body>
      <div class="action-bar">
        <div><strong>Print Preview:</strong> Batch Explosion ${calc.product_code} (${calc.production_quantity} Units)</div>
        <div>
          <button class="btn" onclick="window.print()">Save as PDF / Print</button>
          <button class="btn btn-outline" onclick="window.close()">Close Window</button>
        </div>
      </div>

      <div class="header-bar">
        <div>
          <div class="company-title">Opti Matrix Inc.</div>
          <div class="company-sub">Material Requirement Planning & Stock Shortage Forecast</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 16px; font-weight: 800; color: #0F172A;">MRP EXPLOSION REPORT</div>
          <div style="font-size: 12px; color: #64748B;">Run on: ${generatedDate}</div>
        </div>
      </div>

      <div class="meta-grid">
        <div>
          <div class="meta-label">Target Product SKU</div>
          <div class="meta-value">${calc.product_code}</div>
        </div>
        <div>
          <div class="meta-label">Batch Output Target</div>
          <div class="meta-value">${calc.production_quantity} Unit(s)</div>
        </div>
        <div>
          <div class="meta-label">Inventory Status</div>
          <div class="meta-value" style="color: ${calc.has_sufficient_stock ? '#059669' : '#E11D48'};">
            ${calc.has_sufficient_stock ? '100% Sufficient' : `${calc.total_shortages_count} Shortages Detected`}
          </div>
        </div>
        <div>
          <div class="meta-label">Estimated Batch Material Cost</div>
          <div class="meta-value" style="color: #315C45;">₹${(calc.total_estimated_material_cost || 0).toLocaleString()}</div>
        </div>
      </div>

      <table class="table-container">
        <thead>
          <tr>
            <th style="width: 35px; text-align: center;">#</th>
            <th style="width: 130px;">Item Code</th>
            <th>Material Description</th>
            <th style="text-align: right;">Net Qty</th>
            <th style="text-align: center;">Scrap</th>
            <th style="text-align: right;">Gross Req.</th>
            <th style="text-align: right;">In Stock</th>
            <th style="text-align: center;">Shortage</th>
            <th style="text-align: right;">Line Cost (INR)</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>

      <script>
        window.onload = function() {
          setTimeout(function() {
            window.print();
          }, 400);
        };
      </script>
    </body>
    </html>
  `;

  printWindow.document.open();
  printWindow.document.write(htmlContent);
  printWindow.document.close();
}
