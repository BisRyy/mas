# Thesis Manuscript

This directory contains the thesis chapters for *Design, Implementation, and
Empirical Evaluation of a Multi-Agent Architecture for E-Commerce Inventory
Optimization*. Each chapter is a separate Markdown file so it can be
edited, reviewed, and version-controlled independently.

## Chapter order

| File | Section | Status |
|---|---|---|
| `00_front_matter.md` | Title page, approval, abstract, abbreviations | Template |
| `01_introduction.md` | Background, problem, objectives, RQs, hypotheses | Drafted |
| `02_literature_review.md` | Related work, research gap | Drafted |
| `03_system_design.md` | Architecture, agent roles, communication | Drafted |
| `04_implementation.md` | Tech stack, simulation framework, key algorithms | Drafted |
| `05_methodology.md` | Experimental design, datasets, drift scenarios, metrics | Drafted |
| `06_results.md` | H1, H2, H3 results with statistical tests | Drafted (numbers from final sweeps) |
| `07_discussion.md` | Interpretation, threats to validity | Drafted |
| `08_conclusion.md` | Contributions, future work | Drafted |
| `99_references.md` | Bibliography | Drafted |

## Building the manuscript

To assemble into a single PDF with citations and a table of contents:

```bash
pandoc thesis/0*.md thesis/99_references.md \
  --from markdown \
  --to pdf \
  --pdf-engine=xelatex \
  --toc --toc-depth=2 \
  --number-sections \
  --citeproc \
  --metadata title="Design, Implementation, and Empirical Evaluation of a Multi-Agent Architecture for E-Commerce Inventory Optimization" \
  --metadata author="Bisrat Kebere Derebe" \
  --metadata date="2026" \
  -o thesis/thesis.pdf
```

To produce DOCX (for committee circulation):

```bash
pandoc thesis/0*.md thesis/99_references.md \
  --from markdown --to docx \
  --toc --number-sections \
  -o thesis/thesis.docx
```

## Conventions

- Figures live in `../figures/` and are referenced relative to the repo root
- Tables are inline Markdown
- Citations use Pandoc citation syntax (`[@author2024title]`) — see `references.bib`
- TBD markers (`<!-- TBD: ... -->`) flag content awaiting final data
