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

# Who makes which signal: MCU or analog

| Item | Value | MCU (firmware) | Analog hardware |
|---|---|---|---|
| Gate excitation | 518 Hz, 5 mV peak-to-peak default | MCU's built-in DAC, sine table | Two MFB gate filters |
| Lock-in reference signals | 50 % squares, 90° apart | Hardware timer outputs | Not in docs |
| Gate DC bias | 0.97–1.2 V | Control path not in docs | DAC80508 chip, two channels |
| Drain bias | 0.5–3.5 V supply | Control path not in docs | Four DACs, difference amplifier |

MCU: microcontroller. DAC: digital-to-analog converter. MFB: multiple-feedback filter. DAC80508: bias DAC chip. Split derived from cited rows. Heater setpoints: separate topic, not covered here.

Source: schematics/LIA-board/docs/requirements.md §R.2.1, §R.2.2, §R.4.1; schematics/LIA-board/docs/schematic_overview.md §4.5, §4.6.3; schematics/LIA-board/docs/README.md §9.1

<!-- Facts: S09-F01, S09-F02, S09-F04, S09-F09, S09-F14, S09-F18. Say: The microcontroller (MCU) makes the 518 Hz gate sine and the two 90-degree reference square waves from one timer chain, so they stay phase-locked. Analog parts shape the gate signal and set the bias voltages. How firmware writes to the bias DACs is not in the docs. Heater setpoints are out of scope for this topic. -->

---

# Three source conflicts remain open

| Item | Source A says | Source B says | Status |
|---|---|---|---|
| Excitation range | requirements.md §R.2.1: 400–700 Hz | requirements.md §R.4.1: 305–700 Hz | Open |
| Frequency tolerance | requirements.md §R.2.1: ±20 ppm accuracy | requirements.md §R.2.1: ±50 ppm stability | Open |
| Drain amplifier gain | requirements.md §R.2.2: k = 0.1 (target) | schematic_overview.md §4.6.3: k = 1 (drawn) | Open |

k: gain ratio, feedback over input resistor. ppm: parts per million. Tolerance rows: accuracy vs stability. Not in docs: DAC control bus; offset calibration.

Source: schematics/LIA-board/docs/requirements.md §R.2.1, §R.2.2, §R.4.1; schematics/LIA-board/docs/schematic_overview.md §4.6.3

<!-- Facts: S09-C01, S09-C03, S09-C04, S09-NF01, S09-NF02. Say: Three source conflicts are open, and the deck takes no side. Excitation range is 400–700 Hz in one place and 305–700 Hz in another. The tolerance may be accuracy in one place and stability in another; the sources do not say whether these are the same quantity. The drain amplifier gain target k = 0.1 differs from the drawn k = 1. -->
