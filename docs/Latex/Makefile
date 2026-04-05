# Define variables
TEX = pdflatex -interaction=nonstopmode -shell-escape
BIB = bibtex
PANDOC = pandoc

# List of source files
SOURCES := $(wildcard *.tex)
MAIN = main
READOUT = readout
SCHEMATIC = differential_t2_readout

# Recipe targets
.PHONY: all clean readout readout-pdf readout-docx

# Default target to build the PDF
all: $(MAIN).pdf

# Rule to generate the PDF
$(MAIN).pdf: $(SOURCES) $(MAIN).bbl
	$(TEX) $(MAIN).tex

# Rule to handle bibliography
$(MAIN).bbl: $(MAIN).aux
	$(BIB) $(MAIN)

# Rule to generate auxiliary files
$(MAIN).aux: $(MAIN).tex
	$(TEX) $(MAIN).tex

# Build both readout outputs
readout: readout-pdf readout-docx

# Compile schematic standalone tex to PDF, then crop to content and rasterise to PNG (600 dpi)
$(SCHEMATIC).pdf: $(SCHEMATIC).tex
	$(TEX) $(SCHEMATIC).tex

$(SCHEMATIC).png: $(SCHEMATIC).pdf pdf_to_png.py
	python3 pdf_to_png.py $(SCHEMATIC).pdf $(SCHEMATIC).png 600

# Compile readout.tex to PDF (depends on schematic image)
readout-pdf: $(READOUT).pdf

$(READOUT).pdf: $(READOUT).tex $(SCHEMATIC).png
	$(TEX) $(READOUT).tex

# Compile readout.tex to DOCX via pandoc (depends on schematic image)
readout-docx: $(READOUT).docx

$(READOUT).docx: $(READOUT).tex $(SCHEMATIC).png
	$(PANDOC) $(READOUT).tex -o $(READOUT).docx

# Clean up temporary files
clean:
	rm -f *.aux *.log *.bbl *.blg *.out *.toc *.pdf *.docx *.png *.bcf *.run.xml