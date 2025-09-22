#!/usr/bin/env python3
"""Render ``dist/report.html`` into ``dist/report.pdf`` without external deps.

The previous approach relied on WeasyPrint to obtain a visual-faithful PDF, but the
resulting asset stored binary font streams that broke lightweight PR workflows.
This renderer keeps the pipeline self-contained by parsing the HTML structure and
laying out the content with a minimalist PDF writer that only uses built-in Type1
fonts. The generated PDF keeps all sections (executive brief, key bullets and the
three action cards) and preserves critical glyphs such as accents, typographic
apostrophes and the en dash, while remaining ASCII-friendly so the diff can travel
through text-only tooling.
"""

from __future__ import annotations

import argparse
import io
import re
import textwrap
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional


@dataclass
class Card:
    """Container for a single action card rendered in the executive report."""

    title: str = ""
    paragraphs: List[str] = field(default_factory=list)


@dataclass
class ReportContent:
    """Structured representation of the HTML report."""

    heading: str = ""
    section_title: str = ""
    paragraphs: List[str] = field(default_factory=list)
    bullets: List[str] = field(default_factory=list)
    cards: List[Card] = field(default_factory=list)


class ReportHTMLParser(HTMLParser):
    """Minimal HTML parser that captures the textual structure of the report."""

    def __init__(self) -> None:
        super().__init__()
        self.content = ReportContent()
        self._tag_stack: List[tuple[str, dict[str, str]]] = []
        self._active_buffer: Optional[List[str]] = None
        self._active_target: Optional[tuple[str, Optional[int]]] = None
        self._card_stack: List[int] = []
        self._pending_link: Optional[str] = None

    # -- HTMLParser hooks -------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        self._tag_stack.append((tag, attributes))

        if tag == "div" and "class" in attributes and "card" in attributes["class"].split():
            self.content.cards.append(Card())
            self._card_stack.append(len(self.content.cards) - 1)
        elif tag == "h1":
            self._begin_buffer("heading")
        elif tag == "p":
            css_class = attributes.get("class", "")
            if "section-title" in css_class.split():
                self._begin_buffer("section_title")
            elif self._card_stack:
                self._begin_buffer("card_paragraph", self._card_stack[-1])
            else:
                self._begin_buffer("paragraph")
        elif tag == "ul":
            # nothing to capture directly, list items will be handled separately
            pass
        elif tag == "li":
            self._begin_buffer("bullet")
        elif tag == "h3" and self._card_stack:
            self._begin_buffer("card_title", self._card_stack[-1])
        elif tag == "a":
            self._pending_link = attributes.get("href") or None

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._pending_link and self._active_buffer is not None:
            self._active_buffer.append(f" ({self._pending_link})")
            self._pending_link = None

        if self._active_target is not None and self._matches_active_tag(tag):
            self._commit_buffer()

        popped_tag, popped_attrs = self._tag_stack.pop()
        if popped_tag != tag:
            # HTMLParser already guarantees nesting, but fail loudly if something slips.
            raise RuntimeError(f"Unexpected closing tag order: expected {popped_tag}, got {tag}")

        if popped_tag == "div" and "class" in popped_attrs and "card" in popped_attrs["class"].split():
            self._card_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._active_buffer is not None:
            self._active_buffer.append(data)

    # -- Internal helpers -------------------------------------------------

    def _begin_buffer(self, target: str, index: Optional[int] = None) -> None:
        self._active_buffer = []
        self._active_target = (target, index)

    def _matches_active_tag(self, closing_tag: str) -> bool:
        if self._active_target is None:
            return False
        target, _ = self._active_target
        mapping = {
            "heading": "h1",
            "section_title": "p",
            "paragraph": "p",
            "card_paragraph": "p",
            "bullet": "li",
            "card_title": "h3",
        }
        return mapping.get(target) == closing_tag

    def _commit_buffer(self) -> None:
        if self._active_buffer is None or self._active_target is None:
            return

        text = self._normalise_text("".join(self._active_buffer))
        if not text:
            self._reset_buffer()
            return

        target, index = self._active_target
        if target == "heading":
            self.content.heading = text
        elif target == "section_title":
            self.content.section_title = text
        elif target == "paragraph":
            self.content.paragraphs.append(text)
        elif target == "bullet":
            self.content.bullets.append(text)
        elif target == "card_title" and index is not None:
            self.content.cards[index].title = text
        elif target == "card_paragraph" and index is not None:
            self.content.cards[index].paragraphs.append(text)

        self._reset_buffer()

    def _reset_buffer(self) -> None:
        self._active_buffer = None
        self._active_target = None

    @staticmethod
    def _normalise_text(raw: str) -> str:
        # Collapse whitespace while keeping intentional spacing around punctuation.
        collapsed = re.sub(r"\s+", " ", raw).strip()
        # The HTML occasionally uses arrows; normalise them into ASCII for portability.
        collapsed = collapsed.replace("→", "->")
        return collapsed


