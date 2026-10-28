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

# Board power: USB-C or lab supply

- <span class="tag tag-hard">HARD: must</span> Lab supply and USB-C power; neither feeds the other.
- <span class="tag tag-fluid">FLUID: TBD</span> USB-C power delivery (PD): 11–15 V (docs disagree, see open items).
- <span class="tag tag-fluid">FLUID: TBD</span> +7 V rail, ripple ≤10 % (docs disagree, see open items).
- <span class="tag tag-fluid">FLUID: TBD</span> Negative rails only if front-end option (D-18) is FE-A or FE-B.
- <span class="tag tag-hard">HARD: must</span> Linear regulators: analog (+5VA), heater (+5VP), digital (+3V3_D).
- <span class="tag tag-hard">HARD: must</span> Converter switching never falls in the 377–711 Hz band.

Source: schematics/LIA-board/docs/requirements.md §R.1; simulations/design-context.md §2

<!-- Facts: S02-F01, S02-F02, S02-F03, S02-F04, S02-F05, S02-F06, S02-F07. Say: PD is power delivery over the USB-C cable. The lab supply is a second input through Schottky diodes, and neither input may feed the other. FE is the front-end circuit choice; D-18 is that decision. FLUID here means disputed or undecided in the docs; the tags are the author's reading. Supply values also disagree with the design-context document. -->

---

# Excitation, bias and filter band

- <span class="tag tag-fluid">FLUID: TBD</span> Excitation 518 Hz default; range disputed (see open items).
- <span class="tag tag-fluid">FLUID: TBD</span> Sine excitation; square X/Y references (docs disagree, see open items).
- <span class="tag tag-hard">HARD: must</span> Gate DC 0.97–1.2 V, step ≤100 µV; AC 0.5–20 mVpp.
- <span class="tag tag-hard">HARD: must</span> Six pixels; one active, one blind at a time.
- <span class="tag tag-hard">HARD: must</span> Sensor bias 330 kΩ/side, 5–10 µA; heater 2.5–4.0 V.
- <span class="tag tag-fluid">FLUID: TBD</span> Amplifier gain 10 (docs disagree, see open items); band 377–711 Hz.

Source: schematics/LIA-board/docs/requirements.md §R.2.1–R.2.4, §R.2.6; simulations/design-context.md §1, §4

<!-- Facts: S02-F08, S02-F09, S02-F10, S02-F11, S02-F12, S02-F13, S02-F14, S02-F15, S02-F17, S02-F18. Say: Excitation is the test signal. X and Y are the two demodulator references, in phase and quadrature. mVpp is millivolts peak to peak. A pixel is one sensor element. Gate nets GATE_A and GATE_B drive pixels 1–3 and 4–6; TMUX1109 switches connect one active and one blind pixel at a time. The sensor electrical model is not in the docs (S02-NF01). -->

---

# Signal chain, ADC and PC link

- <span class="tag tag-hard">HARD: must</span> Chain: instrumentation amplifier (in-amp), two second-order filters, demodulator, post-filter.
- <span class="tag tag-hard">HARD: must</span> Passes 50 mV peak before clipping; common-mode rejection (CMRR) ≥100 dB.
- <span class="tag tag-fluid">FLUID: TBD</span> Post-filter time constant 500 ms (docs disagree, see open items).
- <span class="tag tag-fluid">FLUID: TBD</span> Analog-to-digital (ADC) choice: 24-bit ADS1220 (docs disagree, see open items).
- <span class="tag tag-hard">HARD: must</span> Microcontroller (MCU) STM32U575RGT6: 16 MHz clock; isolated UART to PC.
- <span class="tag tag-fluid">FLUID: TBD</span> Firmware frequency 305–700 Hz (docs disagree, see open items).

Source: schematics/LIA-board/docs/requirements.md §R.2.4–R.4.1; simulations/design-context.md §1, §5

<!-- Facts: S02-F16, S02-F19, S02-F20, S02-F21, S02-F22, S02-F23, S02-F24, S02-F25. Say: The demodulator multiplies by plus or minus one, using references from the MCU. CMRR is common-mode rejection ratio, specified at gain 10. UART is a serial data link, here isolated from the PC side. ADC samples at 20 to 1000 samples per second (SPS). Not in docs: sensor electrical model (S02-NF01). -->
