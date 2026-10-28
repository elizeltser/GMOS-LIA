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

# What I need from the team

| Item | Type | Owner | Next step |
|------|------|-------|-----------|
| D-18 front end (FE-A/B/C) | Decision | Eli | Fill D-18 record, then decide |
| VDDA source; UART cable power | Decisions | Owner not named | VDDA before routing; UART at T08 |
| Band-pass width (fixed or wider) | Team question | Team | Decide; no recommendation yet |
| EVB fallback connector; socket reason | Team ask; owner ask | Team; Eli | Choose type and count; S06 reason |
| Heaters, excitation, drain swing | Measurements | Owner not named | Bench measure, then record in §9.2 |

Parts: AD630 single source (research R1); TMUX1109PWR low stock; INA828 range (TI calculator).

Source: schematics/LIA-board/docs/README.md §9.1–§9.2; schematics/LIA-board/docs/schematic_review.md §1, §3; simulations/simulation-plan.md §7.2

<!-- Facts: S30-F01, S30-F03, S30-F04, S30-F06, S30-F07, S30-F11, S30-F12, S30-F14, S30-F16, S30-F17, S30-F19, S30-F20, S30-F21, S30-NF01. Say: D-18 stays open until the record is filled and the owner decides. The EVB connector type, pinout and count are not in the docs, so the team chooses. The socket is decided, and its reason goes on the S06 slide. Readout capacitance (SIM-2 at 60 pF) and the FE-C op-amp check (SIM-11) are also open and are in S30 sources. -->
