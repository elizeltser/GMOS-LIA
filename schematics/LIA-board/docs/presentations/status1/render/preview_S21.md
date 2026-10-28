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

# Cable 5 V on isolated UART still open

UART: serial link. Isolation: no electrical connection. Risk: GREEN low, ORANGE medium, RED high.

| Option | Not in docs | Risk | Mitigation |
|---|---|---|---|
| Keep TTL-232R-3V3 cable as is | Cable RXD tolerance: Not in docs | <span class="risk-red">RED: high, 5 V on isolator</span> | Confirm cable RXD accepts 5 V logic |
| 3.3 V regulator on isolated side | Ground return, current: Not in docs | <span class="risk-orange">ORANGE: medium, 3.3 V only</span> | Size regulator current; confirm GND return |
| Specify TTL-232R-5V cable | Levels, pin order: Not in docs | <span class="risk-red">RED: high, 5 V on isolator</span> | Confirm levels and pin order first |
| 5 V-tolerant parts, isolated side | Parts, supply range: Not in docs | <span class="risk-red">RED: high, 5 V on isolator</span> | Confirm isolator supply range and parts |

Open question: which option handles the 5 V supply?

Source: schematics/LIA-board/docs/README.md §9.1 D-21; schematics/LIA-board/docs/schematic_review.md §1 D-21; schematics/LIA-board/docs/requirements.md §R.3 DG-4

<!-- Facts: S21-F01, S21-F02, S21-F05, S21-F06, S21-F07, S21-F09, S21-F11, S21-NF01, S21-NF02, S21-NF03, S21-NF04, S21-NF05. Say: The board's UART link crosses an isolator to a 6-pin header, and an external FTDI cable supplies the 5 V. D-21 is open because that 5 V on the isolated side is unresolved. Only the 3.3 V regulator keeps the isolator off 5 V, and its current rating is not in the docs. The sources give no reason for the isolation itself, nor for rejecting CP2102N and ISOUSB211. The owner decides. -->
