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

# Other considerations

- Calibration checks the signal chain against known loads and removes zero offset.
- Test points and a debug connector allow probing during bring-up.
- Excitation, timing and pixel selection all depend on firmware.
- 1000-unit rule vs low-stock and single-source parts: open, owner decides.
- Filter fixes the excitation band; a wider filter is still open.
- Prefer hand-solderable packages, and parts that are common and in stock.

Source: schematics/LIA-board/docs/measurement_principles.md §2.13; schematics/LIA-board/docs/requirements.md DG-5, AN-1, AN-34; schematics/LIA-board/docs/firmware.md F.1, F.9; schematics/LIA-board/docs/schematic_overview.md §3.2, §4.9; schematics/LIA-board/docs/README.md §9.1 D-14, §9.2 items 6, 9, 12; simulations/design-context.md §8

<!-- Facts: S10-F01, S10-F02, S10-F04, S10-F05, S10-F06, S10-F09, S10-F12, S10-F13, S10-F15, S10-F18, S10-F19, S10-C01, S10-C02. Say: Calibration checks the chain against known loads; firmware subtracts zero offset. Debug uses the serial debug header only. Firmware sets excitation, timing and pixel selection. Owner decides: the 1000-unit rule conflicts with low-stock parts and AD630 in the schematic. The filter fixes the excitation band; a wider filter is still open. -->
