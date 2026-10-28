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

# Nearby goals: next tasks and dependencies

| Task | Depends on (documented) | Note |
|---|---|---|
| Decide front-end architecture (T00, D-18) | Simulations SIM-10 to SIM-20 | One topology run only |
| Power and front-end sheets (T03, T04) | Decision D-18 | Both marked per D-18 |
| Excitation, DAC, ADC, SoC sheets | No dependency stated | Tick when checks pass |
| MCU sheet and isolated UART (T08) | Cable supply D-21 | LDO if needed |
| Footprints and docs sync (T09, T10) | T10: all tasks ticked | Netlist check (T09) |

Documented: T00 first, then T01 to T05, then T06 to T10. Conflict: node capacitance 50 pF (SIM-12) vs 50–60 pF (README). Order: owner decides.

Source: schematics/LIA-board/docs/schematic_review.md §0, §1, §3; simulations/simulation-plan.md §7.2, §7.3; schematics/LIA-board/docs/README.md §9.2 item 10

<!-- Facts: S28-F01, S28-F03, S28-F04, S28-F06, S28-F07, S28-F08, S28-F09, S28-F10, S28-F11, S28-F12, S28-F13, S28-C01. Say: The documented order puts the T00 decision first. D-18 requires SIM-10 to SIM-20 for each candidate, and only SIM-D1 has a recorded result. Power and front-end sheets are marked per D-18. T01, T02, T06, T07 are the excitation, SoC, DAC and ADC sheets. The MCU sheet step 2 (T08) touches open D-21. No simulation is documented as unblocking any sheet, so none is paired. -->
