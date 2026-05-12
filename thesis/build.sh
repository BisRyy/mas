#!/usr/bin/env bash
# Assemble the thesis chapters into PDF / DOCX / HTML deliverables.
#
# The DOCX uses thesis/reference_aastu.docx, which encodes the
# AASTU SPGS formatting requirements (VPAA-SPGS-GUD-001):
#   * A4 paper
#   * Left margin 1.5"; right/top/bottom 1"
#   * Times New Roman 12-pt body
#   * 1.5 line spacing
#
# Requires pandoc. PDF also needs xelatex (LaTeX) — gracefully skipped
# if absent.
#
# Usage:
#   bash thesis/build.sh                  # PDF + DOCX + HTML
#   bash thesis/build.sh pdf              # PDF only (needs LaTeX)
#   bash thesis/build.sh docx             # DOCX only
#   bash thesis/build.sh html             # standalone HTML only

set -euo pipefail
cd "$(dirname "$0")/.."

target="${1:-all}"

# Chapters in AASTU order: front matter (title, approval, declaration,
# abstract, acks, abbreviations, lists), then 5 numbered chapters, then
# references.
CHAPTERS=(
  thesis/00_front_matter.md
  thesis/01_introduction.md
  thesis/02_literature_review.md
  thesis/03_methodology.md
  thesis/04_results.md
  thesis/05_discussion.md
  thesis/06_conclusion.md
  thesis/99_references.md
)

COMMON_FLAGS=(
  --from markdown
  --toc --toc-depth=3
  # NOTE: --number-sections is intentionally OFF. Our heading text
  # already contains the section numbers ("3.2.5 The Mesa Double-Step
  # Bug"); enabling pandoc's auto-numbering would prepend a second
  # set, producing "3.2.5 3.2.5 The Mesa Double-Step Bug" in the
  # rendered output.
  --citeproc
  --bibliography=thesis/references.bib
  --csl=thesis/ieee.csl
  --metadata title="Design, Implementation, and Empirical Evaluation of a Multi-Agent Architecture for E-Commerce Inventory Optimization"
  --metadata author="Bisrat Kebere Derebe"
  --metadata date="May 2026"
  --metadata link-citations=true
)

# Download an IEEE-style citation style language file if missing.
# IEEE is a sensible default for SE/engineering theses; switch to
# apa-7th-edition.csl or chicago-author-date.csl by replacing the URL
# and filename below.
if [ ! -f thesis/ieee.csl ]; then
  echo "Fetching IEEE citation style ..."
  curl -fsSL \
    https://raw.githubusercontent.com/citation-style-language/styles/master/ieee.csl \
    -o thesis/ieee.csl
fi

# Regenerate the AASTU reference docx if missing or stale.
if [ ! -f thesis/reference_aastu.docx ] || \
   [ scripts/build_aastu_reference.py -nt thesis/reference_aastu.docx ]; then
  echo "Building thesis/reference_aastu.docx ..."
  python -m scripts.build_aastu_reference
fi

if [[ "$target" == "pdf" || "$target" == "all" ]]; then
  if command -v xelatex >/dev/null 2>&1 || command -v pdflatex >/dev/null 2>&1; then
    echo "Building thesis/thesis.pdf ..."
    pandoc "${CHAPTERS[@]}" "${COMMON_FLAGS[@]}" \
      --pdf-engine=xelatex \
      -V geometry:a4paper \
      -V geometry:left=1.5in \
      -V geometry:right=1in \
      -V geometry:top=1in \
      -V geometry:bottom=1in \
      -V mainfont="Times New Roman" \
      -V fontsize=12pt \
      -V linestretch=1.5 \
      --to pdf \
      -o thesis/thesis.pdf
    echo "  -> thesis/thesis.pdf"
  else
    echo "Skipping PDF: no LaTeX engine found (install MacTeX or BasicTeX for PDF output)."
    echo "  DOCX and HTML are usable; open thesis.docx in Word -> Save As PDF if needed."
  fi
fi

if [[ "$target" == "docx" || "$target" == "all" ]]; then
  echo "Building thesis/thesis.docx ..."
  pandoc "${CHAPTERS[@]}" "${COMMON_FLAGS[@]}" \
    --reference-doc=thesis/reference_aastu.docx \
    --to docx \
    -o thesis/thesis.docx
  echo "  -> thesis/thesis.docx"
fi

if [[ "$target" == "html" || "$target" == "all" ]]; then
  echo "Building thesis/thesis.html ..."
  pandoc "${CHAPTERS[@]}" "${COMMON_FLAGS[@]}" \
    --to html5 --embed-resources --standalone --mathjax \
    -o thesis/thesis.html
  echo "  -> thesis/thesis.html"
fi

echo "Done."
