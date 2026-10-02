
## 8. Lab Tests
 
Results measured on the bench with lab equipment (oscilloscope, lock-in, supplies, meters) are collected here, next to the design values they verify. Raw data (scope screenshots, CSV exports, SR860 logs) go in `lab/<test-id>/`, named `YYYY-MM-DD_<short-description>.<ext>`; each results row links to its files. Add a row per run; do not overwrite earlier runs.
 
### 8.1 Equipment
 
| Instrument | Model / serial | Used in | Notes |
|------------|----------------|---------|-------|
| Oscilloscope | | LAB-1, LAB-3, LAB-4 | |
| Oscilloscope probes | | LAB-1, LAB-3, LAB-4 | 10× passive (10 MΩ ∥ ≈ 10–15 pF) |
| Lock-in amplifier | SR860 [[M1]](#ref-m1) | LAB-2, LAB-5, LAB-9 | |
| Low-noise preamplifier | SR560 [[M2]](#ref-m2) | LAB-2 | |
| Function generator | | LAB-5, LAB-6 | |
| Bench power supply | | LAB-3 and board supply | Current limit set (no on-board fuse, [§3.5.4](#354-protection-and-sequencing)) |
| DMM / SMU | | LAB-7, LAB-8 | |
 
### 8.2 Test Index
 
| ID | Test | Verifies | Status |
|----|------|----------|--------|
| [LAB-1](#lab-1-drain-node-waveforms-oscilloscope) | Drain node waveforms (oscilloscope) | Drain DC level, AC swing, common-mode level ([§2.4](#24-transistor-operating-point)) | Not started |
| [LAB-2](#lab-2-bench-lock-in-reference-levels-sr560--sr860) | Bench lock-in reference levels | Expected signal level ([§2.5](#25-expected-signal-level-from-bench-data)) | Not started |
| [LAB-3](#lab-3-power-rails) | Power rails | DC levels, ripple ([§3.5](#35-design-calculations)) | Not started |
| [LAB-4](#lab-4-quadrature-oscillator) | Quadrature oscillator | Amplitude, frequency, THD, quadrature ([§4.5](#45-quadrature-oscillator-design)) | Not started |
| [LAB-5](#lab-5-band-pass-response) | Band-pass response | Gain/phase vs frequency ([§2.8](#28-band-pass-filter-design)) | Not started |
| [LAB-6](#lab-6-common-mode-rejection) | Common-mode rejection | System CMRR ([§2.7](#27-common-mode-rejection)) | Not started |
| [LAB-7](#lab-7-drain-bias-and-current-readback) | Drain bias and current readback | AN-10, AN-11 | Not started |
| [LAB-8](#lab-8-heater-drive-and-current-readback) | Heater drive and current readback | AN-14, AN-18 | Not started |
| [LAB-9](#lab-9-full-chain-vs-sr860) | Full chain vs SR860 | Scale factor and phase ([§2.9](#29-gain-distribution-headroom-and-demodulator-output)) | Not started |
 
### 8.3 Tests
 
#### LAB-1 Drain Node Waveforms (Oscilloscope)
 
**Purpose.** Measure the real drain DC level and AC swing of each transistor, and the active − blind difference, to confirm the common-mode level and the stage gain assumed in [§2.4](#24-transistor-operating-point). This can be done today on the existing bench setup.
 
**Setup.** Existing 3T bench setup (SR860 reference out on the gate, 330 kΩ drain resistors, heaters on the lab supply). CH1 on drain A, CH2 on drain B, both 10× probes, DC coupling for the DC level and AC coupling for the swing; math channel CH1 − CH2 for the differential. Use averaging (≥ 16) and a 20 MHz bandwidth limit. A 10× probe loads the drain with ≈ 10 MΩ ∥ ≈ 12 pF, which lowers the 518 Hz swing by ≈ 3 % (330 kΩ ∥ 10 MΩ); note it in the results.
 
**Expected.** Drain DC 50–250 mV; per-drain swing ≤ ≈ 200–400 mVpp for 5 mVpp excitation at room temperature (upper bound, r_0 ≫ R_D), scaling with the excitation amplitude; differential much smaller than either drain.
 
| Run | Date | V_G DC | δV_GS (setting) | V_heater A / B | I_D A / B | V_D DC A / B | v_d A / B (mVpp) | v_A − v_B (mVpp) | Phase A vs B | Files | Notes |
|-----|------|--------|-----------------|----------------|-----------|--------------|------------------|------------------|--------------|-------|-------|
| | | | | | | | | | | | |
 
<!-- ![Drain A, drain B and A−B on the scope](lab/LAB-1/drain_waveforms.png) -->
 
#### LAB-2 Bench Lock-in Reference Levels (SR560 / SR860)
 
**Purpose.** Record the maximum X/Y/R on the existing bench chain at the planned operating points, to confirm the signal-level assumption of [§2.5](#25-expected-signal-level-from-bench-data) and the gain plan of [§2.9](#29-gain-distribution-headroom-and-demodulator-output).
 
**Expected.** X/Y ≤ ≈ 400 mVrms with SR560 gain 20 and 5 mVrms excitation, i.e. ≤ 20 mVrms differential at the drains.
 
| Run | Date | Excitation (SR860, Vrms) | V_G DC | V_heater A / B | SR560 gain / filter | SR860 τ / slope | X | Y | R | θ | Files | Notes |
|-----|------|--------------------------|--------|----------------|---------------------|-----------------|---|---|---|---|-------|-------|
| | | | | | | | | | | | | |
 
#### LAB-3 Power Rails
 
**Purpose.** Verify the DC level, ripple and low-frequency noise of each rail ([§3.5](#35-design-calculations), [§6](#6-power-budget)).
 
**Setup.** Scope, 20 MHz bandwidth limit, probe ground spring at the output capacitor; AC coupling for ripple. Input current from the bench supply display. Check the spectrum around 518 Hz with the scope FFT (no PFM bursts expected: FPWM, DC-7).
 
| Rail | Expected DC | Measured DC | Expected ripple (pp) | Measured ripple (pp) | Load / input current | Files | Notes |
|------|-------------|-------------|----------------------|----------------------|----------------------|-------|-------|
| V_positive (+7 V) | 7.02 V | | 8–11 mV @ 500 kHz | | | | |
| V_negative (−7 V) | −7.02 V | | ≈ 5–6 mV @ 500 kHz | | | | |
| 5V_analog | 5.00 V | | ≪ 1 mV | | | | |
| N5V_analog | −4.99 V | | ≪ 1 mV | | | | |
| 3V3_digital | 3.30 V | | ≪ 1 mV | | | | |
| VIN current @ 12 V | ≈ 0.17–0.19 A (worst case) | | — | — | | | |
 
#### LAB-4 Quadrature Oscillator
 
**Purpose.** Verify amplitude, frequency, distortion and quadrature of the oscillator ([§4.5](#45-quadrature-oscillator-design)).
 
**Setup.** CH1 on sin, CH2 on cos (10× probes); frequency from the scope counter (and the MCU capture, AN-7a); THD from the scope FFT or the SR860 harmonic measurement; quadrature from the X–Y (Lissajous) display or the scope phase measurement.
 
| Run | Date | Amplitude sin / cos (Vpp) | Frequency (Hz) | Frequency from MCU (Hz) | THD sin / cos (%) | Phase sin → cos (°) | Reference after divider (Vpp) | Start-up time (s) | Files | Notes |
|-----|------|---------------------------|----------------|-------------------------|-------------------|---------------------|-------------------------------|-------------------|-------|-------|
| Expected | — | 6.3 / 6.3 | 518–521 (±1 %) | same | ≤ 1 | 90 ± 1 | 2.0 | ≈ 0.4 | — | Simulation, [§4.5.7](#457-simulated-performance-ideal-op-amps-ngspice) |
| | | | | | | | | | | |
 
#### LAB-5 Band-Pass Response
 
**Purpose.** Verify the INA + band-pass + ×4 gain chain against the design ([§2.8](#28-band-pass-filter-design)).
 
**Setup.** Function generator, 10 mVpp differential (or single-ended into one INA input with the other grounded through 330 kΩ), swept 100 Hz–5 kHz; measure at the ×4 output with the SR860 (gain and phase) or the scope.
 
| Run | Date | Gain at 518 Hz (V/V) | Phase at 518 Hz (°) | f_L −3 dB (Hz) | f_H −3 dB (Hz) | Gain at 1036 Hz rel. | Gain at 50 Hz rel. | Files | Notes |
|-----|------|----------------------|---------------------|----------------|----------------|----------------------|--------------------|-------|-------|
| Expected | — | 40 | 0 ± 1.6 | 377 | 711 | −10 dB | −41 dB | — | |
| | | | | | | | | | |
 
#### LAB-6 Common-Mode Rejection
 
**Purpose.** Measure the system CMRR ([§2.7](#27-common-mode-rejection)).
 
**Setup.** Drive both drain nodes with the same 518 Hz signal through their 330 kΩ resistors (transistors removed or gates grounded), measure the AD630 input or X/Y; repeat with a differential signal of known amplitude for the reference gain.
 
| Run | Date | CM input (Vpp) | Output for CM | DM input (Vpp) | Output for DM | CMRR (dB) | Files | Notes |
|-----|------|----------------|---------------|----------------|---------------|-----------|-------|-------|
| Expected | — | | | | | ≈ 56 (≥ 48) | — | |
| | | | | | | | | |
 
#### LAB-7 Drain Bias and Current Readback
 
**Purpose.** Verify drain DAC setting resolution (AN-10) and the drain current readback (AN-11) against a DMM/SMU.
 
| Run | Date | Channel | DAC setting (V) | Measured V_supply (DMM) | Measured V_D (DMM) | I_D from DMM (µA) | I_D from board (µA) | Error | Files | Notes |
|-----|------|---------|-----------------|-------------------------|--------------------|-------------------|---------------------|-------|-------|-------|
| | | | | | | | | | | |
 
#### LAB-8 Heater Drive and Current Readback
 
**Purpose.** Verify heater voltage range (AN-14) and current readback accuracy (AN-18).
 
| Run | Date | Heater | DAC setting (V) | Measured V_heater (DMM) | I_heater from DMM (mA) | I_heater from board (mA) | Error (µA) | Files | Notes |
|-----|------|--------|-----------------|-------------------------|------------------------|--------------------------|------------|-------|-------|
| | | | | | | | ≤ 100 (spec) | | |
 
#### LAB-9 Full Chain vs SR860
 
**Purpose.** Compare the board X/Y with the SR860 on the same sensor and operating point, and confirm the scale factor of [§2.9](#29-gain-distribution-headroom-and-demodulator-output) (V_X,ADC ≈ 76.4·v̂_diff·cos θ).
 
| Run | Date | Operating point | SR860 X / Y (Vrms, drain-referred) | Board X / Y (V at ADC) | Board X / Y drain-referred | Ratio | Phase offset (°) | Files | Notes |
|-----|------|-----------------|------------------------------------|------------------------|----------------------------|-------|------------------|-------|-------|
| | | | | | | | | | |
