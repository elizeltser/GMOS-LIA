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

# Bench has no switch; board adds switch banks

| Stage | ATE bench (automatic test equipment) | Board (planned analog route) |
|---|---|---|
| Gate | LIA offset plus amplitude | DAC DC level plus sine stages |
| Drain | About 330 kΩ to drain-bias channel | Drain resistor, then SWITCH bank A |
| Readout | Two drains into Stanford SR560 amp | In-amp G=10 taps R_D/switch node |
| Heater | Lab supply on heaters | SWITCH bank B to heaters |
| Pixel select | Not in docs: bench selection | SWITCH banks A/B: one active+blind pair |

SWITCH = switch stage added on the board. LIA = lock-in amplifier; DAC = digital-to-analog converter; in-amp = instrumentation amplifier; R_D = drain resistor.

Source: ate_lia/FSD.md "Signal Chain"; schematics/LIA-board/docs/schematic_overview.md §4.2, §4.7; schematics/LIA-board/docs/README.md §9.1 D-19; schematics/LIA-board/docs/measurement_principles.md §2.3

<!-- Facts: S07-F01, S07-F02, S07-F03, S07-F10, S07-F12, S07-F15, S07-F19, S07-F23, S07-NF05. Say: On the bench, two drains feed an SR560 differential amplifier into the SR860 lock-in; no switch is listed. The board follows that chain, but drains and heaters pass through TMUX1109 switch banks, with one active and one blind pixel measured at a time. D-19 removed the readout muxes, so the in-amp taps the R_D/switch node. Owner's view: the analog route with switches carries some risk. -->

---

# Open items on the switch route and bench

| Item | What the docs say | Status |
|---|---|---|
| Drain-node capacitance (mux open) | 50–60 pF (README §9.2 item 10) | Open: 38 pF in §4.4 |
| Common-mode leakage at drain node | 44 dB at 6 pF mismatch | Re-run open; was 53 dB |
| Demodulator switch (TMUX6136) | Needs 10 V; board 5 V | Open: design issue DI-01 |
| Drain/heater switch (U20/U21) | No datasheet values or simulation | Not in docs |
| Bench settings (C01–C03) | SR560 gain, coupling, offset differ | Open conflict; owner resolves |

Only sourced risks are listed. Mux capacitance is open: decision D-19 removed readout muxes; README §9.2 item 10 still names TMUX1104 readout mux.

Source: schematics/LIA-board/docs/README.md §9.1 D-19, §9.2 item 10; schematics/LIA-board/docs/schematic_overview.md §4.4; simulations/design-issues.md DI-01; ate_lia/FSD.md "Signal Chain"; schematics/LIA-board/docs/measurement_principles.md §2.3

<!-- Facts: S07-F20, S07-F21, S07-F22, S07-F23, S07-F27, S07-F30, S07-NF07, S07-NF08, S07-C01, S07-C02, S07-C03, S07-C05, S07-C06, S07-C07. Say: Drain-node capacitance is open: README §9.2 item 10 gives 50–60 pF with TMUX1104, while §4.4 gives 38 pF and D-19 removed the readout muxes. Leakage is 44 dB at 6 pF mismatch, and 53 dB at the old 20 pF assumption. The demodulator's behavioural switch is simulated; no simulation models the drain or heater switch. Owner resolves C01–C03, not yet listed in README §9.2. -->
