# LIA-Readout — Verification (Simulation & Lab Tests)

Simulations and measurements that verify the design values in [measurement_principles.md](../../documents/measurement_principles.md) and [schematic_overview.md](schematic_overview.md) against [requirements.md](requirements.md).

## 7. Simulation

Moved to [simulation-plan.md](../../../simulations/simulation-plan.md) (2026-10-28), which holds the simulation index, the required simulations SIM-10…SIM-20 with pass criteria, the results table and the D-18 decision matrix. Earlier IDs map as follows: SIM-1…SIM-4 unchanged; SIM-5 → SIM-19; SIM-6 → SIM-13; SIM-7 → SIM-10/SIM-13 (FE-A); SIM-8 kept as a TODO in simulations.md §7.1.

---

## 8. Lab Tests

Results measured with lab equipment are collected here. Raw data (scope screenshots, CSV exports, SR860 logs) go in `lab/<test-id>/`, named `YYYY-MM-DD_<short-description>.<ext>`; each results row links to its files. Add a row per run; never overwrite earlier runs.

### 8.1 Equipment

| Instrument | Model / serial | Used in | Notes |
|------------|----------------|---------|-------|
| Oscilloscope | | LAB-1, 3, 4 | |
| Oscilloscope probes | | LAB-1, 3, 4 | 10× passive (10 MΩ ∥ ≈ 10–15 pF) |
| Lock-in amplifier | SR860 [[M1]](README.md#ref-m1) | LAB-2, 5, 9 | |
| Low-noise preamplifier | SR560 [[M2]](README.md#ref-m2) | LAB-2 | |
| Function generator | | LAB-5, 6 | |
| USB-C PD source (≥ 12 V PDO) and bench supply | | LAB-3 and board supply | Bench supply only if the optional lab input is fitted; set current limit |
| DMM / SMU | | LAB-7, 8 | |

### 8.2 Test Index

| ID | Test | Verifies | Bench / board | Status |
|----|------|----------|---------------|--------|
| [LAB-1](#lab-1-drain-node-waveforms-oscilloscope) | Drain node waveforms | Drain DC, AC swing, CM level, excitation amplitude unit ([§2.4](../../documents/measurement_principles.md#24-transistor-operating-point)) | Bench (now) | Not started |
| [LAB-2](#lab-2-bench-lock-in-reference-levels-sr560--sr860) | Bench lock-in reference levels | Signal level ([§2.5](../../documents/measurement_principles.md#25-expected-signal-level-from-bench-data)) | Bench (now) | Not started |
| [LAB-3](#lab-3-power-rails-and-pd-negotiation) | Power rails and PD negotiation | DC-1…DC-7, [§3.4](schematic_overview.md#33-design-calculations) | Board | Not started |
| [LAB-4](#lab-4-excitation-and-references) | Excitation and references | AN-1…AN-7b | Board | Not started |
| [LAB-5](#lab-5-band-pass-response) | Band-pass response | AN-20…AN-22 | Board | Not started |
| [LAB-6](#lab-6-common-mode-rejection) | Common-mode rejection | AN-23 | Board | Not started |
| [LAB-7](#lab-7-drain-bias-current-readback-and-r0) | Drain bias, current readback, r₀ | AN-9…AN-11, decision D-8 | Bench + board | Not started |
| [LAB-8](#lab-8-heater-drive-and-current-readback) | Heater drive, resistance, current readback | AN-13…AN-18, open item 2 | Bench + board | Not started |
| [LAB-9](#lab-9-full-chain-vs-sr860) | Full chain vs SR860 | Scale factor and phase ([§2.9](../../documents/measurement_principles.md#29-gain-distribution-headroom-and-demodulator-output)) | Board + bench | Not started |
| [LAB-10](#lab-10-on-board-calibration-loopback) | On-board calibration loopback | AN-29e, [§2.13](../../documents/measurement_principles.md#213-calibration) | Board | Not started |

### 8.3 Tests

#### LAB-1 Drain Node Waveforms (Oscilloscope)

**Purpose.** Measure the real drain DC level and AC swing of each transistor and the active − blind difference, to confirm the common-mode level and stage gain assumed in [§2.4](../../documents/measurement_principles.md#24-transistor-operating-point). Also measure the gate excitation directly to settle whether the SR860 "5 mV" setting is rms (README §9.2 item 3).

**Setup.** Existing 3T bench setup. CH1 on drain A, CH2 on drain B, 10× probes, DC coupling for DC level and AC coupling for swing; math CH1 − CH2. Averaging ≥ 16, 20 MHz bandwidth limit. A 10× probe loads the drain with ≈ 10 MΩ ∥ 12 pF, lowering the swing by ≈ 3 %; note it. Then probe the gate (AC coupled) and record Vpp.

**Expected.** Drain DC 50–250 mV; per-drain swing ≤ ≈ 200–400 mVpp per 5 mVpp excitation (upper bound); differential much smaller than either drain; gate ≈ 14.1 mVpp if the setting is rms.

| Run | Date | V_G DC | δV_GS setting / measured (mVpp) | V_heater A / B | I_D A / B | V_D DC A / B | v_d A / B (mVpp) | v_A − v_B (mVpp) | Phase A vs B | Files | Notes |
|-----|------|--------|----------------------------------|----------------|-----------|--------------|------------------|------------------|--------------|-------|-------|
| | | | | | | | | | | | |

#### LAB-2 Bench Lock-in Reference Levels (SR560 / SR860)

**Purpose.** Record the maximum X/Y/R on the bench chain at the planned operating points, to confirm [§2.5](../../documents/measurement_principles.md#25-expected-signal-level-from-bench-data) and the gain plan of [§2.9](../../documents/measurement_principles.md#29-gain-distribution-headroom-and-demodulator-output). Repeat at several excitation amplitudes (e.g. 2, 5, 10 mVrms) to see linearity and decide open item 5.

**Expected.** X/Y ≤ ≈ 400 mVrms with SR560 gain 20 and 5 mVrms excitation (≤ 20 mVrms differential at the drains), scaling linearly with excitation.

| Run | Date | Excitation (SR860) | V_G DC | V_heater A / B | SR560 gain / filter | SR860 τ / slope | f_ref | X | Y | R | θ | Files | Notes |
|-----|------|--------------------|--------|----------------|---------------------|-----------------|-------|---|---|---|---|-------|-------|
| | | | | | | | | | | | | | |

#### LAB-3 Power Rails and PD Negotiation

**Purpose.** Verify PD negotiation (12 V contract, no start on 5 V-only source), DC level, ripple and low-frequency noise of each rail.

**Setup.** Scope with 20 MHz limit, ground spring at the output capacitor, AC coupling for ripple; FFT around f₀ (no burst components expected: FPWM, DC-7). Try a 5 V-only USB source: converters must stay off.

| Rail | Expected DC | Measured DC | Expected ripple (pp) | Measured ripple (pp) | Load / input current | Files | Notes |
|------|-------------|-------------|----------------------|----------------------|----------------------|-------|-------|
| VIN (PD contract) | 12 V | | — | | | | |
| +7V | 7.02 V | | 8–11 mV @ 500 kHz | | | | |
| −7V | −7.02 V | | ≈ 5–6 mV @ 500 kHz | | | | |
| +5VA | 5.0 V | | ≪ 1 mV | | | | |
| +5VP | 5.0 V | | ≪ 1 mV | | | | |
| −5VA | −5.0 V | | ≪ 1 mV | | | | |
| +3V3_D | 3.29 V | | ≪ 1 mV | | | | |
| VDDA | 3.300 V ± ref tolerance | | ≪ 100 µV | | | | Also log vs temperature |
| Input current @ 12 V | ≈ 0.15 A | | — | — | | | |

#### LAB-4 Excitation and References

**Purpose.** Verify the MCU-generated excitation and lock-in references (AN-1…AN-7b, FW-1…FW-10). Bench procedure for the firmware side: [firmware_requirements.md §F.8](../../../firmware/firmware_requirements.md#f8-verification-bench-lab-4).

**Setup.** Scope CH1 on the gate net (AC coupled, averaging), CH2 on REF_X, CH3 on REF_Y; frequency from the scope counter; THD from scope FFT or SR860 harmonic measurement at the reconstruction-filter output (larger signal) and at the gate; phase REF_X → REF_Y and gate → REF_X from scope cursors.

| Run | Date | f set / measured (Hz) | Amplitude set / measured at gate (mVpp) | THD at filter output / gate (%) | Image level at ≈ N·f₀ (dBc) | REF_X → REF_Y (°) | Gate → REF_X (°) | Gate DC set / measured (V) | Files | Notes |
|-----|------|-----------------------|------------------------------------------|---------------------------------|-----------------------------|-------------------|------------------|----------------------------|-------|-------|
| Expected | — | 518.0 / ±50 ppm | 5.0 / ±1 % | ≤ 0.3 | ≤ −40 at gate | 90.0 ± 0.1 | fixed, recorded | 0.990 / ±0.5 mV | — | SIM-19 |
| | | | | | | | | | | |

#### LAB-5 Band-Pass Response

**Purpose.** Verify the INA + band-pass chain (measured at the LPF output, U3 pin 7) ([§2.8](../../documents/measurement_principles.md#28-band-pass-filter-design)).

**Setup.** Function generator, 10 mVpp differential (or single-ended into one INA input with the other grounded through 330 kΩ), swept 100 Hz–5 kHz; measure at the LPF output (U3 pin 7) with the SR860 (gain and phase). Repeat with the on-board calibration tone (LAB-10) at a few frequencies and compare.

| Run | Date | Gain at 518 Hz (V/V) | Phase at 518 Hz (°) | f_L −3 dB (Hz) | f_H −3 dB (Hz) | Gain at 1036 Hz rel. | Gain at 50 Hz rel. | Files | Notes |
|-----|------|----------------------|--------------------|----------------|----------------|----------------------|--------------------|-------|-------|
| Expected | — | 10 | 0 ± 1.6 | 377 | 711 | −10 dB | −41 dB | — | |
| | | | | | | | | | |

#### LAB-6 Common-Mode Rejection

**Purpose.** Measure the system CMRR ([§2.7](../../documents/measurement_principles.md#27-common-mode-rejection)).

**Setup.** Option A (bench): drive both drain nodes with the same signal through their 330 kΩ resistors (gate grounded). Option B (board): calibration network in common-mode configuration (LAB-10). Repeat with a differential signal of known amplitude for the reference gain.

| Run | Date | Method | CM input (Vpp) | Output for CM | DM input (Vpp) | Output for DM | CMRR (dB) | Files | Notes |
|-----|------|--------|----------------|---------------|----------------|---------------|-----------|-------|-------|
| Expected | — | | | | | | ≈ 56 (≥ 48) | — | |
| | | | | | | | | | |

#### LAB-7 Drain Bias, Current Readback and r0

**Purpose.** Verify the drain DAC range/resolution (AN-9, AN-10), the drain-current readback (AN-11), and measure r₀ to decide D-8.

**Setup.** For r₀ (bench, now): at fixed V_G and heater, step the drain supply in 10 mV steps over 2.7–3.5 V and record I_D; r₀ ≈ ΔV_DS/ΔI_D. If ΔI_D per 100 µV of supply is ≪ 46 pA, the proposed ≤ 100 µV resolution is sufficient.

| Run | Date | Pixel | DAC / supply setting (V) | Measured V_supply (DMM) | Measured V_D (DMM) | I_D from DMM (µA) | I_D from board (µA) | Error | r₀ (MΩ) | Files | Notes |
|-----|------|-------|--------------------------|-------------------------|--------------------|-------------------|---------------------|-------|---------|-------|-------|
| | | | | | | | | | | | |

#### LAB-8 Heater Drive and Current Readback

**Purpose.** Verify heater voltage range (AN-14) and current readback (AN-18), and measure all six heater resistances (open item 2) **before** finalizing the shunt value.

| Run | Date | Heater | R_heater cold (Ω, DMM) | DAC setting (V) | Measured V_heater (DMM) | I_heater from DMM (mA) | I_heater from board (mA) | Error (µA) | Files | Notes |
|-----|------|--------|------------------------|-----------------|-------------------------|------------------------|--------------------------|------------|-------|-------|
| Spec | — | | 600–1200 (or ≈ 300?) | | 2.5–4.0 | | | ≤ 100 | — | |
| | | | | | | | | | | |

#### LAB-9 Full Chain vs SR860

**Purpose.** Compare the board X/Y with the SR860 on the same sensor and operating point, and confirm the scale factor of [§2.9](../../documents/measurement_principles.md#29-gain-distribution-headroom-and-demodulator-output) (|V_X,ADC| ≈ 38.2·v̂_diff·cos θ, the same for FE-A/B/C, D-18). Record the sign of X for a known Δg_m polarity (§2.13).

| Run | Date | Operating point | SR860 X / Y (Vrms, drain-referred) | Board X / Y (V at ADC) | Board X / Y drain-referred | Ratio | Phase offset (°) | Files | Notes |
|-----|------|-----------------|------------------------------------|------------------------|----------------------------|-------|------------------|-------|-------|
| | | | | | | | | | |

#### LAB-10 On-Board Calibration Loopback

**Purpose.** Verify that mux position 4 with the DAC1_OUT2 tone measures chain gain and phase consistently with LAB-5 (AN-29e).

**Setup.** Select mux position 4; set tone amplitude so the differential input is ≈ 10 mVpp; read X/Y; compute gain and phase vs the known tone; repeat at 450, 518, 600 Hz and in CM configuration.

| Run | Date | f (Hz) | Tone at CAL_P−CAL_N (mVpp, scope) | Board X / Y | Gain (V/V) | Phase (°) | Δ vs LAB-5 | CM leakage (dB) | Files | Notes |
|-----|------|--------|-----------------------------------|-------------|------------|-----------|------------|-----------------|-------|-------|
| | | | | | | | | | | |