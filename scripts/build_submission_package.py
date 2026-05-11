#!/usr/bin/env python3
"""Build an EMNLP/ARR-style anonymous submission package.

The package mirrors the internal Paper5 submission-bundle layout:

submission zip
├── emnlp_submission/        # submit this folder
│   ├── 01_main_paper_8p.pdf
│   ├── 02_supplement.pdf
│   └── source/
└── extras/                  # do not submit; preprint/repro only

PDFs are generated directly from the anonymous Markdown with ReportLab so the
package is usable even on systems without TeX. The Markdown and LaTeX source in
`source/` remain the authoritative camera-ready inputs.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import textwrap
import zipfile
from pathlib import Path

import pypandoc
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJ = Path("/scratch/hpc198a01/젬마4해커톤")
OUT_ROOT = PROJ / "submissions"
PKG = OUT_ROOT / "EMNLP2026_StateGated_LoRA_submission"
ZIP_PATH = OUT_ROOT / "EMNLP2026_StateGated_LoRA_submission.zip"

ANON = PROJ / "paper_anon"
PAPER = PROJ / "paper"

IDENT_PATTERNS = [
    "Byoungsang",
    "Yunchul",
    "Youmin",
    "Chaewon",
    "Jung Heon",
    "Sungkyunkwan",
    "SKKU",
    "MoonTechnology",
    "jhlee",
    "carryer",
    "0000-000",
    "/scratch/hpc198a01",
    "These authors contributed equally",
    "^#^",
]


def run(cmd: list[str]) -> None:
    import subprocess

    subprocess.run(cmd, cwd=PROJ, check=True)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst)


def copy_sections_without_local_notes(src: Path, dst: Path) -> None:
    """Copy paper sections, excluding local analogy/story notes."""
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    excluded = {"appendix_C_cross_domain.md"}
    for p in sorted(src.glob("*.md")):
        if p.name in excluded:
            continue
        shutil.copy2(p, dst / p.name)


def copy_curated_figures(src: Path, dst: Path) -> None:
    """Copy only figures/data used by the current audit framing."""
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    excluded_prefixes = (
        "fig_step_cliff",
        "fig_pf",
        "fig_forgetting_law",
        "section_5_3_5_4_fill",
    )
    for p in sorted(src.iterdir()) if src.exists() else []:
        if not p.is_file():
            continue
        if p.name.startswith(excluded_prefixes):
            continue
        shutil.copy2(p, dst / p.name)


def strip_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def md_to_plain_blocks(md: str) -> list[tuple[str, str]]:
    """Return `(kind, text)` blocks for simple PDF rendering."""
    md = strip_links(md)
    blocks: list[tuple[str, str]] = []
    table_lines: list[str] = []
    para: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            blocks.append(("para", " ".join(x.strip() for x in para).strip()))
            para = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            blocks.append(("table", "\n".join(table_lines)))
            table_lines = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("|") and line.endswith("|"):
            flush_para()
            table_lines.append(line)
            continue
        flush_table()
        if not line.strip():
            flush_para()
            continue
        if line.startswith("```"):
            flush_para()
            blocks.append(("code", line))
            continue
        if line.startswith("#"):
            flush_para()
            level = len(line) - len(line.lstrip("#"))
            blocks.append((f"h{min(level, 3)}", line.lstrip("#").strip()))
        elif line.startswith(("- ", "* ")):
            flush_para()
            blocks.append(("bullet", line[2:].strip()))
        else:
            para.append(line)
    flush_para()
    flush_table()
    return blocks


def clean_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<font name='DejaVuSansMono'>\1</font>", text)
    text = text.replace("**", "")
    text = text.replace("__", "")
    return text


def register_fonts() -> tuple[str, str]:
    candidates = [
        Path("/scratch/hpc198a01/.myksc/codeserver/.local/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"),
        Path("/scratch/hpc198a01/.conda/envs/py310/fonts/DejaVuSans.ttf"),
    ]
    mono_candidates = [
        Path("/scratch/hpc198a01/.myksc/codeserver/.local/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSansMono.ttf"),
        Path("/scratch/hpc198a01/.conda/envs/py310/fonts/DejaVuSansMono.ttf"),
    ]
    font = "Helvetica"
    mono = "Courier"
    for p in candidates:
        if p.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(p)))
            font = "DejaVuSans"
            break
    for p in mono_candidates:
        if p.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSansMono", str(p)))
            mono = "DejaVuSansMono"
            break
    return font, mono


def split_markdown_title(md: str) -> tuple[str, str]:
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), "\n".join(lines[:i] + lines[i + 1:])
    return "Anonymous Paper", md


def render_pdf(md: str, out: Path, title: str, *, two_column: bool = True) -> None:
    """Render a conference-style PDF without system TeX dependencies."""
    out.parent.mkdir(parents=True, exist_ok=True)
    doc_title, body_md = split_markdown_title(md)
    font, mono = register_fonts()
    width, height = letter
    left = 0.58 * inch
    right = 0.58 * inch
    top = 0.55 * inch
    bottom = 0.58 * inch
    gap = 0.22 * inch
    frame_width = (width - left - right - gap) / 2
    full_width = width - left - right

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TitleX", fontName=font, fontSize=17.2, leading=19.0, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle("H1X", fontName=font, fontSize=11.2, leading=12.2, spaceBefore=7, spaceAfter=3))
    styles.add(ParagraphStyle("H2X", fontName=font, fontSize=10.0, leading=11.0, spaceBefore=5.5, spaceAfter=2.5))
    styles.add(ParagraphStyle("H3X", fontName=font, fontSize=9.1, leading=10.0, spaceBefore=4.5, spaceAfter=2, italic=True))
    styles.add(ParagraphStyle("BodyX", fontName=font, fontSize=8.15 if two_column else 9.0, leading=9.35 if two_column else 10.8, alignment=TA_LEFT, spaceAfter=2.4))
    styles.add(ParagraphStyle("BulletX", fontName=font, fontSize=7.95 if two_column else 8.8, leading=9.0 if two_column else 10.4, leftIndent=10, firstLineIndent=-6, spaceAfter=1.5))
    styles.add(ParagraphStyle("CodeX", fontName=mono, fontSize=5.8 if two_column else 7.0, leading=6.7 if two_column else 8.4, leftIndent=5, rightIndent=2, spaceAfter=2.5))
    styles.add(ParagraphStyle("SmallX", fontName=font, fontSize=4.7 if two_column else 6.6, leading=5.45 if two_column else 7.6))

    story = []
    usable_width = frame_width if two_column else full_width
    for kind, text in md_to_plain_blocks(body_md):
        if not text:
            continue
        if kind == "h1":
            story.append(Paragraph(clean_inline(text), styles["H1X"]))
        elif kind == "h2":
            story.append(Paragraph(clean_inline(text), styles["H2X"]))
        elif kind == "h3":
            story.append(Paragraph(clean_inline(text), styles["H3X"]))
        elif kind == "bullet":
            story.append(Paragraph("• " + clean_inline(text), styles["BulletX"]))
        elif kind == "code":
            story.append(Paragraph(clean_inline(text), styles["CodeX"]))
        elif kind == "table":
            rows = []
            for line in text.splitlines():
                if re.match(r"^\|\s*:?-{2,}", line):
                    continue
                cells = [clean_inline(c.strip()) for c in line.strip("|").split("|")]
                if cells:
                    rows.append([Paragraph(c, styles["SmallX"]) for c in cells])
            if rows:
                col_count = max(len(r) for r in rows)
                for r in rows:
                    while len(r) < col_count:
                        r.append(Paragraph("", styles["SmallX"]))
                col_widths = [usable_width / col_count] * col_count
                table = Table(rows, repeatRows=1, colWidths=col_widths, splitByRow=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.black),
                            ("LINEBELOW", (0, 0), (-1, 0), 0.35, colors.black),
                            ("LINEBELOW", (0, -1), (-1, -1), 0.45, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 1.4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 1.4),
                            ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 2.8))
        else:
            for chunk in textwrap.wrap(text, width=780 if two_column else 1100, break_long_words=False, replace_whitespace=False) or [text]:
                story.append(Paragraph(clean_inline(chunk), styles["BodyX"]))

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(width / 2, 0.34 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    def draw_first(canvas, doc):
        draw_page(canvas, doc)
        canvas.saveState()
        title_style = styles["TitleX"]
        title_para = Paragraph(clean_inline(doc_title), title_style)
        tw, th = title_para.wrap(full_width, 0.95 * inch)
        title_para.drawOn(canvas, left, height - top - th + 4)
        canvas.setFont(font, 8.0)
        canvas.setFillColor(colors.HexColor("#333333"))
        canvas.drawCentredString(width / 2, height - top - th - 8, "Anonymous submission")
        canvas.restoreState()

    if two_column:
        first_top_reserved = 1.05 * inch
        first_height = height - top - bottom - first_top_reserved
        frames_first = [
            Frame(left, bottom, frame_width, first_height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            Frame(left + frame_width + gap, bottom, frame_width, first_height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        ]
        later_height = height - top - bottom
        frames_later = [
            Frame(left, bottom, frame_width, later_height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            Frame(left + frame_width + gap, bottom, frame_width, later_height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        ]
        doc = BaseDocTemplate(str(out), pagesize=letter, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom, title=title)
        doc.addPageTemplates([
            PageTemplate(id="First", frames=frames_first, onPage=draw_first, autoNextPageTemplate="Later"),
            PageTemplate(id="Later", frames=frames_later, onPage=draw_page),
        ])
    else:
        frame = Frame(left, bottom, full_width, height - top - bottom - 0.75 * inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        doc = BaseDocTemplate(str(out), pagesize=letter, title=title)
        doc.addPageTemplates([PageTemplate(id="One", frames=[frame], onPage=draw_first)])
    doc.build(story)


def md_to_tex(md: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tex = pypandoc.convert_text(md, "latex", format="md")
    write(out, tex)


def make_supplement() -> str:
    section_names = [
        "appendix_A_dataset.md",
        "appendix_B_hparams.md",
        "appendix_D_failure_gallery.md",
        "appendix_E_repro.md",
        "appendix_F_protocol.md",
        "appendix_G_failure_atlas.md",
    ]
    parts = ["# Supplementary Material\n"]
    for name in section_names:
        p = ANON / "sections" / name
        if p.exists():
            parts.append(read(p))
            parts.append("\n")
    return "\n".join(parts)


def make_full_report() -> str:
    section_names = [
        "01_introduction.md",
        "02_related_work.md",
        "03_method.md",
        "04_family_as_evaluator.md",
        "05_experiments.md",
        "06_discussion.md",
        "07_future_work.md",
        "08_conclusion.md",
        "appendix_A_dataset.md",
        "appendix_B_hparams.md",
        "appendix_D_failure_gallery.md",
        "appendix_E_repro.md",
        "appendix_F_protocol.md",
        "appendix_G_failure_atlas.md",
    ]
    parts = [read(ANON / "main.md"), "\n# Full Technical Report Body\n"]
    for name in section_names:
        p = ANON / "sections" / name
        if p.exists():
            parts.append(read(p))
            parts.append("\n")
    return "\n".join(parts)


def write_manifest(root: Path) -> None:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "manifest_sha256.txt":
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            rows.append(f"{h}  {p.relative_to(root).as_posix()}")
    write(root / "manifest_sha256.txt", "\n".join(rows) + "\n")


def scan_identifiers(root: Path) -> list[str]:
    hits: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in IDENT_PATTERNS:
            if pat in text:
                hits.append(f"{p.relative_to(root)}: {pat}")
    return hits


def main() -> None:
    # Refresh anonymized source first.
    run(["bash", "scripts/build_anon_paper.sh"])

    if PKG.exists():
        shutil.rmtree(PKG)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (PKG / "emnlp_submission/source").mkdir(parents=True)
    (PKG / "extras/04_reproducibility").mkdir(parents=True)

    main_md = read(PAPER / "main_emnlp8.md")
    # main_emnlp8 has no author block and is already written as double-blind;
    # still remove local identifiers defensively.
    main_md = main_md.replace("/scratch/hpc198a01/젬마4해커톤", "[local path]")
    supp_md = make_supplement()
    full_md = make_full_report()

    submit = PKG / "emnlp_submission"
    source = submit / "source"
    extras = PKG / "extras"

    write(submit / "01_main_paper_8p.md", main_md)
    write(submit / "02_supplement.md", supp_md)
    write(source / "main_emnlp8_anonymous.md", main_md)
    write(source / "supplement_anonymous.md", supp_md)
    md_to_tex(main_md, source / "main_emnlp8_anonymous.tex")
    md_to_tex(supp_md, source / "supplement_anonymous.tex")
    write(
        source / "references.bib",
        "% Anonymous minimal bibliography for submission source.\n"
        "% The current Markdown/LaTeX source contains no active citation commands.\n",
    )

    copy_curated_figures(ANON / "figures", source / "figures")
    copy_sections_without_local_notes(ANON / "sections", source / "sections")
    copy_tree(PAPER / "data_release", source / "data_release")
    fae_release = source / "fae_protocol"
    fae_release.mkdir(parents=True, exist_ok=True)
    for rel in [
        "SPEC.md",
        "probes_v1.jsonl",
        "probes_v1.sha256",
        "probes_v2_translit.jsonl",
        "probes_v3_schema.jsonl",
        "taxonomy_v1.txt",
        "scoring_template.csv",
        "score_translit_auto.py",
        "score_schema_auto.py",
        "generate_g3_schema_probes.py",
        "preregistration_template.yaml",
    ]:
        src = PROJ / "tools/fae_protocol" / rel
        if src.exists():
            text = src.read_text(encoding="utf-8", errors="ignore")
            text = text.replace("Byoungsang Lee", "Anonymous Author")
            text = text.replace("Jung Heon Lee", "Anonymous Author")
            text = text.replace("Lee, Byoungsang", "Anonymous")
            text = text.replace("Lee, Jung Heon", "Anonymous")
            text = text.replace("jhlee7@skku.edu", "anonymous@example.com")
            text = text.replace("Family-as-Evaluator", "Human-Tier Audit")
            text = text.replace("FaE", "human-tier audit")
            text = text.replace("Human-Tier Audit (human-tier audit)", "Human-Tier Audit")
            text = text.replace(
                "Beyond BLEU: Human-Tier Audit for Trilingual L1-Aware Language Tutors",
                "State-Gated Audit for Niche-Population LoRA Fine-Tuning",
            )
            text = text.replace(
                "Beyond BLEU: Family-as-Evaluator for Trilingual L1-Aware Language Tutors",
                "State-Gated Audit for Niche-Population LoRA Fine-Tuning",
            )
            text = re.sub(
                r"\*\*Companion paper\*\*: \*.*?\*\s*\(arXiv preprint\)\.",
                "**Companion paper**: *State-Gated Audit for Niche-Population "
                "LoRA Fine-Tuning*.",
                text,
                flags=re.S,
            )
            text = text.replace("On-Device Tutoring with Gemma 4", "LoRA Fine-Tuning")
            write(fae_release / rel, text)

    repro_scripts = extras / "04_reproducibility" / "repro_scripts"
    repro_scripts.mkdir(parents=True, exist_ok=True)
    for rel in [
        "tools/fae_protocol/score_translit_auto.py",
        "tools/fae_protocol/score_schema_auto.py",
        "tools/fae_protocol/generate_g3_schema_probes.py",
        "prototype/eval/eval_g2_extended.py",
        "prototype/eval/summarize_g2_extended.py",
        "prototype/eval/g2_threshold_sensitivity.py",
        "prototype/eval/eval_g3_extended.py",
        "prototype/eval/summarize_g3_extended.py",
        "prototype/eval/build_selector_audit_trace.py",
        "prototype/eval/export_g2_raw_generations.py",
        "scripts/run_g2_extended_4gpu.sh",
        "scripts/run_g3_extended_4gpu.sh",
        "scripts/build_emnlp8.sh",
    ]:
        src = PROJ / rel
        if src.exists():
            dst = repro_scripts / rel.replace("/", "__")
            txt = src.read_text(encoding="utf-8", errors="ignore")
            txt = txt.replace(str(PROJ), "[PROJECT_ROOT]")
            txt = txt.replace("/scratch/hpc198a01", "[WORKSPACE_ROOT]")
            write(dst, txt)

    render_pdf(main_md, submit / "01_main_paper_8p.pdf", "Anonymous Main Paper")
    render_pdf(supp_md, submit / "02_supplement.pdf", "Anonymous Supplementary Material")

    write(extras / "03_full_technical_report.md", full_md)
    md_to_tex(full_md, extras / "03_full_technical_report.tex")
    render_pdf(full_md, extras / "03_full_technical_report.pdf", "Anonymous Full Technical Report")
    shutil.copy2(PAPER / "REFERENCE_AUDIT.md", extras / "REFERENCE_AUDIT.md")
    shutil.copy2(PROJ / "REPRODUCIBILITY.md", extras / "04_reproducibility" / "REPRODUCIBILITY.md")

    readme = """# State-Gated Audit for Niche-Population LoRA Fine-Tuning

