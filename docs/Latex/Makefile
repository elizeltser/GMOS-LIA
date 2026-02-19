# Define variables
TEX = pdflatex -interaction=nonstopmode -shell-escape
BIB = bibtex

# List of source files
SOURCES := $(wildcard *.tex)
MAIN = main

# Recipe targets
PHONY: all clean

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

# Clean up temporary files
clean:
   rm -f *.aux *.log *.bbl *.blg *.out *.toc *.pdf