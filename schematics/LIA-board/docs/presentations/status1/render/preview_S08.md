---
marp: true
html: true
theme: default
size: 16:9
paginate: true
footer: 'GMOS LIA Board · Status 1 · Eli Zeltser · 29 Oct 2026'
style: |
  section { font-size: 26px; padding: 40px 56px; }
  section h1 { font-size: 40px; }
  section table { font-size: 20px; }
  .risk-green  { background: #d4edda; font-weight: bold; }
  .risk-orange { background: #ffe0b2; font-weight: bold; }
  .risk-red    { background: #f8d7da; font-weight: bold; }
  .tag { font-size: 16px; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
  .tag-hard { background: #d4edda; }
  .tag-fluid { background: #fff3cd; }
  .tag-proposed { background: #e2e3f5; }
---

# Pick one active and one blind pixel

<span class="tag tag-proposed">PROPOSED: owner may drop</span>

- Six pixels: active 1–3 and blind 4–6.
- Pick one active and one blind pixel, any combination.
- All other pixels are disconnected.
- Two address lines per side, plus a shared enable.
- Address 11 connects a fixed calibration load instead of a pixel.
- Not in docs: how the pair is picked, and any money cost.

Source: schematics/LIA-board/docs/requirements.md §R.2.6 (AN-27, AN-28); schematics/LIA-board/docs/schematic_overview.md §4.7

<!-- Facts: S08-F01, S08-F02, S08-F03, S08-F04, S08-NF01, S08-NF02. Say: Six pixels sit in two groups of three. You choose one active and one blind pixel, in any combination; the rest are disconnected. Each side has its own address lines and switch chip. Address 11 selects the calibration load. The docs do not say how the pair is picked or give a money cost. -->
