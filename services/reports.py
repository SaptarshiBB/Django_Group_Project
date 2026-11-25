"""
PDF Report Generation Service.
Generates an official, printable A4 compliance verification report using ReportLab
under the Legal Metrology (Packaged Commodities) Rules, 2011.
"""
import io
import os
from typing import Optional
from PIL import Image as PILImage
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas:
    """Canvas that performs a two-pass calculation for accurate 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        from reportlab.pdfgen import canvas
        self._canvas_class = canvas.Canvas
        self.pages = []

    def __call__(self, *args, **kwargs):
        canvas_instance = self._canvas_class(*args, **kwargs)
        orig_show_page = canvas_instance.showPage
        orig_save = canvas_instance.save

        def show_page():
            self.pages.append(dict(canvas_instance.__dict__))
            canvas_instance._startPage()

        def save():
            num_pages = len(self.pages)
            for page in self.pages:
                canvas_instance.__dict__.update(page)
                self.draw_page_decorations(canvas_instance, num_pages)
                orig_show_page()
            orig_save()

        canvas_instance.showPage = show_page
        canvas_instance.save = save
        return canvas_instance

    def draw_page_decorations(self, canvas, total_pages):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#475569"))

        # Top running header on later pages
        if canvas._pageNumber > 1:
            canvas.drawString(
                36,
                A4[1] - 25,
                "Legal Metrology (Packaged Commodities) Rules, 2011 — Official Compliance Inspection Report",
            )
            canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
            canvas.setLineWidth(0.5)
            canvas.line(36, A4[1] - 28, A4[0] - 36, A4[1] - 28)

        # Bottom footer
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.setLineWidth(0.5)
        canvas.line(36, 32, A4[0] - 36, 32)

        footer_text = "Government of India | Legal Metrology Division | Department of Consumer Affairs"
        page_str = f"Page {canvas._pageNumber} of {total_pages}"
        canvas.drawString(36, 20, footer_text)
        canvas.drawRightString(A4[0] - 36, 20, page_str)
        canvas.restoreState()


class ComplianceReportGenerator:
    """Builds a formatted A4 PDF compliance report for a Scan instance."""

    def __init__(self, scan):
        self.scan = scan
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Define enterprise-grade typography and color scheme."""
        self.styles.add(
            ParagraphStyle(
                name="DocHeader",
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=18,
                textColor=colors.HexColor("#1b365d"),
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="DocSubHeader",
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#334155"),
                alignment=1,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionTitle",
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                textColor=colors.HexColor("#1b365d"),
                spaceBefore=10,
                spaceAfter=4,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="TableCell",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#1e293b"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="TableCellBold",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#0f172a"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="LegalDisclaimer",
                fontName="Helvetica-Oblique",
                fontSize=7.5,
                leading=10,
                textColor=colors.HexColor("#64748b"),
            )
        )

    def generate(self) -> io.BytesIO:
        """Render the complete PDF into an in-memory byte buffer."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=40,
        )

        story = []

        # 1. Header Banner
        story.append(
            Paragraph(
                "LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011",
                self.styles["DocHeader"],
            )
        )
        story.append(
            Paragraph(
                "OFFICIAL PACKAGING STATUTORY COMPLIANCE AUDIT REPORT",
                self.styles["DocSubHeader"],
            )
        )
        story.append(Spacer(1, 10))
        story.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=colors.HexColor("#1b365d"),
                spaceAfter=10,
            )
        )

        # 2. Executive Metadata & Status Grid
        metadata_table = self._build_metadata_table()
        story.append(metadata_table)
        story.append(Spacer(1, 12))

        # 3. Product Label Thumbnail (if present)
        thumbnail_element = self._build_thumbnail_element()
        if thumbnail_element:
            story.append(thumbnail_element)
            story.append(Spacer(1, 10))

        # 4. Mandatory Extracted Declarations
        story.append(
            Paragraph("1. STATUTORY DECLARATIONS VERIFICATION", self.styles["SectionTitle"])
        )
        declarations_table = self._build_declarations_table()
        story.append(declarations_table)
        story.append(Spacer(1, 12))

        # 5. Rule-by-Rule Compliance Evaluation Matrix
        story.append(
            Paragraph(
                "2. RULE-BY-RULE LEGAL METROLOGY EVALUATION RESULTS",
                self.styles["SectionTitle"],
            )
        )
        rules_table = self._build_rules_table()
        story.append(rules_table)
        story.append(Spacer(1, 14))

        # 6. Statutory Disclaimer & Verification Note
        disclaimer_text = (
            "STATUTORY NOTICE & DISCLAIMER: This report is compiled pursuant to the provisions of the "
            "Legal Metrology (Packaged Commodities) Rules, 2011 (as amended). Automated OCR and rule matching "
            "is provided to support statutory compliance audits. Official enforcement proceedings must confirm "
            "specimen measurements (including physical numeral font height and weight verification) on physical packaging."
        )
        story.append(
            KeepTogether(
                [
                    HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=colors.HexColor("#cbd5e1"),
                        spaceAfter=6,
                    ),
                    Paragraph(disclaimer_text, self.styles["LegalDisclaimer"]),
                    Spacer(1, 14),
                    self._build_signatures_table(),
                ]
            )
        )

        # Build document
        canvas_maker = NumberedCanvas()
        doc.build(story, canvasmaker=canvas_maker)
        buffer.seek(0)
        return buffer

    def _build_metadata_table(self) -> Table:
        status_colors = {
            "COMPLIANT": colors.HexColor("#166534"),
            "NON_COMPLIANT": colors.HexColor("#991b1b"),
            "NEEDS_REVIEW": colors.HexColor("#854d0e"),
            "PENDING": colors.HexColor("#475569"),
        }
        status_bg = {
            "COMPLIANT": colors.HexColor("#dcfce7"),
            "NON_COMPLIANT": colors.HexColor("#fee2e2"),
            "NEEDS_REVIEW": colors.HexColor("#fef9c3"),
            "PENDING": colors.HexColor("#f1f5f9"),
        }

        verdict_color = status_colors.get(self.scan.status, colors.black)
        verdict_bg = status_bg.get(self.scan.status, colors.white)

        verdict_para = Paragraph(
            f"<b>{self.scan.get_status_display().upper()}</b><br/><font size=7>Score: {self.scan.score}%</font>",
            ParagraphStyle(
                name="VerdictCell",
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=12,
                textColor=verdict_color,
                alignment=1,
            ),
        )

        data = [
            [
                Paragraph("<b>Inspection ID:</b>", self.styles["TableCellBold"]),
                Paragraph(f"INSP-{self.scan.id:06d}", self.styles["TableCell"]),
                Paragraph("<b>Date & Time:</b>", self.styles["TableCellBold"]),
                Paragraph(self.scan.created_at.strftime("%d-%b-%Y %H:%M IST"), self.styles["TableCell"]),
                verdict_para,
            ],
            [
                Paragraph("<b>Product / Brand:</b>", self.styles["TableCellBold"]),
                Paragraph(self.scan.product_name or "Not Specified", self.styles["TableCell"]),
                Paragraph("<b>Commodity Category:</b>", self.styles["TableCellBold"]),
                Paragraph(self.scan.get_category_display(), self.styles["TableCell"]),
                "",
            ],
            [
                Paragraph("<b>Inspector / User:</b>", self.styles["TableCellBold"]),
                Paragraph(self.scan.user.username, self.styles["TableCell"]),
                Paragraph("<b>Packaging Type:</b>", self.styles["TableCellBold"]),
                Paragraph(self.scan.pre_packed_type or "Standard Pre-packed", self.styles["TableCell"]),
                "",
            ],
        ]

        col_widths = [90, 140, 100, 120, 72]
        table = Table(data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (3, -1), 0.5, colors.HexColor("#f1f5f9")),
                    ("SPAN", (4, 0), (4, 2)),
                    ("BACKGROUND", (4, 0), (4, 2), verdict_bg),
                    ("BOX", (4, 0), (4, 2), 1.0, verdict_color),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    def _build_thumbnail_element(self) -> Optional[Table]:
        """Optionally embed an uploaded panel image thumbnail if available."""
        first_img = self.scan.images.first()
        if not first_img or not bool(first_img.image):
            return None

        try:
            if not hasattr(first_img.image, "path"):
                return None
            img_path = first_img.image.path
            if not os.path.exists(img_path):
                return None

            # Calculate scaled thumbnail dimensions keeping aspect ratio within 140x90
            with PILImage.open(img_path) as pil_img:
                w, h = pil_img.size
                scale = min(140.0 / w, 90.0 / h)
                thumb_w = w * scale
                thumb_h = h * scale

            report_img = Image(img_path, width=thumb_w, height=thumb_h)
            caption = Paragraph(
                f"<b>Specimen Packaging Image</b><br/>"
                f"<font size=7 color='#64748b'>Panel: {first_img.get_label_type_display()} | OCR Avg Conf: {first_img.avg_confidence}%</font>",
                self.styles["TableCell"],
            )

            thumb_table = Table([[report_img, caption]], colWidths=[150, 372])
            thumb_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            return thumb_table
        except Exception:
            return None

    def _build_declarations_table(self) -> Table:
        headers = [
            Paragraph("<b>Mandatory Declaration Field</b>", self.styles["TableCellBold"]),
            Paragraph("<b>Extracted / Stated Label Text</b>", self.styles["TableCellBold"]),
            Paragraph("<b>Verification</b>", self.styles["TableCellBold"]),
        ]

        rows = [headers]
        for field in self.scan.extracted_fields.all():
            label_text = field.label or field.key.replace("_", " ").title()
            val_text = field.value if field.value else "<font color='#94a3b8'>[Not Detected]</font>"
            status_text = "Inspector Edited" if field.is_user_edited else f"OCR ({field.confidence:.0f}%)"

            rows.append(
                [
                    Paragraph(f"<b>{label_text}</b>", self.styles["TableCell"]),
                    Paragraph(val_text, self.styles["TableCell"]),
                    Paragraph(status_text, self.styles["TableCell"]),
                ]
            )

        table = Table(rows, colWidths=[150, 290, 82])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    def _build_rules_table(self) -> Table:
        headers = [
            Paragraph("<b>Rule Reference</b>", self.styles["TableCellBold"]),
            Paragraph("<b>Statutory Subject</b>", self.styles["TableCellBold"]),
            Paragraph("<b>Status</b>", self.styles["TableCellBold"]),
            Paragraph("<b>Findings & Legal Evaluation</b>", self.styles["TableCellBold"]),
        ]

        status_badge_colors = {
            "PASS": "#166534",
            "FAIL": "#991b1b",
            "WARNING": "#854d0e",
            "NEEDS_REVIEW": "#1e3a8a",
        }

        rows = [headers]
        for res in self.scan.rule_results.select_related("rule").all():
            badge_hex = status_badge_colors.get(res.status, "#334155")
            badge_para = Paragraph(
                f"<b><font color='{badge_hex}'>{res.status}</font></b>",
                self.styles["TableCellBold"],
            )

            rows.append(
                [
                    Paragraph(res.rule.rule_reference, self.styles["TableCellBold"]),
                    Paragraph(res.rule.title, self.styles["TableCell"]),
                    badge_para,
                    Paragraph(res.message, self.styles["TableCell"]),
                ]
            )

        table = Table(rows, colWidths=[110, 120, 62, 230])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    def _build_signatures_table(self) -> Table:
        data = [
            [
                Paragraph("<b>Inspected & Evaluated By:</b>", self.styles["TableCellBold"]),
                Paragraph("<b>Legal Metrology Officer / Controller:</b>", self.styles["TableCellBold"]),
            ],
            [
                Paragraph(f"Signature: _______________________<br/>Officer: {self.scan.user.username}", self.styles["TableCell"]),
                Paragraph("Authorized Stamp: ___________________<br/>Verification Date: _______________", self.styles["TableCell"]),
            ],
        ]
        table = Table(data, colWidths=[260, 262])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table
