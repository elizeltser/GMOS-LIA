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

# Risk map of the open decisions

| Decision | Options | Risk now | After mitigation / owner line |
|---|---|---|---|
| MCU placement | A: on board; B: on EVB | <span class="risk-red">RED: MCU pins not wired yet</span> | Owner rec: A. Checks; fallback B |
| Front end (D-18) | FE-A, FE-B, FE-C | FE-B: <span class="risk-orange">ORANGE: medium</span> | Owner rec: FE-B; §9.1 closure pending |
| Supply architecture | P0 as drawn; P1, P4, P5 | <span class="risk-red">RED: overall B−. Beat between clocks</span> | P1 or P5: <span class="risk-orange">ORANGE: overall B+</span> |
| UART cable power | Cable, regulator, or 5 V parts | <span class="risk-red">RED: isolator 5 V range unknown</span> | Open: which option handles 5 V? |
| Drain-node capacitance | Mux drop, symmetry, calibration, tests | <span class="risk-orange">ORANGE: medium</span> | Open: 50–60 pF valid after D-19? |
| Band-pass filter | Fixed 518 Hz, switchable, wide | <span class="risk-orange">ORANGE: medium</span> | Open: team decides; no recommendation |

Legend: GREEN low, ORANGE medium, RED high. Risk now: owner's option or worst.

Source: Slides S18–S24 of this deck; their sources.

<!-- Facts: from S18…S24 slides. Say: Each row is one open decision. Risk now copies the source grade: the owner's option where recommended, else the worst shown. The MCU is red today because its sheet is open; the owner recommends it on the board, with EVB fallback. FE-B is orange on first-pass D-18 score 3 of 5, with an open TMUX6136 supply. Supply, UART and drain-node items stay open. Band-pass has no recommendation. Nothing is re-graded here. -->
