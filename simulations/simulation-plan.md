# GMOS LIA Board — Simulations

Single place for every simulation: what it must show, how it is set up, pass criteria, and the recorded result. Lab measurements are in [preliminary_lab_test_results.md](../schematics/LIA-Readout/docs/preliminary_lab_test_results.md); theory in [measurement_principles.md](../schematics/documents/measurement_principles.md); requirement IDs in [requirements.md](../schematics/LIA-Readout/docs/requirements.md).

**Rules**
- Each board-level simulation has an ID `SIM-xx` (what must be shown and the pass criteria). The runs that answer it are entries `C-xx`/`P-xx` of [simulation-index.md](simulation-index.md), and their files live in the simulation project that ran them (currently [`ti-pspice/`](ti-pspice/CLAUDE.md): netlists in `circuits/`, results in `docs/sim-results/<ID>.md`).
- Use vendor models (TI PSpice / ADI LTspice) for every active part in a decision-relevant simulation. Generic models (ideal SPDT, ideal op-amp) are allowed only for topology checks and must be labelled so.
- Plot **averages over an integer number of reference periods after settling**, never `max()` of a demodulated output (it includes the 2f₀ ripple).
- Record numbers, not only plots: every pass criterion below is a number.
- A superseded simulation stays listed with status "obsolete".

---

## 7. Simulation Index

### 7.1 Completed / Historical

