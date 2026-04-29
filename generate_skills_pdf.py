#!/usr/bin/env python3
"""
generate_skills_pdf.py
Convert skills.md (or any skills markdown file) to a formatted PDF.
The PDF embeds the ##/### heading markers and ``` code fences verbatim
so that skill_task_runner.py can load it directly via --file skills.pdf.

Usage:
  python generate_skills_pdf.py                     # skills.md -> skills.pdf
  python generate_skills_pdf.py my_skills.md        # custom input
  python generate_skills_pdf.py input.md out.pdf    # custom input + output
"""

import os
import re
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Preformatted,
        Spacer, HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
except ImportError:
    print("Error: reportlab is required.")
    print("  Install: pip install reportlab")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "cover_title": s(
            "CoverTitle",
            fontSize=26, leading=32, spaceAfter=10,
            textColor=colors.HexColor("#1a365d"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "cover_sub": s(
            "CoverSub",
            fontSize=12, spaceAfter=6,
            textColor=colors.HexColor("#4a5568"),
            alignment=TA_CENTER,
        ),
        "skill": s(
            "Skill",
            fontSize=14, leading=18,
            spaceBefore=18, spaceAfter=4,
            textColor=colors.HexColor("#1e3a8a"),
            fontName="Helvetica-Bold",
        ),
        "task": s(
            "Task",
            fontSize=11, leading=15,
            spaceBefore=10, spaceAfter=3,
            textColor=colors.HexColor("#1d4ed8"),
            fontName="Helvetica-Bold",
            leftIndent=10,
        ),
        "body": s(
            "Body",
            fontSize=9.5, leading=14,
            spaceAfter=4,
            textColor=colors.HexColor("#374151"),
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontSize=8, leading=11,
            fontName="Courier",
            backColor=colors.HexColor("#f3f4f6"),
            borderColor=colors.HexColor("#d1d5db"),
            borderWidth=0.5,
            borderPadding=(5, 6, 5, 6),
            leftIndent=14,
            rightIndent=6,
            spaceBefore=4,
            spaceAfter=8,
        ),
    }


# ---------------------------------------------------------------------------
# XML/text helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Escape XML entities for use inside a Paragraph."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

def md_to_pdf(md_path: str, pdf_path: str) -> None:
    with open(md_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    styles = _build_styles()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title="Skill Task Runner — Skills",
        author="skill_task_runner",
        subject=md_path,
    )

    story = _build_story(content, styles, md_path)
    doc.build(story)
    size_kb = os.path.getsize(pdf_path) // 1024
    print(f"PDF created : {pdf_path}  ({size_kb} KB)")


def _build_story(content: str, styles: dict, source_name: str) -> list:
    story = []

    # Cover block
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("Skill Task Runner", styles["cover_title"]))
    story.append(Paragraph(f"Source: {os.path.basename(source_name)}", styles["cover_sub"]))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor("#1e3a8a"), spaceAfter=12))
    story.append(Spacer(1, 0.5 * cm))

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # ── Fenced code block ────────────────────────────────────────────
        if re.match(r"^\s*```", line):
            fence_marker = line.rstrip()           # e.g. ```python
            code_lines = [fence_marker]
            i += 1
            while i < len(lines):
                code_lines.append(lines[i])
                if re.match(r"^\s*```\s*$", lines[i]):
                    i += 1
                    break
                i += 1
            # Preformatted does not process markup — safe for raw code
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            continue

        # ── Horizontal rule ───────────────────────────────────────────────
        if re.match(r"^-{3,}\s*$", line):
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#9ca3af"), spaceAfter=4))
            i += 1
            continue

        # ── ## Skill heading ──────────────────────────────────────────────
        if re.match(r"^## ", line) and not line.startswith("### "):
            story.append(Paragraph(_esc(line), styles["skill"]))
            i += 1
            continue

        # ── ### Task heading ──────────────────────────────────────────────
        if line.startswith("### "):
            story.append(Paragraph(_esc(line), styles["task"]))
            i += 1
            continue

        # ── # Top-level heading ───────────────────────────────────────────
        if re.match(r"^# [^#]", line):
            # already shown in the cover; skip to avoid duplication
            i += 1
            continue

        # ── Empty line ────────────────────────────────────────────────────
        if not line.strip():
            story.append(Spacer(1, 0.15 * cm))
            i += 1
            continue

        # ── Body text ─────────────────────────────────────────────────────
        story.append(Paragraph(_esc(line), styles["body"]))
        i += 1

    return story


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    md_path  = args[0] if len(args) >= 1 else "skills.md"
    pdf_path = args[1] if len(args) >= 2 else os.path.splitext(md_path)[0] + ".pdf"

    if not os.path.exists(md_path):
        print(f"Error: '{md_path}' not found.")
        sys.exit(1)

    md_to_pdf(md_path, pdf_path)
    print(f"Run tasks : python skill_task_runner.py --file {pdf_path} --list")


if __name__ == "__main__":
    main()
