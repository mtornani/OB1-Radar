"""PDF certificate minting."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from core import config


class CertificateGenerator:
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or (config.OUTPUT_DIR / "certificates")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, player_data: Dict[str, object], buyer_email: Optional[str] = None) -> Dict[str, object]:
        """Generate €49 PDF certificate - zero customization."""
        if not player_data:
            raise ValueError("player data required")

        label = str(player_data.get("label") or player_data.get("name") or "Unknown Player")
        certificate_id = hashlib.sha256(f"{label}{datetime.utcnow().isoformat()}".encode("utf-8")).hexdigest()[:12]
        filename = self.output_dir / f"cert_{certificate_id}.pdf"

        story = []
        styles = getSampleStyleSheet()
        title = styles["Title"]
        body = styles["BodyText"]

        story.append(Paragraph("OB1 TALENT ASSESSMENT", title))
        story.append(Paragraph(f"Certificate ID: {certificate_id}", body))
        story.append(Paragraph(f"Issued: {datetime.utcnow().isoformat(timespec='seconds')}Z", body))
        story.append(Paragraph(f"Valid Until: {(datetime.utcnow() + timedelta(days=30)).isoformat(timespec='seconds')}Z", body))

        table_data = [
            ["Player", label],
            ["OB1 Score", player_data.get("score", "-")],
            ["Signals", ", ".join(player_data.get("why", [])) or "none"],
            ["Verdict", _verdict(float(player_data.get("score", 0)))],
            ["Price Paid", f"€{config.PRICING['certificate']}"],
        ]

        table = Table(table_data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                    ("BOX", (0, 0), (-1, -1), 1, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        story.append(table)

        doc = SimpleDocTemplate(str(filename), pagesize=A4)
        doc.build(story)

        return {
            "certificate_id": certificate_id,
            "pdf": str(filename),
            "price": config.PRICING["certificate"],
            "buyer_email": buyer_email,
        }


def _verdict(score: float) -> str:
    if score >= 70:
        return "HIGH POTENTIAL"
    if score >= 40:
        return "MONITOR"
    return "AVOID"


__all__ = ["CertificateGenerator"]
