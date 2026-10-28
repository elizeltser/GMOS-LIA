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

# Three front-end (FE) options; I recommend FE-B

| | FE-A (D-18 total 47 of 75) | FE-B (D-18 total 51 of 75) | FE-C (D-18 total 50 of 75) |
|---|---|---|---|
| Demodulator (rectifies at excitation phase) | 2× AD630 chips | TMUX6136 switch + OPA2196 | 2× TMUX1219 switch + OPA2365 |
| Rails (supply lines) | ±5 V, plus ±7 V chain | ±5 V or ±7 V: open | +5 V, 2.5 V, −0.23 V |
| First-pass risk (D-18 score) | <span class="risk-green">GREEN: low</span> score 4 of 5 | <span class="risk-orange">ORANGE: medium</span> score 3 of 5 | <span class="risk-red">RED: high</span> score 2 of 5 |
| Main risk | <span class="risk-red">RED: high</span> AD630 not at JLC/LCSC | <span class="risk-orange">ORANGE: medium</span> TMUX6136 supply open | <span class="risk-red">RED: high</span> INA333 ±200 mV: open |

Legend: GREEN = low, ORANGE = medium, RED = high; colour from D-18 §5 scores.

Owner's recommendation: FE-B — provisional; decisive sims not run; §9.1 closure pending.

Source: schematics/LIA-board/docs/schematic_overview.md §4.9; schematics/LIA-board/docs/decisions/D-18_frontend.md §1, §5; simulations/simulation-plan.md §7.4

<!-- Facts: S19-F01, S19-F02, S19-F03, S19-F48, S19-F50, S19-F53, S19-F54, S19-F55, S19-F65. Say: FE is the analog chain from sensor to ADC; the demodulator picks out the signal at excitation phase; a rail is a supply line. Colours are D-18 scores; FE-A main risk is availability (1). Simulations are topology only and confidence is low to medium. Totals are provisional; FE-B and FE-C are within 10 percent. -->

---

# What each option means for parts

| | FE-A | FE-B | FE-C |
|---|---|---|---|
| Parts added / removed | As drawn (reference) | Removes AD630s; adds TMUX6136, OPA2196 | −AD630s, −negative chain; +5 IC types |
| Rails (supply lines) | ±5 V, plus ±7 V chain | No rail change; switch supply open | −7 V/−5VA removed; +V_REF, −0.23 V |
| Availability (all single-maker) | AD630 unstocked (JLC); INA828 LCSC-only | TMUX6136 low at JLC; Mouser stocked | INA333 LCSC-only; LM7705 stock: sources differ |
| Mitigation | Not in docs: no alternative part | SIM-10/11-B, LAB-9 tests; order now | Headroom fix; full-chain sim (SIM-13-C) |

Open: switch ±5 V (overview) or ±7 V (D-18); INA333 ±200 mV OK (principles) or clips (D-18).

Owner's recommendation: FE-B — provisional; decisive sims not run; §9.1 closure pending.

Source: schematics/LIA-board/docs/ — schematic_overview.md §4.9; decisions/D-18_frontend.md §3.2, §6; measurement_principles.md §2.15

<!-- Facts: S19-F07, S19-F09, S19-F10, S19-F20, S19-F21, S19-F25, S19-F26, S19-F29, S19-F30, S19-F31, S19-F62, S19-C01, S19-C03, S19-C07. Say: FE-C adds five IC types in eight packages and replaces INA828 with INA333; OPA2365 is LCSC-only. FE-B adds TMUX6136 and OPA2196. Overview and research disagree on LM7705 stock; no counts shown. LAB-9 is the bench full-chain test. INA828 is also used in FE-A. -->
