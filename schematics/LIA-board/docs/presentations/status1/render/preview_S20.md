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

# Supply architecture: one converter or two

| Option | What it is | Risk | Mitigation |
|---|---|---|---|
| P0 (as drawn) | Two converters on 12 V PD | <span class="risk-red">RED: overall B−. Beat between clocks</span> | Post-filter beat; effort medium-hard |
| P1 | One chip, 5 V USB only | <span class="risk-orange">ORANGE: overall B+. Changes requirements</span> | Team approves requirement change |
| P4 | P1 plus bench ±9 V input | <span class="risk-orange">ORANGE: overall B+. Source-current limit</span> | Require 1.5 A or 3 A |
| P5 | One converter, diode pump, negative rail | <span class="risk-orange">ORANGE: overall B+. Unregulated negative rail</span> | Measure pump ripple first |

Legend: GREEN low, ORANGE medium, RED high. PD: USB Power Delivery.

Open question: is a 5 V USB-only input acceptable?

Source: schematics/LIA-board/docs/decisions/DC_tps6513x_study.md §2, §2.2, §4, §6.1, §7

<!-- Facts: S20-F15, S20-F16, S20-F26, S20-F27, S20-F29, S20-F34, S20-F35, S20-F37, S20-F44, S20-F24, S20-F25, S20-F32, S20-F38. Say: P0 has two free-running clocks, so the beat can only be filtered. P1 uses one chip, but changes requirements and shares the 100 mA USB source limit. P4 adds a bench input, and P5 keeps the 12 V PD input with an unregulated negative rail. Colours follow the study's overall grades. P2, P3 and P6 exist in the study and are not shown. -->

---
# Supply architecture (cont.)

- Study: if 5 V USB is acceptable, P1, built as P4 first.
- Study: if 12 V PD must stay, P5.
- Conflict, open: design-context §2 says 0–5 V; study §8.1 says ±5 V.
- Owner recommends FE-B (not yet closed); it keeps the negative rail.
- Not shown: P2, P3, P6.

Source: schematics/LIA-board/docs/decisions/DC_tps6513x_study.md §6.1, §8.1; simulations/design-context.md §2

<!-- Facts: S20-F45, S20-F46, S20-F47, S20-C02, S20-F51, S20-F10, S20-F24, S20-F25, S20-F32, S20-F37, S20-F50, S20-F49. Say: The 5 V branch picks P1, built as P4 first; the 12 V PD branch picks P5. P1 and P5 score about the same. P3 is bench only; P6 is not graded. The single-rail versus ±5 V conflict is reported, not resolved. The owner recommends FE-B, not yet closed; it keeps the negative rail. -->
