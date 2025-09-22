import re
import textwrap
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import List

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 48
TOP_MARGIN = 50
LINE_HEIGHT = 13


def normalize_whitespace(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def replace_unicode(value: str) -> str:
    # Map characters that are outside WinAnsiEncoding to safe fallbacks.
    return value.replace("\u00a0", " ")


@dataclass
class Card:
    title: str = ""
    paragraphs: List[str] = field(default_factory=list)


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str = ""
        self.section_title: str = ""
        self.paragraphs: List[str] = []
        self.bullets: List[str] = []
        self.cards: List[Card] = []
        self._current_text: List[str] | None = None
        self._current_link: str | None = None
        self._in_card: Card | None = None
        self._current_tag: str | None = None
        self._is_section_title = False
        self._in_list = False

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        if tag == "h1":
            self._current_tag = tag
            self._current_text = []
        elif tag == "p":
            self._current_tag = tag
            self._current_text = []
            classes = attrs_dict.get("class", "")
            self._is_section_title = "section-title" in classes.split()
        elif tag == "ul":
            self._in_list = True
        elif tag == "li":
            self._current_tag = tag
            self._current_text = []
        elif tag == "div" and "card" in attrs_dict.get("class", "").split():
            self._in_card = Card()
            self.cards.append(self._in_card)
        elif tag == "h3" and self._in_card is not None:
            self._current_tag = tag
            self._current_text = []
        elif tag == "a":
            self._current_link = attrs_dict.get("href")
        
    def handle_data(self, data: str):
        if self._current_text is None:
            return
        cleaned = data.replace("\n", " ")
        if cleaned:
            self._current_text.append(cleaned)

    def handle_endtag(self, tag: str):
        if tag == "a":
            if self._current_link and self._current_text is not None:
                self._current_text.append(f" ({self._current_link})")
            self._current_link = None
            return
        if tag == "ul":
            self._in_list = False
        if tag == "div" and self._in_card is not None:
            self._in_card = None
            return
        if self._current_tag != tag:
            return
        if self._current_text is None:
            return
        combined = normalize_whitespace("".join(self._current_text))
        if not combined:
            self._current_text = None
            self._current_tag = None
            return
        if tag == "h1":
            self.title = combined
        elif tag == "p":
            if self._in_card is not None:
                self._in_card.paragraphs.append(combined)
            elif self._is_section_title:
                self.section_title = combined
            else:
                self.paragraphs.append(combined)
        elif tag == "li":
            self.bullets.append(combined)
        elif tag == "h3" and self._in_card is not None:
            self._in_card.title = combined
        self._current_text = None
        self._current_tag = None
        self._is_section_title = False


def max_chars(width_points: float, font_size: float) -> int:
    avg_char_width = font_size * 0.55
    return max(12, int(width_points / avg_char_width))


def pdf_escape(text: str) -> str:
    text = replace_unicode(text)
    encoded = text.encode("cp1252", errors="replace")
    result = []
    for byte in encoded:
        char = chr(byte)
        if char in {"(", ")", "\\"}:
            result.append(f"\\{char}")
        elif 32 <= byte <= 126:
            result.append(char)
        else:
            result.append(f"\\{byte:03o}")
    return "".join(result)


class LayoutBuilder:
    def __init__(self) -> None:
        self.margin_x = MARGIN_X
        self.top_y = PAGE_HEIGHT - TOP_MARGIN
        self.current_y = self.top_y
        self.commands: List[str] = []
        self.rectangles: List[tuple[float, float, float, float]] = []

    def _add_text(self, text: str, font: str, size: float, x: float, line_height: float) -> None:
        if "\u2192" in text:
            parts = text.split("\u2192")
            segments = [f"BT\n/{font} {size:.2f} Tf\n{x:.2f} {self.current_y:.2f} Td\n"]
            for index, piece in enumerate(parts):
                if piece:
                    segments.append(f"({pdf_escape(piece)}) Tj\n")
                if index < len(parts) - 1:
                    segments.append(f"/F3 {size:.2f} Tf\n(\\256) Tj\n/{font} {size:.2f} Tf\n")
            segments.append("ET\n")
            self.commands.append("".join(segments))
        else:
            escaped = pdf_escape(text)
            self.commands.append(
                f"BT\n/{font} {size:.2f} Tf\n{x:.2f} {self.current_y:.2f} Td\n({escaped}) Tj\nET\n"
            )
        self.current_y -= line_height

    def _wrap(self, text: str, width_points: float, font_size: float) -> List[str]:
        width_chars = max_chars(width_points, font_size)
        return textwrap.wrap(text, width=width_chars, break_long_words=False, break_on_hyphens=False)

    def add_title(self, text: str) -> None:
        self._add_text(text, "F2", 18, self.margin_x, 22)
        self.current_y -= 6

    def add_section_title(self, text: str) -> None:
        self._add_text(text.upper(), "F2", 11, self.margin_x, 15)

    def add_paragraph(self, text: str) -> None:
        for line in self._wrap(text, PAGE_WIDTH - 2 * self.margin_x, 12):
            self._add_text(line, "F1", 12, self.margin_x, LINE_HEIGHT)
        self.current_y -= 3

    def add_bullet(self, text: str) -> None:
        available = PAGE_WIDTH - 2 * self.margin_x - 18
        lines = self._wrap(text, available, 12)
        for index, line in enumerate(lines):
            x = self.margin_x + (18 if index else 0)
            content = line if index else f"• {line}"
            self._add_text(content, "F1", 12, x, LINE_HEIGHT)
        self.current_y -= 2

    def add_card(self, card: Card) -> None:
        card_padding = 8
        inner_width = PAGE_WIDTH - 2 * self.margin_x - 2 * card_padding
        layout: List[tuple[str, str, float, float]] = []  # (text, font, size, line_height)

        layout.append((card.title, "F2", 13, 14))
        for paragraph in card.paragraphs:
            lines = self._wrap(paragraph, inner_width, 11)
            for line in lines:
                layout.append((line, "F1", 11, 12))
            layout.append(("", "", 0, 4))
        if layout and layout[-1][0] == "":
            layout.pop()

        total_height = sum(item[3] for item in layout if item[3]) + 2 * card_padding
        card_top = self.current_y
        card_bottom = card_top - total_height
        card_width = PAGE_WIDTH - 2 * self.margin_x
        self.rectangles.append((self.margin_x, card_bottom, card_width, total_height))

        self.current_y -= card_padding
        for text, font, size, height in layout:
            if not text:
                self.current_y -= height
                continue
            self._add_text(text, font or "F1", size or 11, self.margin_x + card_padding, height)
        self.current_y -= card_padding + 6

    def build_stream(self) -> bytes:
        parts: List[str] = []
        if self.rectangles:
            parts.append("0.75 G\n")
            for x, y, width, height in self.rectangles:
                parts.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S\n")
            parts.append("0 G\n")
        parts.extend(self.commands)
        return "".join(parts).encode("latin-1")


def build_pdf(data: ReportParser, output_path: Path) -> None:
    layout = LayoutBuilder()
    layout.add_title(data.title)
    if data.section_title:
        layout.add_section_title(data.section_title)
    for paragraph in data.paragraphs:
        layout.add_paragraph(paragraph)
    for bullet in data.bullets:
        layout.add_bullet(bullet)
    for card in data.cards:
        layout.add_card(card)

    content_stream = layout.build_stream()

    objects: List[bytes] = []

    def add_object(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_regular = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\n")
    font_bold = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\n")
    font_symbol = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Symbol >>\n")

    resource_obj = add_object(
        f"<< /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R /F3 {font_symbol} 0 R >> /ProcSet [/PDF /Text] >>\n".encode("ascii")
    )

    contents_obj = add_object(
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("ascii")
        + content_stream
        + b"\nendstream\n"
    )

    page_obj = add_object(
        f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Contents {contents_obj} 0 R /Resources {resource_obj} 0 R >>\n".encode("ascii")
    )

    pages_obj = add_object(
        f"<< /Type /Pages /Kids [{page_obj} 0 R] /Count 1 >>\n".encode("ascii")
    )

    # Update page parent reference now that pages_obj is known
    objects[page_obj - 1] = (
        f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Contents {contents_obj} 0 R /Resources {resource_obj} 0 R >>\n".encode("ascii")
    )

    catalog_obj = add_object(
        f"<< /Type /Catalog /Pages {pages_obj} 0 R >>\n".encode("ascii")
    )

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body_chunks: List[bytes] = []
    offsets: List[int] = []
    position = len(header)

    for index, obj in enumerate(objects, start=1):
        chunk = f"{index} 0 obj\n".encode("ascii") + obj + b"endobj\n"
        body_chunks.append(chunk)
        offsets.append(position)
        position += len(chunk)

    xref_offset = position
    xref_entries = [b"0000000000 65535 f \n"]
    for off in offsets:
        xref_entries.append(f"{off:010d} 00000 n \n".encode("ascii"))

    xref = b"xref\n0 %d\n" % (len(objects) + 1) + b"".join(xref_entries)
    trailer = (
        f"trailer<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )

    with output_path.open("wb") as pdf_file:
        pdf_file.write(header)
        for chunk in body_chunks:
            pdf_file.write(chunk)
        pdf_file.write(xref)
        pdf_file.write(trailer)


def main() -> None:
    html_path = Path("dist/report.html")
    pdf_path = Path("dist/report.pdf")
    parser = ReportParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    build_pdf(parser, pdf_path)


if __name__ == "__main__":
    main()
