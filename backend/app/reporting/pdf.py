from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

from app.db.models import AssessmentModel, ReportRecordModel, RunModel


REPORT_ROOT = Path("data/reports")


def _dt(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return value


def _date_key(record: dict) -> str | None:
    for key in ("compromised_date", "date_detected", "first_seen", "last_seen"):
        value = record.get(key)
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc).date().isoformat()
            except ValueError:
                continue
    return None


def _paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text) if text not in (None, "") else "—"), style)


class _ReportTemplate(BaseDocTemplate):
    def __init__(self, filename: str, title: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.title_text = title
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=self._footer)])

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(self.leftMargin, 10 * mm, f"Page {doc.page}")
        canvas.drawRightString(doc.pagesize[0] - self.rightMargin, 10 * mm, "Prepared by: APM")
        canvas.restoreState()


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
                                leading=24, alignment=TA_CENTER, spaceAfter=8 * mm),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=13,
                             leading=16, spaceBefore=4 * mm, spaceAfter=3 * mm),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=9,
                             leading=11, spaceBefore=2 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5,
                               leading=11, spaceAfter=2.5 * mm),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7,
                                leading=9, spaceAfter=1.5 * mm),
        "tiny": ParagraphStyle("Tiny", parent=base["BodyText"], fontName="Helvetica", fontSize=5.5,
                               leading=7),
        "cell": ParagraphStyle("Cell", parent=base["BodyText"], fontName="Helvetica", fontSize=5.7,
                               leading=7),
        "cell_bold": ParagraphStyle("CellBold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=5.7,
                                    leading=7),
    }


