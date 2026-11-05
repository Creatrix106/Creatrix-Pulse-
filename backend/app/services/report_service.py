import io
import csv
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.config import settings
from app.db.database import db
from app.schemas.report import ReportConfig, ReportPreview, ReportRecord, ReportSummaryItem, ReportColumn
from app.schemas.filters import AnalyticsFilters
from app.services.analytics_service import AnalyticsService

METRIC_LABELS = {
    "revenue": ("Revenue", "currency"),
    "orders": ("Orders", "number"),
    "units": ("Units sold", "number"),
    "aov": ("Average order value", "currency"),
    "cost": ("Cost", "currency"),
    "profit": ("Gross profit", "currency"),
}

class ReportService:
    @classmethod
    async def build_preview(cls, dataset_id: str, config: ReportConfig) -> ReportPreview:
        filters = AnalyticsFilters(
            datePreset=config.datePreset,
            comparison="none",
            groupBy="month"
        )
        df, dataset = await AnalyticsService.load_dataframe(dataset_id)
        has_cost = dataset.get("capabilities", {}).get("cost", False)
        cur_df, _, period, _ = AnalyticsService.slice_dataframe(df, filters)
        tot = AnalyticsService.calculate_totals(cur_df, has_cost)
        series = AnalyticsService.build_timeseries(cur_df, "month", has_cost)

        # Filter metrics
        valid_metrics = [
            m for m in config.metrics
            if m in METRIC_LABELS and not (m in ["cost", "profit"] and not has_cost)
        ]

        summary: List[ReportSummaryItem] = []
        for m in valid_metrics:
            lbl, fmt = METRIC_LABELS[m]
            val = tot.get(m) or 0.0
            summary.append(ReportSummaryItem(label=lbl, value=round(val, 2), format=fmt))

        columns = [ReportColumn(key="date", label="Month", format="date")]
        for m in valid_metrics:
            lbl, fmt = METRIC_LABELS[m]
            columns.append(ReportColumn(key=m, label=lbl, format=fmt))

        rows: List[Dict[str, Any]] = []
        for p in series:
            item = {"date": p.date}
            for m in valid_metrics:
                item[m] = getattr(p, m, 0.0) or 0.0
            rows.append(item)

        return ReportPreview(
            title=config.title,
            generatedAt=datetime.datetime.utcnow().isoformat() + "Z",
            period=period,
            summary=summary,
            columns=columns,
            rows=rows
        )

    @classmethod
    async def create_report(cls, dataset_id: str, config: ReportConfig, user_id: Optional[str] = None) -> ReportRecord:
        preview = await cls.build_preview(dataset_id, config)
        report_id = f"rep-{uuid.uuid4().hex[:10]}"
        fmt = config.format.lower()
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        file_path = None
        content = None
        size_bytes = 0

        if fmt == "json":
            content = json.dumps(preview.dict(), indent=2)
            size_bytes = len(content.encode("utf-8"))
            file_path = str(settings.REPORTS_DIR / f"{report_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        elif fmt == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([c.label for c in preview.columns])
            for r in preview.rows:
                writer.writerow([r.get(c.key, "") for c in preview.columns])
            content = buf.getvalue()
            size_bytes = len(content.encode("utf-8"))
            file_path = str(settings.REPORTS_DIR / f"{report_id}.csv")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        elif fmt == "xlsx":
            file_path = str(settings.REPORTS_DIR / f"{report_id}.xlsx")
            rows_data = []
            for r in preview.rows:
                row_dict = {c.label: r.get(c.key, "") for c in preview.columns}
                rows_data.append(row_dict)
            rep_df = pd.DataFrame(rows_data)
            rep_df.to_excel(file_path, index=False, engine="openpyxl")
            size_bytes = Path(file_path).stat().st_size

        elif fmt == "pdf":
            file_path = str(settings.REPORTS_DIR / f"{report_id}.pdf")
            cls._generate_pdf_report(file_path, preview)
            size_bytes = Path(file_path).stat().st_size

        download_url = f"{settings.API_V1_PREFIX}/datasets/{dataset_id}/reports/{report_id}/download"

        report_data = {
            "id": report_id,
            "dataset_id": dataset_id,
            "user_id": user_id,
            "title": f"{config.title} ({config.datePreset})",
            "format": fmt,
            "parameters": config.dict(),
            "row_count": len(preview.rows),
            "file_size_bytes": size_bytes,
            "file_path": file_path,
            "content": content if fmt in ["csv", "json"] else None,
            "download_url": download_url,
            "created_at": now_iso
        }
        await db.create_report(report_data)

        return ReportRecord(
            id=report_id,
            datasetId=dataset_id,
            title=report_data["title"],
            format=fmt,
            createdAt=now_iso,
            rowCount=len(preview.rows),
            sizeBytes=size_bytes,
            content=content,
            downloadUrl=download_url
        )

    @staticmethod
    def _generate_pdf_report(output_path: str, preview: ReportPreview):
        doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a")
        )
        meta_style = ParagraphStyle(
            name="MetaStyle",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b")
        )
        kpi_label_style = ParagraphStyle(
            name="KpiLabel",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        kpi_val_style = ParagraphStyle(
            name="KpiVal",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0284c7")
        )

        elements = []
        # Title & Meta
        elements.append(Paragraph(f"<b>Creatrix Pulse</b> — {preview.title}", title_style))
        elements.append(Spacer(1, 6))
        meta_text = f"Generated at: {preview.generatedAt[:19].replace('T', ' ')} UTC | Period: {preview.period.get('from')} to {preview.period.get('to')}"
        elements.append(Paragraph(meta_text, meta_style))
        elements.append(Spacer(1, 16))

        # KPI Summary Cards in Table
        kpi_cells = []
        for s in preview.summary:
            fmt_val = f"₹{s.value:,.2f}" if s.format == "currency" else f"{s.value:,.0f}"
            cell = [Paragraph(s.label.upper(), kpi_label_style), Paragraph(fmt_val, kpi_val_style)]
            kpi_cells.append(cell)

        if kpi_cells:
            # Arrange in rows of up to 3 cards
            card_rows = []
            curr_row = []
            for c in kpi_cells:
                curr_row.append(c)
                if len(curr_row) == 3:
                    card_rows.append(curr_row)
                    curr_row = []
            if curr_row:
                while len(curr_row) < 3:
                    curr_row.append([Paragraph("", kpi_label_style), Paragraph("", kpi_val_style)])
                card_rows.append(curr_row)

            kpi_table = Table(card_rows, colWidths=[2.3 * inch, 2.3 * inch, 2.3 * inch])
            kpi_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(kpi_table)
            elements.append(Spacer(1, 20))

        # Data Table
        table_data = [[c.label for c in preview.columns]]
        for r in preview.rows:
            row_items = []
            for c in preview.columns:
                v = r.get(c.key, "")
                if c.format == "currency":
                    row_items.append(f"₹{float(v):,.2f}")
                elif c.format == "number":
                    row_items.append(f"{float(v):,.0f}")
                else:
                    row_items.append(str(v))
            table_data.append(row_items)

        col_w = 7.0 * inch / max(1, len(preview.columns))
        data_table = Table(table_data, colWidths=[col_w] * len(preview.columns))
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ]))
        elements.append(data_table)

        doc.build(elements)