EMNLP/ARR-style anonymous submission package.

## Folder layout

```
emnlp_submission/        <- submit this folder
├── 01_main_paper_8p.pdf
├── 02_supplement.pdf
└── source/              (Markdown/LaTeX source, figures, probe files)

extras/                  <- do NOT submit for double-blind review
├── 03_full_technical_report.pdf
├── 03_full_technical_report.md/.tex
├── REFERENCE_AUDIT.md
└── 04_reproducibility/
```

The submission folder is anonymized for double-blind review. The source
contains the paper Markdown, generated LaTeX, bibliography, figures, and probe
files. Minimal reproduction scripts are in `extras/04_reproducibility/`.
The PDFs are generated from the same
anonymous Markdown on this machine; if the venue requires a specific ACL/ARR
style, rebuild the Markdown/LaTeX source with that style before upload.

## Paper message

This is not a calibrated detector paper. It proposes a conservative
audit-and-promotion protocol: GREEN logs and admits, AMBER triggers
documented repair or scoped waiver plus failed-gate rerun, and RED blocks
promotion unless the deployment specification changes and the full audit is
rerun.

## Hygiene checks

- No author names, affiliations, ORCIDs, e-mails, hostnames, or local paths in
  `emnlp_submission/` text files.
- No co-first/equal-contribution wording.
- `lora_v1` remains RED under all G2 threshold sensitivity rules.
- `lora_v2` is G2-clean but blocked by independent G3 schema debt.
"""
    write(PKG / "README.md", readme)

    write_manifest(PKG)
    hits = scan_identifiers(PKG / "emnlp_submission")
    write(PKG / "anonymity_scan.txt", "\n".join(hits) + ("\n" if hits else "PASS\n"))
    if hits:
        raise SystemExit("Identifier scan failed:\n" + "\n".join(hits))

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PKG.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(PKG.parent))

    print(f"[ok] package: {PKG}")
    print(f"[ok] zip: {ZIP_PATH}")
    print(f"[ok] sha256: {hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
