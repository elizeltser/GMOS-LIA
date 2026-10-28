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

# Simulation: the switch model is hopeful, unchecked

| Element | Model | Status |
|---|---|---|
| Switch (C-01) | Behavioural `SPDT_PREC`, not TI | Hopeful: values unchecked |
| Switch part name | TMUX6136 (C-01) vs TMUX1136 (P-21) | Open: owner decides (DI-01) |
| OPA192, INA828 | TI models | Not stated as checked to datasheet |
| Ideal SPDT + OPA192 (SIM-D1) | Generic switch, max() plotting | Topology only: principle, not numbers |
| Demodulator noise (P-15) | Estimate | Not simulated |

Workflow: entry, run, analysis, grade, review. PSpice: owner's Windows PC only.

Ideal SPDT lacks on-resistance, capacitance, charge, leakage, delay.

Source: simulations/simulation-index.md (lines 48, 409); simulations/ti-pspice/vendor/README.md §3, §5; simulations/simulation-plan.md (Rules, line 25); simulations/ti-pspice/CLAUDE.md

<!-- Facts: S16-F02, S16-F03, S16-F06, S16-F10, S16-F12, S16-F13, S16-F16, S16-F18, S16-F23, S16-F31, S16-F35, S16-C01. Say: "Hopeful" is the owner's word. SPDT_PREC is not a TI model, built from datasheet parameters whose values were never checked. The OPA192 and INA828 are TI models; no datasheet check is stated, and the INA828 gain was checked at one RG. SIM-D1 used an ideal SPDT with an OPA192 and plotted max(). C, P and SIM labels are test IDs of the simulation index. -->
