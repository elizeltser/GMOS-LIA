# ============================================================
# Makefile for GMOS-LIA LaTeX documents
# ============================================================
#
# All build artifacts (PDF, DOCX, aux, log, …) go to build/
#
# Common targets:
#   make                 Build thesis.pdf + thesis.docx (full thesis)
#   make thesis-pdf      Build thesis.pdf only
#   make thesis-docx     Build thesis.docx only (via pandoc)
#   make readout         Build readout.pdf AND readout.docx
#   make readout-pdf     Build readout.pdf only
#   make readout-docx    Build readout.docx only (via pandoc)
#   make clean           Remove build/ entirely
#
# Dependencies:
#   pdflatex             For PDF compilation
#   biber                For bibliography (sudo pacman -S texlive-bibtexextra)
#   makeglossaries       For acronym list  (sudo pacman -S texlive-base)
#   pandoc               For DOCX conversion  (sudo pacman -S pandoc)
#   ghostscript          For PDF->PNG rasterisation (sudo pacman -S ghostscript)
# ============================================================

TEX     = pdflatex -interaction=nonstopmode -shell-escape -output-directory=$(BUILD)
BIB     = biber
PANDOC  = pandoc
BUILD   = build
FIGURES = figures

SOURCES       := $(wildcard *.tex)
THESIS         = thesis
READOUT        = readout
SCHEMATIC      = differential_t2_readout
LIA_SCHEMATIC  = lia_schematic

.PHONY: all clean thesis-pdf thesis-docx readout readout-pdf readout-docx

# Default target — must come before the $(BUILD) directory rule
all: thesis-pdf thesis-docx

# Ensure build directory exists before any recipe that needs it
$(BUILD):
	mkdir -p $(BUILD)

# ---- Figures: standalone TikZ/CircuiTikZ → PDF → PNG ----

$(BUILD)/$(SCHEMATIC).pdf: $(FIGURES)/$(SCHEMATIC).tex | $(BUILD)
	$(TEX) $<

$(BUILD)/$(SCHEMATIC).png: $(BUILD)/$(SCHEMATIC).pdf pdf_to_png.py
	python3 pdf_to_png.py $< $@ 600

$(BUILD)/$(LIA_SCHEMATIC).pdf: $(FIGURES)/$(LIA_SCHEMATIC).tex | $(BUILD)
	$(TEX) $<

$(BUILD)/$(LIA_SCHEMATIC).png: $(BUILD)/$(LIA_SCHEMATIC).pdf pdf_to_png.py
	python3 pdf_to_png.py $< $@ 600

# ---- readout ----

readout: readout-pdf readout-docx

readout-pdf: $(BUILD)/$(READOUT).pdf

$(BUILD)/$(READOUT).pdf: $(READOUT).tex $(BUILD)/$(SCHEMATIC).png | $(BUILD)
	$(TEX) $<

readout-docx: $(BUILD)/$(READOUT).docx

$(BUILD)/$(READOUT).docx: $(READOUT).tex $(BUILD)/$(SCHEMATIC).png | $(BUILD)
	$(PANDOC) $(READOUT).tex -o $@

# ---- thesis ----

thesis-pdf: $(BUILD)/$(THESIS).pdf

thesis-docx: $(BUILD)/$(THESIS).docx

# First pass: depends on ALL sources so any .tex change triggers a full rebuild
$(BUILD)/$(THESIS).bcf: $(SOURCES) | $(BUILD)
	$(TEX) $(THESIS).tex

# Bibliography: biber reads build/thesis.bcf, writes build/thesis.bbl
$(BUILD)/$(THESIS).bbl: $(BUILD)/$(THESIS).bcf
	$(BIB) $(BUILD)/$(THESIS)

# Final passes: bibliography + glossaries + cross-references
$(BUILD)/$(THESIS).pdf: $(SOURCES) $(BUILD)/$(THESIS).bbl $(BUILD)/$(LIA_SCHEMATIC).png $(BUILD)/$(SCHEMATIC).png
	makeglossaries -d $(BUILD) $(THESIS)
	$(TEX) $(THESIS).tex
	$(TEX) $(THESIS).tex

$(BUILD)/$(THESIS).docx: $(THESIS).tex | $(BUILD)
	$(PANDOC) $(THESIS).tex -o $@

# ---- clean ----

clean:
	rm -rf $(BUILD)
