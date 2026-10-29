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

<span class="tag tag-proposed">PROPOSED: owner may drop</span>

# Board takes USB-C power or a lab supply

| Input | Voltage | Notes |
|-------|---------|-------|
| USB-C PD (power delivery over USB-C) | 12 V (15 V fine) | Converters will not start on 5 V |
| Lab supply, terminal block J4 | 11–15 V | Either input works, neither feeds other |
| Heaters (+5VP) | Own +5VP regulator | Keeps heater current off analog rail |
| Not in docs | — | USB current, J4 rating, heater current |

Open: +7 V rail, made by a buck (step-down) converter. Requirements say +7 V; schematic overview gives 7.02 V calculated, 4.33 V drawn. Owner check.

Source: schematics/LIA-board/docs/requirements.md §R.1 (DC-1, DC-2, DC-4b); schematics/LIA-board/docs/schematic_overview.md §3.1–§3.3; schematics/LIA-board/docs/README.md §9.1 (D-10)

<!-- Facts: S04-F01, S04-F02, S04-F03, S04-F05, S04-F08, S04-F17, S04-C02, S04-NF01, S04-NF02, S04-NF03. Say: Plug in USB-C power delivery at 12 V (15 V fine), or a lab supply on terminal J4 at 11 to 15 V. A 5 V-only USB source will not start the converters. Heaters have their own regulator, separate from the analog rail. The +7 V rail is open: the requirements say +7 V; the schematic overview gives 7.02 V calculated and 4.33 V drawn. The USB current, J4 rating and heater current are not in the docs. -->
