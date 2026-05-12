"""Build thesis/reference_aastu.docx — pandoc's style template, AASTU-styled.

Applies the AASTU SPGS VPAA-SPGS-GUD-001 specification:
  * A4 paper
  * Left margin 1.5 inch; right, top, bottom 1 inch
  * Times New Roman 12-pt body
  * 1.5 line spacing for body, single for headings/tables/code
  * Bold headings
  * Monospace (Courier New 10-pt) for code blocks and inline code
  * Tables with single thin borders on every cell

The result is consumed by pandoc via `--reference-doc` when building the
DOCX deliverable.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


REFERENCE_DOCX = Path("thesis/reference_aastu.docx")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _set_rfonts(rpr, *, ascii_font, hansi_font=None, cs_font=None,
                east_asia_font=None):
    """Force per-script font names on a `<w:rPr>` element."""
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), ascii_font)
    rfonts.set(qn("w:hAnsi"), hansi_font or ascii_font)
    rfonts.set(qn("w:cs"), cs_font or ascii_font)
    rfonts.set(qn("w:eastAsia"), east_asia_font or ascii_font)


def _apply_paragraph_style(style, *, font_name="Times New Roman", size_pt=12,
                           line_spacing=1.5, bold=False, color=None):
    style.font.name = font_name
    style.font.size = Pt(size_pt)
    style.font.bold = bold
    if color is not None:
        style.font.color.rgb = RGBColor.from_string(color)
    rpr = style.element.get_or_add_rPr()
    _set_rfonts(rpr, ascii_font=font_name)
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    style.paragraph_format.line_spacing = line_spacing
    style.paragraph_format.space_after = Pt(6)


def _ensure_default_reference() -> None:
    """Regenerate pandoc's default reference docx if missing."""
    if REFERENCE_DOCX.exists():
        return
    subprocess.run(
        ["pandoc", "--print-default-data-file=reference.docx"],
        stdout=open(REFERENCE_DOCX, "wb"),
        check=True,
    )


# ---------------------------------------------------------------------------
# Page-level (section properties)
# ---------------------------------------------------------------------------
def apply_section_properties(doc: Document) -> None:
    """A4 paper + AASTU margins on every section."""
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.left_margin = Inches(1.5)
        section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)


# ---------------------------------------------------------------------------
# Body / heading styles
# ---------------------------------------------------------------------------
def apply_body_and_heading_styles(doc: Document) -> None:
    _apply_paragraph_style(doc.styles["Normal"],
                           size_pt=12, line_spacing=1.5, bold=False)

    for name, size in [("Heading 1", 16), ("Heading 2", 14),
                       ("Heading 3", 13), ("Heading 4", 12),
                       ("Heading 5", 12), ("Heading 6", 12)]:
        if name in doc.styles:
            _apply_paragraph_style(doc.styles[name], size_pt=size,
                                   line_spacing=1.15, bold=True)


# ---------------------------------------------------------------------------
# Code: paragraph (Source Code) + inline (Verbatim Char)
# ---------------------------------------------------------------------------
def apply_code_styles(doc: Document) -> None:
    """Force Courier New 10pt single-spacing on code blocks and inline code."""
    target_font = "Courier New"

    # Paragraph style for fenced code blocks.
    if "Source Code" in doc.styles:
        s = doc.styles["Source Code"]
        s.font.name = target_font
        s.font.size = Pt(10)
        s.font.bold = False
        rpr = s.element.get_or_add_rPr()
        _set_rfonts(rpr, ascii_font=target_font)
        s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        s.paragraph_format.line_spacing = 1.0
        s.paragraph_format.space_after = Pt(6)

    # Character style for inline `code`.
    if "Verbatim Char" in doc.styles:
        v = doc.styles["Verbatim Char"]
        v.font.name = target_font
        v.font.size = Pt(11)
        rpr = v.element.get_or_add_rPr()
        _set_rfonts(rpr, ascii_font=target_font)


# ---------------------------------------------------------------------------
# Tables: single thin borders on every cell
# ---------------------------------------------------------------------------
def _make_border_element(border_name: str, size: str = "6",
                         color: str = "404040") -> OxmlElement:
    el = OxmlElement(f"w:{border_name}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), size)        # 1/8 of a point; 6 ≈ 0.75pt
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), color)
    return el


def _full_borders_xml() -> OxmlElement:
    """Build a <w:tblBorders> with single thin borders on all edges + inside."""
    borders = OxmlElement("w:tblBorders")
    for n in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(_make_border_element(n))
    return borders


def apply_table_borders(doc: Document) -> None:
    """Give the default Pandoc table style a full grid of thin borders.

    Pandoc 3.x picks one of: "Table Grid", "Table", "TableNormal", or
    falls back to "Normal Table" depending on the locale of the reference
    docx. We add borders to all candidates we can find.
    """
    candidates = [
        "Table Grid", "Table", "Normal Table", "TableNormal", "Table Normal",
    ]
    applied = []
    for name in candidates:
        if name not in doc.styles:
            continue
        style = doc.styles[name]
        # Get or create <w:tblPr> inside the style XML.
        tbl_pr = style.element.find(qn("w:tblPr"))
        if tbl_pr is None:
            tbl_pr = OxmlElement("w:tblPr")
            style.element.append(tbl_pr)
        # Remove any pre-existing tblBorders and replace.
        existing = tbl_pr.find(qn("w:tblBorders"))
        if existing is not None:
            tbl_pr.remove(existing)
        tbl_pr.append(_full_borders_xml())
        applied.append(name)
    return applied


def patch_default_table_xml(doc: Document) -> None:
    """Patch the document's underlying styles.xml so any table inheriting
    from the default `TableNormal` chain inherits borders too.

    Pandoc-generated tables sometimes pick up `TableNormal` rather than
    `Table` / `Table Grid`. We modify the in-memory `styles.xml` to ensure
    borders end up on the parent of all table styles.
    """
    styles_element = doc.styles.element
    for st in styles_element.findall(qn("w:style")):
        style_id = st.get(qn("w:styleId"))
        style_type = st.get(qn("w:type"))
        if style_type != "table":
            continue
        # Match common Pandoc table style ids:
        if style_id not in ("TableNormal", "Table", "TableGrid",
                            "Table Normal", "Table Grid"):
            continue
        tbl_pr = st.find(qn("w:tblPr"))
        if tbl_pr is None:
            tbl_pr = OxmlElement("w:tblPr")
            st.append(tbl_pr)
        existing = tbl_pr.find(qn("w:tblBorders"))
        if existing is not None:
            tbl_pr.remove(existing)
        tbl_pr.append(_full_borders_xml())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _ensure_default_reference()
    doc = Document(str(REFERENCE_DOCX))
    apply_section_properties(doc)
    apply_body_and_heading_styles(doc)
    apply_code_styles(doc)
    apply_table_borders(doc)
    patch_default_table_xml(doc)
    doc.save(str(REFERENCE_DOCX))
    print(f"AASTU reference DOCX written: {REFERENCE_DOCX}")


if __name__ == "__main__":
    main()