| ID | Simulation | Tool / file | Verifies | Status / result |
|----|------------|-------------|----------|-----------------|
| SIM-1 | Analog quadrature oscillator transient | ngspice | Rev A oscillator | Obsolete (D-3) |
| SIM-2 | System CMRR Monte-Carlo (50 000 trials, C_node = 20 pF) | Python | [§2.7](../schematics/documents/measurement_principles.md#27-common-mode-rejection) | Done; **re-run needed with C_node = 50–60 pF** (SIM-12) |
| SIM-3 | CMRR SPICE cross-check (60 runs) | ngspice | §2.7 | Done |
| SIM-4 | Band-pass tolerance Monte-Carlo (unity-gain SK, 4:1 ratios) | Python | [§2.8](../schematics/documents/measurement_principles.md#28-band-pass-filter-design) | Done; superseded by SIM-14 if the K = 2 band-pass is chosen |
| SIM-8 | Heater driver with Kelvin feedback driving 600 Ω (and 300 Ω): stability, headroom from +5VP | ngspice | AN-13, AN-14 | TODO (not decision-relevant for D-18) |
| SIM-D1 | Discrete switch demodulator, topology check: ideal SPDT + OPA192, single 5 V, V_REF = 2.5 V, input 2 V pk at 517 Hz, phase swept 0–180° | PSpice (user, 2026-10-26) | Switch-demodulator principle ([§2.16](../schematics/documents/measurement_principles.md#216-switch-based-synchronous-demodulator)) | **Pass (topology).** X = 2.5 − 1.273·cos θ V, Y = 2.5 + 1.273·sin θ V, matching (2/π)·2 V = 1.273 V. Generic switch model, max() plotting; must be repeated with vendor models (SIM-10…SIM-13) |

### 7.2 Front-End Architecture Decision (D-18): Required Simulations

The three candidate architectures are defined in [schematic_overview.md §4.9](../schematics/LIA-Readout/docs/schematic_overview.md#49-front-end-architecture-options-decision-d-18):
- **FE-A** — ±5 V, INA828, unity-gain SK band-pass, 2× AD630 (gain ±2), post-filter −3 (as drawn 2026-10-24).
- **FE-B** — ±5 V, INA828, K = 2 SK band-pass, discrete demodulator (TMUX6136 + OPA2196, gain ±1), post-filter −1.5.
- **FE-C** — single 5 V + V_REF 2.5 V (REF3325), INA333 with LM7705 (−0.23 V) on V−, K = 2 SK band-pass, discrete demodulator (2× TMUX1219), signal-path op-amps **OPA2365** (zero-crossover; the OPA2196 input transition region is 2.0–3.5 V on a 5 V rail, see [§2.15](../schematics/documents/measurement_principles.md#215-single-supply-referencing-v_ref)), post-filter −1.5. Removes the −7 V / −5 V rails.

For FE-C, SIM-11 must also be run with the OPA2196 model in place of the OPA2365 to quantify the transition-region error (distortion and offset step around 2–3.5 V); for FE-B, check at full scale (2.14 V pk) that the OPA2196 inputs stay below +2 V.

Simulations marked **all** are run for every candidate still under consideration; the decision matrix in §7.4 is filled from them.

| ID | What | Applies to | Setup | Pass criteria |
|----|------|-----------|-------|---------------|
| SIM-10 | Demodulator transfer with vendor models | B, C (A: AD630 model) | Input = sine at f₀ around the reference (0 V for A/B, V_REF for C), amplitudes **0.4 V pk (default)** and **2.1 V pk (full scale)** at the demodulator input; θ = 0…360° in 15° steps; references = ideal 0/3.3 V squares, Y delayed T/4. Average the demodulator output over 20 periods after 10 periods settling | X(θ), Y(θ) within ±0.5 % of (2/π)·A·{cos, sin} after a single gain/phase calibration; X/Y orthogonality error ≤ 0.2° |
| SIM-11 | Demodulator linearity and offset | all | θ = 0 and 90°; amplitude 1 mV → 2.1 V pk in decade steps; plus input = reference level (zero signal) | Gain deviation ≤ 0.1 % over 10 mV…2.1 V; zero-input offset at the demodulator output recorded (it is subtracted in firmware); offset ≤ 1 mV |
| SIM-12 | System CMRR with real node capacitance | all | Drain nodes: R_D = 330 kΩ (0.1 % MC), C_node = 50 pF ± 10 % (mux on-cap + INA input + traces), common-mode drive 300 mVpp at f₀ through both R_D; Monte-Carlo ≥ 200 runs | Median system CMRR ≥ 48 dB; leakage reported separately in X and Y |
| SIM-13 | Full chain with vendor models | all | Drain-node sources → in-amp → band-pass → demodulator → post-filter (τ may be reduced to 50 ms to shorten the run; scale the ripple result). DC drain mismatch 0, +200 mV, −200 mV. Excitation 10 mV pk differential | Scale factor at the ADC within ±1 % of the design value (−38.2·v̂·cos θ for all three candidates); no stage clips at ±200 mV mismatch; ripple at the ADC input ≤ 1 LSB-equivalent of the 20-SPS noise (≈ 3 µV) after the analog + ADS1220 digital filter |
| SIM-14 | Band-pass tolerance (K = 2 equal-component SK) | B, C | Monte-Carlo: R 0.1 %, C 1 % C0G, ≥ 1000 runs | Gain at f₀ 4.00 ± 1 %, phase at f₀ 0 ± 2°, f₀ 518 ± 1 % |
| SIM-15 | Harmonic and interference rejection | all | Inject at the in-amp input: 2f₀, 3f₀, 500 Hz, 550 Hz (mains harmonics), 50 Hz, each 10 mV pk; measure X/Y | Rejection relative to an f₀ signal of the same amplitude: 2f₀ ≥ 40 dB, 3f₀ ≥ 25 dB (square-wave demodulation passes 1/3), 50 Hz ≥ 60 dB, 500/550 Hz ≥ 30 dB with τ = 0.5 s (the 18 Hz beat between 518 Hz and the 10th mains harmonic is only attenuated ≈ 35 dB by a 0.5 s first-order filter; longer software τ or moving f₀ to ≈ 525 Hz improves it) |
| SIM-16 | Noise (.NOISE + transient) | all | Two drain shot-noise current sources √(2qI_D), I_D = 7.5 µA, in parallel with R_D; R_D thermal noise; vendor op-amp/in-amp noise. Output noise at the ADC in 0.5 Hz ENBW | Total ≈ 31 µV rms (sensor-limited); amplifier contribution ≤ 10 % of total noise power |
| SIM-17 | Post-demodulator offset drift | all | Vendor-model offset and drift (or datasheet worst case in a spreadsheet), ΔT = 20 °C, referred to the drain | ≤ 0.2 µV/°C referred to the drain differential |
| SIM-18 | Power-up / sequencing | all (C: LM7705 + REF3325) | Ramp each rail in all orders (5 ms ramps), references off | No latch-up, no op-amp output stuck at a rail after all rails are up, demodulator recovers within 1 s |
| SIM-19 | Excitation chain | all | DAC1 sample-and-hold source (128 samples/period, 12-bit quantization) → MFB stage (gain −1/120) → gate capacitance (3 pixels + socket ≈ 50 pF) | Gate amplitude 5.0 mVpp ± 1 %; THD ≤ 0.3 %; image at 66 kHz ≤ −40 dBc at the gate; phase lag at f₀ recorded (≈ 8°); A/B stage mismatch ≤ 0.2 % / 0.1° in Monte-Carlo |
| SIM-20 | Drain bias difference amplifier | all | U10A: V_out = (1+k)·V_DAC2 − k·V_DAC6, k = 0.1, with 1 kΩ + 10 µF output filter, DAC noise source 100 nV/√Hz | Output range 0.5–3.5 V; noise at the drain node ≤ 50 nV/√Hz at f₀ (≤ 1 % of the shot-noise power) |

### 7.3 Simulation Results (fill in)

| ID | Date | Candidate | Tool / models | Key numbers | Pass? | Files |
|----|------|-----------|---------------|-------------|-------|-------|
| SIM-D1 | 2026-10-26 | B/C topology | PSpice, ideal SPDT, OPA192 | X: 1.227…3.773 V, Y: 2.5…3.773 V over θ = 0…180° | ✓ topology | `simulations/ti-pspice/archive/2026-10-26_lia_sanity_ost_sweep/` (index C-07) |
| | | | | | | |

### 7.4 Decision Matrix for D-18 (fill in from §7.3 and research)

Scores 1–5 (5 = best). Weight in brackets. A criterion that fails a pass threshold above disqualifies the candidate unless a fix is identified.

| Criterion (weight) | FE-A (AD630, ±5 V) | FE-B (switch, ±5 V) | FE-C (switch, single 5 V) | Evidence |
|--------------------|--------------------|---------------------|---------------------------|----------|
| First-pass success risk (×3) | | | | SIM-10…13, 18; maturity of each topology |
| Accuracy: scale factor, linearity, X/Y orthogonality (×2) | | | | SIM-10, 11, 13 |
| Baseline drift after the demodulator (×2) | | | | SIM-17 |
| Noise (×1) | | | | SIM-16 |
| CMRR / interference (×2) | | | | SIM-12, 15 |
| Part availability (JLC stock, second source) (×2) | | | | Research: AD630 not stocked at JLC; TMUX6136 ≈ 158 pcs at JLC (2026-10-24) |
| BOM cost (×1) | | | | Research |
| Board area / routing / number of rails (×1) | | | | Layout estimate |
| Schematic change effort from the 2026-10-24 netlist (×1) | | | | schematic_review.md |
| **Weighted total** | | | | |

**Decision rule.** Choose the highest weighted total among candidates with no failed pass criterion. If FE-B and FE-C are within 10 %, prefer FE-C only if SIM-18 passes and the single-supply front end shows no clipping at ±200 mV drain mismatch (SIM-13); otherwise FE-B.