def _kv_table(rows: list[tuple[str, str]], styles) -> Table:
    data = [[_paragraph(k, styles["cell_bold"]), _paragraph(v, styles["cell"])] for k, v in rows]
    table = Table(data, colWidths=[48 * mm, 132 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E9EEF5")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C2CC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _records_table(records: list[tuple[str, dict]], styles) -> Table:
    headers = [
        "Compromised Date", "Date Detected", "First Seen", "Last Seen",
        "Victim's Domain", "Victim's Login", "Password", "Victim IP",
        "Source", "Malware", "Threat Actor", "Source Link",
    ]
    rows = [[_paragraph(h, styles["cell_bold"]) for h in headers]]
    for classification, record in records:
        ips = ", ".join(record.get("victim_ips") or ()) or "—"
        source = ", ".join(record.get("source_names") or record.get("source_types") or ()) or "—"
        malware = ", ".join(record.get("stealer_families") or record.get("malware_ids") or ()) or "—"
        actor = ", ".join(record.get("threat_actors") or ()) or "—"
        links = record.get("source_links") or ()
        link_text = "<br/>".join(escape(str(link)) for link in links) or "—"
        values = [
            _dt(record.get("compromised_date")), _dt(record.get("date_detected")),
            _dt(record.get("first_seen")), _dt(record.get("last_seen")),
            record.get("victim_domain"), record.get("username") or record.get("account"),
            record.get("password"), ips, source, malware, actor, link_text,
        ]
        row = []
        for value in values:
            row.append(_paragraph(value, styles["cell"]))
        rows.append(row)
    widths = [20, 20, 20, 20, 22, 25, 22, 20, 23, 24, 23, 38]
    table = Table(rows, colWidths=[w * 0.96 * mm / 4.0 for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#AAB3BD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def generate_report(db, run: RunModel) -> tuple[str, str]:
    assessment = db.query(AssessmentModel).filter(AssessmentModel.run_id == run.run_id).one_or_none()
    if assessment is None:
        raise ValueError("Assessment is required before PDF generation.")

    report_rows = list(db.query(ReportRecordModel).filter(ReportRecordModel.run_id == run.run_id))
    records = [(row.classification, json.loads(row.canonical_json)) for row in report_rows]
    records.sort(key=lambda item: (
        -(datetime.fromisoformat(item[1]["last_seen"].replace("Z", "+00:00")).timestamp()
          if item[1].get("last_seen") else
          datetime.fromisoformat(item[1]["first_seen"].replace("Z", "+00:00")).timestamp()
          if item[1].get("first_seen") else 0),
        item[1].get("compromise_identity", ""),
    ))

    new_records = [record for classification, record in records if classification == "NEW"]
    old_records = [record for classification, record in records if classification == "OLD_HISTORICAL"]
    trend = { (datetime.now(timezone.utc).date() - timedelta(days=i)).isoformat(): 0 for i in range(6, -1, -1) }
    for record in new_records:
        key = _date_key(record)
        if key in trend:
            trend[key] += 1

    facts = json.loads(assessment.facts_json)
    observations = json.loads(assessment.observations_json)
    attention = json.loads(assessment.recommended_attention_json)
    basis = json.loads(assessment.basis_json)
    domains = sorted({r.get("victim_domain") for r in new_records if r.get("victim_domain")})
    malware = sorted({x for r in new_records for x in (r.get("stealer_families") or ())})
    sources = sorted({x for r in new_records for x in (r.get("source_names") or ())})

    report_id = str(uuid4())
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    final_path = REPORT_ROOT / f"{report_id}.pdf"
    temp_path = REPORT_ROOT / f".{report_id}.tmp"
    styles = _styles()

    doc = _ReportTemplate(
        str(temp_path),
        "Group-IB Threat Intelligence Report",
        pagesize=landscape(A4),
        rightMargin=15 * mm, leftMargin=15 * mm, topMargin=15 * mm, bottomMargin=16 * mm,
        title="Group-IB Threat Intelligence Report",
        author="APM",
    )
    story = [
        Spacer(1, 10 * mm),
        Paragraph("GROUP-IB THREAT INTELLIGENCE REPORT", styles["title"]),
        _paragraph(f"Report Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", styles["body"]),
        Paragraph("Quick View", styles["h1"]),
        _kv_table([
            ("Run ID", run.run_id), ("Activity Level", assessment.activity_level),
            ("Assessment Confidence", assessment.confidence), ("Records Retrieved", str(run.records_retrieved)),
            ("NEW Compromises", str(len(new_records))), ("Affected Domains", str(len(domains))),
            ("Infostealer Families", str(len(malware))), ("Sources in NEW Records", str(len(sources))),
        ], styles),
        Spacer(1, 4 * mm),
        Paragraph("Operational Note", styles["h2"]),
        _paragraph("This report contains Group-IB intelligence observed during the collection run and deterministic assessment output. Absence of NEW records is not evidence that the environment is free of compromise.", styles["body"]),
        Paragraph("Seven-Day NEW Compromise Trend", styles["h1"]),
        Table(
            [[_paragraph("Date", styles["cell_bold"]), _paragraph("NEW", styles["cell_bold"])]]
            + [[_paragraph(day, styles["cell"]), _paragraph(count, styles["cell"])] for day, count in trend.items()],
            colWidths=[60 * mm, 30 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C2CC")),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ]),
        ),
        PageBreak(),
        Paragraph("Executive Summary", styles["h1"]),
        _paragraph(assessment.assessment, styles["body"]),
        Paragraph("Daily Threat Assessment", styles["h1"]),
        _kv_table([("Activity Level", assessment.activity_level), ("Assessment Confidence", assessment.confidence)], styles),
        Paragraph("Facts", styles["h2"]),
        *[_paragraph(item, styles["body"]) for item in facts],
        Paragraph("Key Observations", styles["h2"]),
        *[_paragraph(item, styles["body"]) for item in observations],
        Paragraph("Recommended Analyst Attention", styles["h2"]),
        *[_paragraph(item, styles["body"]) for item in attention],
        Paragraph("Assessment Basis", styles["h2"]),
        *[_paragraph(item, styles["body"]) for item in basis],
        PageBreak(),
        Paragraph("NEW Compromised Accounts", styles["h1"]),
        (_records_table([("NEW", r) for r in new_records], styles)
         if new_records else _paragraph("No NEW compromise records were observed in this run.", styles["body"])),
        PageBreak(),
        Paragraph("OLD / HISTORICAL Records", styles["h1"]),
        (_records_table([("OLD_HISTORICAL", r) for r in old_records], styles)
         if old_records else _paragraph("No OLD / HISTORICAL records were classified in this run.", styles["body"])),
        PageBreak(),
        Paragraph("Collection / Data Quality", styles["h1"]),
        _kv_table([
            ("Collection Status", run.status),
            ("Records Retrieved", str(run.records_retrieved)),
            ("Records Normalized", str(run.records_normalized)),
            ("Records Classified", str(run.records_classified)),
            ("Normalization Warnings", str(run.normalization_errors)),
            ("Previous Baseline Available", str(run.previous_baseline_available)),
        ], styles),
        Paragraph("Run Metadata", styles["h1"]),
        _kv_table([
            ("Created", _dt(run.created_at.isoformat() if run.created_at else None)),
            ("Started", _dt(run.started_at.isoformat() if run.started_at else None)),
            ("Completed", _dt(run.completed_at.isoformat() if run.completed_at else None)),
            ("Assessment ID", assessment.assessment_id),
            ("Report ID", report_id),
        ], styles),
    ]

    try:
        doc.build(story)
        os.replace(temp_path, final_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        if final_path.exists():
            final_path.unlink()
        raise
    return report_id, str(final_path)
