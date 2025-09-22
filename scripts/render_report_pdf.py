"""Render the HTML report into PDF using an HTML/CSS engine."""
from __future__ import annotations

from pathlib import Path

try:
    from weasyprint import HTML
except ModuleNotFoundError as exc:  # pragma: no cover - imported dynamically
    raise SystemExit(
        "WeasyPrint is required to build the PDF. Install dependencies with "
        "`pip install -r requirements.txt`."
    ) from exc


def render_pdf() -> Path:
    """Render ``dist/report.html`` into ``dist/report.pdf``.

    Returns the path of the generated PDF.
    """

    repo_root = Path(__file__).resolve().parents[1]
    html_path = repo_root / "dist" / "report.html"
    pdf_path = repo_root / "dist" / "report.pdf"

    if not html_path.exists():
        raise SystemExit(f"Missing HTML source: {html_path}")

    HTML(filename=str(html_path), base_url=str(html_path.parent)).write_pdf(str(pdf_path))
    return pdf_path


def main() -> None:
    pdf_path = render_pdf()
    print(f"PDF generated: {pdf_path}")


if __name__ == "__main__":
    main()
