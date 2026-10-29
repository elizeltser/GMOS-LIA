# Render presentation.md with Marp.
#
# presentation.md has no Marp front matter of its own; frontmatter.md
# (theme, footer, tag/risk classes) is prepended to it at build time.
#
#   make          HTML (default)
#   make pdf      PDF
#   make pptx     PowerPoint
#   make all      HTML + PDF + PPTX
#   make watch    live preview in the browser, rebuilds on save
#   make clean    remove generated files
#
# PDF/PPTX need a browser; Marp uses Chrome/Chromium by default.
# With only Firefox installed:  make pdf BROWSER=firefox

MARP    ?= marp
BROWSER ?=
SRC     := presentation.md
FRONT   := frontmatter.md
OUT     := build
DECK    := .deck.md

MARP_FLAGS := --html --allow-local-files $(if $(BROWSER),--browser $(BROWSER))

.PHONY: html pdf pptx all watch clean

html: $(OUT)/presentation.html
pdf:  $(OUT)/presentation.pdf
pptx: $(OUT)/presentation.pptx
all:  html pdf pptx

# Kept next to presentation.md so relative image paths still resolve.
$(DECK): $(FRONT) $(SRC)
	cat $(FRONT) $(SRC) > $@

$(OUT):
	mkdir -p $@

$(OUT)/presentation.html: $(DECK) | $(OUT)
	$(MARP) $(MARP_FLAGS) $< -o $@

$(OUT)/presentation.pdf: $(DECK) | $(OUT)
	$(MARP) $(MARP_FLAGS) --pdf $< -o $@

$(OUT)/presentation.pptx: $(DECK) | $(OUT)
	$(MARP) $(MARP_FLAGS) --pptx $< -o $@

# Marp watches the generated deck; re-concatenate when the sources change.
watch: $(DECK)
	$(MARP) $(MARP_FLAGS) --server . & \
	trap 'kill $$!' EXIT INT TERM; \
	while inotifywait -qq -e close_write $(FRONT) $(SRC); do \
		cat $(FRONT) $(SRC) > $(DECK); \
	done

clean:
	rm -rf $(OUT) $(DECK)
