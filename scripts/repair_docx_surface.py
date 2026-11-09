import argparse
from pathlib import Path
from typing import Any, cast

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor


def set_font(run, name: str = "宋体", size: int = 10) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)


def repair(source: Path, target: Path) -> None:
    document = Document(str(source))
    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Mm(23)
        section.bottom_margin = Mm(23)
        section.left_margin = Mm(25)
        section.right_margin = Mm(25)
    for style_name in ("Normal", "Body Text", "First Paragraph"):
        style = cast(Any, document.styles[style_name])
        style.font.name = "宋体"
        style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
        style.font.size = Pt(10.5)
        style.font.color.rgb = RGBColor(0, 0, 0)
    for level in range(1, 10):
        style = cast(Any, document.styles[f"Heading {level}"])
        style.font.name = "黑体"
        style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "黑体")
        style.font.color.rgb = RGBColor(0, 0, 0)
    for _index, paragraph in enumerate(document.paragraphs):
        if paragraph.text.strip() == "Abstract":
            paragraph.clear()
            run = paragraph.add_run("摘  要")
            set_font(run, "黑体", 12)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.style = "Heading 1"
            continue
        style_name = paragraph.style.name or "" if paragraph.style is not None else ""
        if style_name == "Abstract" and paragraph._p.pPr is not None:
            numbering = paragraph._p.pPr.find(qn("w:numPr"))
            if numbering is not None:
                paragraph._p.pPr.remove(numbering)
        if style_name == "Title":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                set_font(run, "黑体", 18)
        elif style_name.startswith("Heading"):
            for run in paragraph.runs:
                set_font(run, "黑体", 12)
        else:
            for run in paragraph.runs:
                set_font(run)
        if style_name == "Abstract":
            paragraph.paragraph_format.left_indent = Mm(0)
            paragraph.paragraph_format.first_line_indent = Mm(0)
            paragraph.paragraph_format.space_after = Pt(5)
            paragraph.paragraph_format.line_spacing = 1.15
    target.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(target))


parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("target", type=Path)
args = parser.parse_args()
repair(args.source, args.target)
