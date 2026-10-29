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

# Decided: sensor socket

- Socket `J3`: 40-pin `DIP-40` (dual in-line package).
- Pixels (GMOS devices) 1–3 Active, 4–6 Blind.
- Calibration (`CAL`): dummy heater, not a device.
- Same pins as earlier `J19`. Not in docs: socket or soldered.
- Reason: owner to state (not in docs).

Soldered: rejected; reason not in docs.

Open: FSD (functional spec) says 2 of 6 devices are unused; schematic_overview §1.3 uses all 6.

Source: schematics/LIA-board/docs/schematic_overview.md §1.3; ate_lia/FSD.md "Definitions for the GMOS"; schematics/existing_boards/GMOS_v3-CM.pdf p. 1

<!-- Facts: S06-F01, S06-F02, S06-F10, S06-F11, S06-C01, S06-NF01, S06-NF02, S06-NF03. Say: The sensor sits in a 40-pin socket, J3, with six pixels: three Active, three Blind. Its pin map matches the earlier boards' J19 pin for pin. The docs give no reason for the socket, so the owner will state it. Soldered was rejected; the docs give no reason for that either. Open: the FSD says two of six devices are never used; the schematic uses all six. -->