class SimplePDF:
    """Ultra-light PDF writer that sticks to ASCII output."""

    PAGE_WIDTH = 595.0
    PAGE_HEIGHT = 842.0
    LEFT_MARGIN = 50.0
    RIGHT_MARGIN = 50.0
    TOP_MARGIN = 60.0
    BOTTOM_MARGIN = 60.0

    def __init__(self) -> None:
        self._pages: List[List[str]] = [[]]
        self._page_index = 0
        self._cursor_y = self.PAGE_HEIGHT - self.TOP_MARGIN

    # -- Public layout helpers ------------------------------------------

    def add_heading(self, text: str) -> None:
        self._add_text_block(text, font_size=18, spacing_before=0, spacing_after=12)

    def add_section_title(self, text: str) -> None:
        uppercase = text.upper()
        self._add_text_block(uppercase, font_size=11, spacing_before=0, spacing_after=10)

    def add_paragraph(self, text: str) -> None:
        self._add_text_block(text, font_size=12, spacing_before=0, spacing_after=10)

    def add_bullet(self, text: str) -> None:
        bullet_lines = self._wrap_text(text, font_size=12, indent_points=20.0)
        if not bullet_lines:
            return
        first, *rest = bullet_lines
        lines = ["• " + first]
        lines.extend(["  " + line for line in rest])
        self._write_lines(lines, font_size=12, indent=0.0, spacing_before=2, spacing_after=8)

    def add_card(self, card: Card) -> None:
        self._add_text_block(card.title, font_size=13, spacing_before=4, spacing_after=6)
        for paragraph in card.paragraphs:
            self._add_text_block(paragraph, font_size=12, indent=16.0, spacing_before=0, spacing_after=6)

    def render(self) -> bytes:
        if not self._pages:
            self._pages.append([])

        page_streams = ["".join(commands).encode("ascii") for commands in self._pages]
        page_count = len(page_streams)
        if page_count == 0:
            page_streams = [b""]
            page_count = 1

        page_object_numbers = [3 + i for i in range(page_count)]
        font_object_number = 3 + page_count
        content_object_numbers = [font_object_number + 1 + i for i in range(page_count)]

        kids_entries = " ".join(f"{num} 0 R" for num in page_object_numbers)

        objects: List[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [{kids}] /Count {count} >>".format(
                kids=kids_entries,
                count=page_count,
            ).encode("ascii"),
        ]

        for page_num, (page_obj_num, content_obj_num) in enumerate(
            zip(page_object_numbers, content_object_numbers),
            start=1,
        ):
            objects.append(
                (
                    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content} 0 R "
                    "/Resources << /Font << /F1 {font} 0 R >> >> >>"
                ).format(content=content_obj_num, font=font_object_number).encode("ascii")
            )

        objects.append(
            b"<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
        )

        for stream in page_streams:
            objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))

        buffer = io.BytesIO()
        buffer.write(b"%PDF-1.4\n%OB1 Radar ASCII PDF\n")

        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{index} 0 obj\n".encode("ascii"))
            buffer.write(obj)
            if not obj.endswith(b"\n"):
                buffer.write(b"\n")
            buffer.write(b"endobj\n")

        xref_start = buffer.tell()
        buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        buffer.write(b"trailer\n")
        buffer.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
        buffer.write(b"startxref\n")
        buffer.write(str(xref_start).encode("ascii"))
        buffer.write(b"\n%%EOF\n")
        return buffer.getvalue()

    # -- Internal layout helpers ----------------------------------------

    def _add_text_block(
        self,
        text: str,
        font_size: float,
        indent: float = 0.0,
        spacing_before: float = 4.0,
        spacing_after: float = 4.0,
    ) -> None:
        lines = self._wrap_text(text, font_size=font_size, indent_points=indent)
        if not lines:
            return
        self._write_lines(
            lines,
            font_size=font_size,
            indent=indent,
            spacing_before=spacing_before,
            spacing_after=spacing_after,
        )

    def _wrap_text(self, text: str, font_size: float, indent_points: float = 0.0) -> List[str]:
        usable_width = self.PAGE_WIDTH - self.LEFT_MARGIN - self.RIGHT_MARGIN - indent_points
        if usable_width <= 0:
            return []
        # Approximate character width for Helvetica.
        chars_per_line = max(10, int(usable_width / (font_size * 0.5)))
        wrapped = textwrap.wrap(text, width=chars_per_line)
        return wrapped

    def _write_lines(
        self,
        lines: List[str],
        font_size: float,
        indent: float,
        spacing_before: float,
        spacing_after: float,
    ) -> None:
        leading = font_size * 1.3
        y = self._cursor_y - spacing_before
        for line in lines:
            if y < self.BOTTOM_MARGIN:
                self._new_page()
                y = self._cursor_y - spacing_before
            self._current_page_commands().append(
                "BT /F1 {size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({text}) Tj ET\n".format(
                    size=font_size,
                    x=self.LEFT_MARGIN + indent,
                    y=y,
                    text=self._escape_text(line),
                )
            )
            y -= leading
        self._cursor_y = y - spacing_after

    def _current_page_commands(self) -> List[str]:
        return self._pages[self._page_index]

    def _new_page(self) -> None:
        # Finalise the current page and start a new one.
        self._page_index += 1
        if self._page_index >= len(self._pages):
            self._pages.append([])
        self._cursor_y = self.PAGE_HEIGHT - self.TOP_MARGIN

    @staticmethod
    def _escape_text(text: str) -> str:
        encoded = text.encode("cp1252", errors="replace")
        escaped_chars = []
        for byte in encoded:
            if byte in (0x28, 0x29, 0x5C):  # (, ), \
                escaped_chars.append(f"\\{chr(byte)}")
            elif 32 <= byte <= 126:
                escaped_chars.append(chr(byte))
            else:
                escaped_chars.append(f"\\{byte:03o}")
        return "".join(escaped_chars)


def parse_report(html_path: Path) -> ReportContent:
    parser = ReportHTMLParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    return parser.content


def build_pdf(html_path: Path, pdf_path: Path) -> None:
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()

    content = parse_report(html_path)
    pdf = SimplePDF()
    pdf.add_heading(content.heading)
    if content.section_title:
        pdf.add_section_title(content.section_title)
    for paragraph in content.paragraphs:
        pdf.add_paragraph(paragraph)
    for bullet in content.bullets:
        pdf.add_bullet(bullet)
    for card in content.cards:
        pdf.add_card(card)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(pdf.render())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render HTML report to PDF without third-party engines")
    parser.add_argument(
        "html",
        nargs="?",
        default="dist/report.html",
        type=Path,
        help="Path to the HTML report (default: dist/report.html)",
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        default="dist/report.pdf",
        type=Path,
        help="Path where the PDF should be written (default: dist/report.pdf)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_pdf(args.html, args.pdf)


if __name__ == "__main__":
    main()
