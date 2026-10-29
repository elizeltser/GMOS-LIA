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

# Fluid requirements and what blocks them

<span class="tag tag-fluid">FLUID: TBD</span>

| Item | Open point | Blocked by |
|------|-----------|-----------|
| Front end (D-18, front-end decision) | AD630, switch, or 5 V design | Decision D-18 (owner recommends FE-B) |
| Supply (docs disagree) | One 5 V rail or ±5 V | Owner decision (DI-10) |
| Band (docs disagree) | 518 Hz; ≈400–700 Hz | Decision: wider or switchable band-pass |
| Demodulator switch | TMUX6136 supply margin: Critical | Test R-04 (TMUX1136 parameters) |
| Sensor impedance | Impedance not in docs | Impedance range; test R-01 |

Owner recommends FE-B (switch demodulator), pending closure in README §9.1. Disagreements: see open items.

Source: schematics/LIA-board/docs/README.md §9.1 D-18, §9.2 item 6; schematics/LIA-board/docs/requirements.md §R.2.1 AN-1; simulations/design-issues.md DI-01, DI-10, DI-11; simulations/design-context.md §1, §9

<!-- Facts: S03-F01, S03-F02, S03-F05, S03-F07, S03-F08, S03-F09, S03-F12, S03-F13. Say: Five items stay fluid. D-18 picks the front end: FE-A (AD630, a single source), FE-B (switch demodulator) or FE-C. The owner recommends FE-B, pending formal closure. The supply choice is the owner's, and the docs disagree on it. The switch's supply margin is Critical, so test R-04 reruns with TMUX1136 parameters. Loading exceeds 0.1 % (Draft) from 100 Ω per leg. -->
---
# Other fluid items and what they wait for

<span class="tag tag-fluid">FLUID: TBD</span>

- Sensor common mode: INA828 (input amplifier) kept only if 2.1–2.9 V.
  - Blocked by: sensor common-mode value (TBD).
- ADC: requirements AN-30 names ADS1220; design-context says not chosen.
  - Blocked by: resolution target, TBD (DI-13).
- Phase error: 76 % of samples exceed 1° (Draft) at current tolerances.
  - Blocked by: calibration or C0G (stable) capacitors, 0.1 % thin-film resistors (DI-08).
- Not in docs: sensor signal range and offset.

Source: schematics/LIA-board/docs/requirements.md §R.2.7 AN-30; simulations/design-context.md §1; simulations/design-issues.md DI-02, DI-08, DI-13

<!-- Facts: S03-F10, S03-F18, S03-F23, S03-NF01. Say: Four smaller items remain. The INA828, an input amplifier, stays only if the sensor common mode holds at 2.1 to 2.9 volts, and that value is not in the docs. The ADC: requirements name ADS1220, but design-context says not chosen, and the resolution target is TBD. At current tolerances, 76 percent of samples exceed the one-degree draft limit. The sensor signal range is not in the docs. -->
