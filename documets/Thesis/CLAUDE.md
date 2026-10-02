# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## Directory Layout

- `thesis.tex` — main document entry point; inputs all chapter files and the preamble
- `acronyms.tex` — `\newacronym` definitions; loaded in the preamble of `thesis.tex`
- `references.bib` — BibTeX database for `biblatex`/`biber`
- `figures/` — standalone TikZ/CircuiTikZ source files (e.g. `differential_t2_readout.tex`)
- `build/` — all build artifacts (PDF, DOCX, PNG, aux, log, …); gitignored
- `pdf_to_png.py` — converts a figure PDF to a tight-cropped PNG via Ghostscript; no extra pip deps

## Build Commands

Run from the project root with `-C`, or `cd` into this directory first.

```bash
# From project root
make -C docs/Thesis

# Targets
make                # Build build/thesis.pdf + build/thesis.docx (full thesis)
make thesis-pdf     # Build build/thesis.pdf only
make thesis-docx    # Build build/thesis.docx only (via pandoc)
make readout        # Build build/readout.pdf + build/readout.docx
make readout-pdf    # Build build/readout.pdf only
make readout-docx   # Build build/readout.docx only (via pandoc)
make clean          # Remove build/ entirely
```

## How the Build Works

The thesis build sequence is:
1. `pdflatex thesis.tex` — first pass, generates `build/thesis.bcf` (for biber) and `build/thesis.acn` (for glossaries)
2. `biber build/thesis` — resolves bibliography, writes `build/thesis.bbl`
3. `makeglossaries -d build thesis` — processes acronyms, writes `build/thesis.acr`
4. `pdflatex thesis.tex` × 2 — final passes to resolve all cross-references

## Acronyms

Defined in `acronyms.tex` using `\newacronym{key}{SHORT}{Long form}`. Loaded via `\input{acronyms.tex}` in the preamble of `thesis.tex`. In text, use `\gls{key}` — first use expands to "Long form (SHORT)", subsequent uses print "SHORT". All defined acronyms are forced into the printed list via `\glsaddall` regardless of whether they appear in the text.

## Formatting Preferences (user-confirmed)

- **Page geometry**: `left=2.5cm, right=2.5cm, top=2.5cm, bottom=3cm` (A4) — set globally in `thesis.tex` via `geometry` package.
- **Section numbering**: OFF — `\setcounter{secnumdepth}{0}` in `thesis.tex`. Sections appear in TOC but without numbers.
- **Figure numbering**: Simple integers (1, 2, 3) — `\renewcommand{\thefigure}{\arabic{figure}}` in `thesis.tex`; NOT the chapter-prefixed `0.1` form from report class.
- **List of Figures format**: `Figure N: Title ... page` — via `tocloft` package in `thesis.tex` using `\cftfigpresnum{Figure~}` and `\cftfigaftersnum{: }`. Always provide a short LoF title with `\caption[Short title]{Long caption}`.
- **Wide figures**: Use `\begin{sidewaysfigure}[p]` (from `rotating` package) with `\includegraphics[width=\textheight]{...}` so the figure fills the landscape page. This is the correct approach for the LIA schematic and any other figure wider than ~15 cm.
- **Acronym table**: Each entry on a single line — `\newgeometry{left=1.5cm, right=1.5cm}` + `\setlength{\glsdescwidth}{\dimexpr\textwidth-3.5cm\relax}` wraps the `\printglossary` call; `\restoregeometry` follows immediately after.
- **TikZ figure font**: Standalone documents use `\documentclass[tikz, border=24pt, 12pt]{standalone}` (12 pt base). Block nodes use `font=\large`; wire equation labels use `font=\normalsize`.
- **Academic writing style**: All user-added prose must be revised to conform to academic English conventions: passive voice where appropriate, no first-person pronouns, formal vocabulary (e.g., "suppresses" not "supresses", "is assumed" not "should be"), and correct grammar throughout. Apply this check whenever editing or adding text to any `.tex` file.
- **Chemical formulas**: Use `\mathrm{}` for element symbols inside math mode (e.g., `$\mathrm{CO}$`, `$\mathrm{NO}_2$`). Do NOT write `$CO$` (gives italic, wrong for chemistry).
- **Multi-character subscripts**: Always wrap in `\mathrm{}` (e.g., `$f_{\mathrm{ref}}$`, `$V_{\mathrm{sig}}$`, `$V_{\mathrm{th}}$`).
- **Units / abbreviations in math**: Use `\text{ppm}`, `\text{ppb}` etc., not italic math mode.

## Adding a New TikZ Figure

1. Create a `\documentclass[tikz, border=24pt, 12pt]{standalone}` file in `figures/`
2. Add two rules to the Makefile:
   ```makefile
   $(BUILD)/<name>.pdf: $(FIGURES)/<name>.tex | $(BUILD)
       $(TEX) $<
   $(BUILD)/<name>.png: $(BUILD)/<name>.pdf pdf_to_png.py
       python3 pdf_to_png.py $< $@ 600
   ```
3. Reference it in your `.tex` file as `\includegraphics{build/<name>.png}`
