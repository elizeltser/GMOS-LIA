# GMOS LIA Board — Measurement Principles

Theory and design considerations behind the readout. Requirement IDs are defined in [requirements.md](requirements.md); implemented circuits are in [schematic_overview.md](schematic_overview.md).

## 2. Measurement Principle & Design Considerations

### 2.1 Device and Sensing Mechanism

The GMOS is a micromachined CMOS-SOI pixel containing a transistor (29 nMOS devices in parallel, W = 204 µm, L = 4.15 µm) and an integrated heating resistor. The package used here provides six pixels: three **active** pixels (1–3, exposed, with catalytic layer) and three **blind** pixels (4–6, inert reference). One active and one blind pixel are measured at a time as a differential pair (AN-27); the other four are disconnected (drain and heater open). All gates share one gate net; drains and heaters are individual at the socket.

Gas combustion on the catalytic layer releases heat and raises the active pixel temperature by ΔT. This shifts the threshold voltage and subthreshold drain current of the active transistor relative to the blind one, and the difference appears as a differential signal between the two drain nodes. Because the blind pixel sees the same heater drive, ambient and supply conditions, common-mode drifts are rejected by the differential readout.

### 2.2 3T Readout Method

Each transistor is operated in a three-terminal configuration:

- **Gate:** DC bias plus a small sine excitation at the lock-in reference frequency.
- **Drain:** connected through a series load resistor R_D (330 kΩ) to a programmable supply.
- **Heater:** DC voltage, trimmed per pixel to equalize the drain currents of the active/blind pair.

The gate modulation δV_GS produces a drain-current modulation g_m·δV_GS, which R_D converts to a voltage. The lock-in output is therefore proportional to the differential transconductance:

$$
\Delta v_{d} = -(g_{m,A} - g_{m,B})\cdot \delta V_{GS}\cdot R_D
$$

The minus sign reflects the inverting common-source stage. The phase θ carries information on reactive elements in the signal path and is used for calibration ([§2.13](#213-calibration)).

### 2.3 Bench Setup → Board Block Mapping

| Bench instrument / setting | Board block | Notes |
|----------------------------|-------------|-------|
| SR860 reference out, 990 mV offset | DAC80508 channel → summing amp (unity DC gain) | AN-5, 0.97–1.2 V |
| SR860 reference out, 5 mV (assumed rms ≈ 14.1 mVpp, README §9.2 item 3) | MCU DAC1_OUT1 sine → reconstruction LPF → ÷120 in the summing amp | AN-1…AN-4, programmable 0.5–20 mVpp, default 5 mVpp |
| Lab supply on drain resistors | One DAC80508 channel + R_D per side; mux selects the pixel | AN-8…AN-12 |
| Lab supply on heaters (2.7–2.9 V) | One DAC80508 channel + op-amp driver + INA190 per side, switched to the selected pixel | AN-13…AN-18 |
| SR560: differential input, gain 20 V/V, BPF 300 Hz–1 kHz (6 dB/oct) | INA828 (G = 10, DC-coupled) → SK HPF → SK LPF → ×4 | 40 V/V, 377–711 Hz, 12 dB/oct |
| SR860 demodulator (X, Y, R, θ) | AD630 pair with MCU square-wave references → LPF τ = 500 ms, ×3 → ADS1220; R, θ in MCU/PC | AN-24…AN-26 |
| (none) | Mux position 4 + MCU DAC1_OUT2 test tone | On-board calibration, AN-29e |

As on the bench (SR560 differential input, then filters), the differential conversion happens first and the filtering is done once on the difference signal.

### 2.4 Transistor Operating Point

The GMOS must operate in subthreshold (weak inversion), where the temperature coefficient of the current is maximal. Two conditions must hold simultaneously:

$$
V_{GS} < V_T \approx 1.33\ \mathrm{V}, \qquad V_{DS} > \frac{3 k_B T}{q}
$$

The second condition must be evaluated at the **pixel** temperature:

| Pixel temperature | 3·k_B·T/q |
|-------------------|-----------|
| 300 K | 77.6 mV |
| 400 K | 103.4 mV |
| 573 K (300 °C) | 148.1 mV |
| 673 K (400 °C) | 174.0 mV |

The quiescent drain voltage (source grounded) is

$$
V_{DS} = V_{\mathrm{supply}} - I_{DS}\,R_D
$$

With I_DS = 5–10 µA and R_D = 330 kΩ the drain node sits at 50–250 mV. The 50 mV lower bound is kept so the transistors can be characterized with the heaters off (pixel at room temperature). At elevated pixel temperature the firmware keeps V_DS above the value in the table. Note that once V_DS > 3k_BT/q, I_DS depends on V_GS and T and only weakly (through r₀) on V_DS; V_supply therefore sets V_D rather than I_D (basis of proposal D-8, AN-10).

**AC drain swing.** The 3T stage is a common-source amplifier. Assuming r₀ ≫ R_D, with g_m = I_DS/(n·k_B·T/q):

$$
v_{d,pp} \approx g_m R_D\cdot \delta V_{GS,pp} = \frac{I_{DS} R_D}{n\cdot k_B T/q}\cdot \delta V_{GS,pp}
$$

| Pixel temperature | I_DS·R_D = 1.65 V (5 µA) | I_DS·R_D = 3.3 V (10 µA) |
|-------------------|--------------------------|--------------------------|
| 300 K | gain ≈ 40 → ≈ 200 mVpp | gain ≈ 80 → ≈ 400 mVpp |
| 673 K | gain ≈ 18 → ≈ 90 mVpp | gain ≈ 36 → ≈ 180 mVpp |

> n = 1.6, δV_GS = 5 mVpp.

This is an upper bound; a finite r₀ lowers it, and the bench data ([§2.5](#25-expected-signal-level-from-bench-data)) suggest the real stage gain is lower. For clean small-signal operation the swing must also respect the V_DS limit:

$$
V_{DS,\mathrm{DC}} - \frac{v_{d,pp}}{2} > \frac{3 k_B T}{q}
$$

The drains carry this signal as **common mode** (both transistors share the gate excitation), which the readout must reject ([§2.7](#27-common-mode-rejection)). The gate excitation must remain a small signal relative to n·k_B·T/q ≈ 41 mV (300 K) to 93 mV (673 K); the programmable range of AN-4 (≤ 20 mVpp) satisfies this, but the upper end should be checked for harmonic content (LAB-1).

### 2.5 Expected Signal Level (from Bench Data)

The SR860 reports X, Y and R as rms values of the input component at the reference frequency. Bench measurements gave at most 400 mV on X/Y with the SR560 at 20 V/V and a 5 mVrms excitation, so:

| Quantity | Bench (5 mVrms ≈ 14.1 mVpp excitation) | Board default (5 mVpp excitation) |
|----------|-----------------------------------------|-----------------------------------|
| Differential drain signal, rms | 400 mV / 20 = 20 mVrms | 7.1 mVrms |
| Differential drain signal, peak | 28.3 mV | 10.0 mV |
| Differential drain signal, peak-to-peak | 56.6 mVpp | 20.0 mVpp |

The board value scales with the excitation ratio (5 mVpp / 14.1 mVpp = 0.354); with programmable excitation (AN-4) the drain signal scales linearly with the setting. The bench figure is consistent with the device physics: it corresponds to a Δg_m/g_m of the order of 10–20 % of the drain swing, and the ideal r₀ ≫ R_D swing at bench excitation (0.6–1.1 Vpp) could not fit inside a 50–250 mV drain DC level, which indicates a lower real stage gain. The chain gain ([§2.9](#29-gain-distribution-headroom-and-demodulator-output)) is set from the **board default** column with 2× headroom.

- [ ] TODO: confirm on the bench: drain AC swing per drain and maximum X/Y at the planned operating points (LAB-1, LAB-2).

### 2.6 Front End: Differential Conversion First

The two drain nodes of the selected pair (R_D on the board side, pixel connected through the multiplexer) go directly to a DC-coupled instrumentation amplifier (INA828, G = 10), followed by a single band-pass (Sallen-Key HPF + Sallen-Key LPF) and a ×4 gain stage.

**Drain loading.** The transistor behaves as an AC current source g_m·δV_GS feeding the drain node, and everything attached to the node is in parallel for that current:

$$
v_d = g_m\cdot \delta V_{GS}\cdot \left(R_D \parallel r_0 \parallel Z_{\mathrm{in}}\right)
$$

A Sallen-Key filter connected directly to the drain would present Z_in of a few kΩ to tens of kΩ and attenuate the signal by tens of times. The INA828 inputs are high-impedance (GΩ-level resistance, pA–nA bias current, a few pF; verify against the datasheet), so Z_in ≫ R_D without dedicated buffers. What remains is the drain-node capacitance (INA input + mux + traces), which forms a pole with R_D. The analysis below assumed ≈ 20 pF; with the TMUX1109 (≈ 38 pF on-capacitance) the node is closer to 50–60 pF, giving f_p ≈ 8–10 kHz and a larger capacitive CM→DM term (README §9.2 item 10):

$$
f_p = \frac{1}{2\pi R_D C_{\mathrm{node}}} \approx 24\ \mathrm{kHz}
$$

far above f₀; only its mismatch between the two drains matters ([§2.7](#27-common-mode-rejection)). The INA input bias current flows through R_D and shifts each drain DC level by I_B·R_D (≤ ≈ 0.3 mV for 1 nA), which is calibrated by the drain-voltage measurement.

**DC headroom.** The INA is DC-coupled, so it amplifies the DC mismatch between the drains: ±200 mV → ±2 V at the INA output, inside its swing on ±5 V. The HPF removes it before the ×4 stage. Requirement AN-12b (≤ ±200 mV) is met by firmware using the active and blind drain-supply DACs (V_D can be trimmed directly).

**1/f noise and reference frequency.** The transistor 1/f corner is ≈ 200 Hz at typical I_DS, below the band-pass −3 dB edge (377 Hz). 518 Hz lies between the 10th (500 Hz) and 11th (550 Hz) harmonics of 50 Hz mains and well above the pixel thermal bandwidth (≈ 16 Hz). With programmable frequency (AN-1), the reference can be moved within the pass band to avoid interference lines found on the bench.

**DC leakage on the drain nodes.** Any DC current drawn from the node produces an offset (1 nA → 330 µV). Use guard rings and keep-outs around the drain traces and the low-leakage mux (AN-29c).

**Load resistor quality.** R_D sets both the signal gain and the CMRR. Use 0.1 %, ≤ 25 ppm/°C thin-film resistors placed together so the active and blind resistors track thermally.

### 2.7 Common-Mode Rejection

With the INA first, CM-to-DM conversion comes from mismatch between the two drain nodes (R_D and node capacitance), not from the filters. Monte-Carlo, 50 000 trials (Python; 60-run SPICE cross-check, [§7](preliminary_lab_test_results.md#7-simulation)):

| R_D tolerance | C_node (20 pF) mismatch | INA CMRR | System CMRR median | 99 % worst |
|---------------|-------------------------|----------|--------------------|------------|
| 0.05 % | ±5 % | 90 dB | 62 dB | 54 dB |
| **0.1 %** | **±10 %** | **90 dB** | **56 dB** | **48 dB** |
| 0.1 % | ±20 % | 90 dB | 52 dB | 42 dB |
| 1 % | ±10 % | 90 dB | 44 dB | 35 dB |
| 0.1 % | ±10 % | 80 dB | 56 dB | 48 dB |

A realistic system CMRR is therefore ≈ 50–60 dB, limited by R_D matching and by keeping the two drain-node layouts symmetric (equal trace lengths, same mux type on both sides). At 56 dB, a 300 mVpp common-mode drain swing leaks as ≈ 0.5 mVpp apparent differential signal, ≈ 2.5 % of the expected 20 mVpp board signal; the capacitive part appears mostly in quadrature (Y). Using two identical TMUX1109 devices (one per side, same position) keeps the mux capacitance matched; with only two R_D, a matched resistor pair can be used.

### 2.8 Band-Pass Filter Design

The band-pass is a 2nd-order unity-gain Sallen-Key high-pass followed by a 2nd-order unity-gain Sallen-Key low-pass, both tuned to f₀ = 518 Hz with Q = 1. At f₀ the high-pass contributes +90° and the low-pass −90°, so the filter has **unity gain and 0° phase at f₀**, with 40 dB/decade slopes on each side.

$$
H(s) = \frac{(s/\omega_0)^2}{(s/\omega_0)^2 + \frac{s}{Q\omega_0} + 1}\cdot\frac{1}{(s/\omega_0)^2 + \frac{s}{Q\omega_0} + 1}, \qquad \omega_0 = 2\pi\cdot 518\ \mathrm{Hz}
$$

Trade-off between section Q, bandwidth and sensitivity to excitation-frequency changes:

| Section Q | Gain at f₀ | −3 dB band | Rel. attenuation 50 Hz / 150 Hz / 2f₀ / 3f₀ | Phase change over ±1 % frequency |
|-----------|-------------|------------|----------------------------------------------|----------------------------------|
| 0.707 (HP 400 Hz, LP 670 Hz) | 0.74 | 318–843 Hz | −34 / −15 / −6 / −12 dB | 2.9° |
| **1 (selected)** | **1.00** | **377–711 Hz** | **−41 / −21 / −10 / −18 dB** | **4.6°** |
| 1.5 | 2.25 | 419–641 Hz | −48 / −27 / −16 / −25 dB | 6.9° |
| 2 | 4.0 | 441–608 Hz | −53 / −32 / −20 / −29 dB | 9.2° |

With the excitation now clock-derived (±50 ppm), frequency drift no longer moves θ. When the frequency is changed on purpose, gain and phase of the filter change along the curve above and must be taken from the on-board calibration ([§2.13](#213-calibration)).

Component relations for unity-gain Sallen-Key sections (ratio 4Q² = 4 for Q = 1):

| Section | Components | Relations | Values |
|---------|------------|-----------|--------|
| HPF | C1 = C2 = C (series), R_f (cap junction → output), R_g (+input → ground) | Q = ½·√(R_g/R_f), R_f = 1/(2·Q·ω₀·C), R_g = 4Q²·R_f | C = 33 nF, R_f = 4.64 kΩ, R_g = 18.56 kΩ (4 × 4.64 kΩ in series) |
| LPF | R1 = R2 = R (series), C1 (junction → output), C2 (+input → ground) | Q = ½·√(C1/C2), C2 = 1/(2·Q·ω₀·R), C1 = 4Q²·C2 | R = 4.64 kΩ, C2 = 33 nF, C1 = 132 nF (4 × 33 nF in parallel) |

Building the 4:1 ratios from identical parts keeps the ratio tracking over temperature and tolerance. Use C0G/NP0 1 % capacitors and 0.1 % thin-film resistors. Tolerance spread at f₀ (Monte-Carlo):

| Components | Gain σ | Gain 99 % range | Phase σ | Phase 99 % range |
|------------|--------|-----------------|---------|------------------|
| R 0.1 %, C 1 % (C0G) | 0.06 dB | ±0.14 dB | 0.66° | ±1.6° |
| R 1 %, C 5 % | 0.31 dB | ±0.72 dB | 3.4° | ±8.2° |

### 2.9 Gain Distribution, Headroom and Demodulator Output

The AD630 runs on the ±5 V analog rails, its minimum supply. At ±5 V its datasheet ranges are [[D4]](README.md#ref-d4):

- **Signal inputs:** (−V_S + 4) to (+V_S − 1) = **−1 V to +4 V**. Usable symmetric swing ±1 V; design limit ±0.8 V pk.
- **Comparator inputs:** (−V_S + 3) to (+V_S − 1.5) = **−2 V to +3.5 V**. The MCU references (0/3.3 V, driven differentially) are inside this range (AN-6).

Gain distribution at the default 5 mVpp excitation:

| Stage | Gain | Expected max (board default, [§2.5](#25-expected-signal-level-from-bench-data)) | Linear limit |
|-------|------|-----------------------------|--------------|
| Drain differential | — | 10 mV pk | 20 mV pk |
| INA828 (G = 10) | 10 | 0.1 V pk (+ DC mismatch × 10) | |
| SK HPF + SK LPF | 1 at f₀ | 0.1 V pk | |
| Non-inverting gain stage | 4 | 0.4 V pk | 0.8 V pk |
| AD630 (gain ±1, full-wave) | 1 | DC: 0.25 V | DC: 0.51 V |
| Post-LPF (inverting, ×3) around VMID | −3 | ∓0.76 V around VMID | ∓1.53 V around VMID |
| ADS1220 (±2.048 V FS, differential vs VMID) | — | 37 % FS | 75 % FS |

The expected maximum sits at half the AD630 linear range, leaving 2× headroom. Because the drain signal scales with the excitation, the usable excitation at the expected Δg_m is ≈ 10 mVpp; above that the ×4 stage should be reduced (README §9.2 item 5). Firmware should flag AD630 overload from the X/Y magnitude.

The AD630 with a square-wave reference produces a DC output; the chain scale factor at the ADC input is

$$
V_X = \frac{2}{\pi}\,G\,\hat{v}_{\mathrm{diff}}\cos\theta, \qquad V_Y = \frac{2}{\pi}\,G\,\hat{v}_{\mathrm{diff}}\sin\theta, \qquad |V_{X,\mathrm{ADC}}| = 3\cdot\frac{2}{\pi}\cdot 40\cdot\hat{v}_{\mathrm{diff}}\cos\theta \approx 76.4\,\hat{v}_{\mathrm{diff}}\cos\theta
$$

(G = 40 up to the AD630 input; the post stage is inverting, so the sign is flipped in firmware.) To compare with SR860 readings (rms), use v̂_diff = √2·v_rms.

### 2.10 Demodulator Low-Pass Filter and Oversampling

The post-AD630 filter is first order with τ = 500 ms (f_c = 0.318 Hz, equivalent noise bandwidth 1/(4τ) = 0.5 Hz). It attenuates the 2f₀ ripple of the demodulator output by ≈ 70 dB, and the ADS1220 digital filter adds further rejection.

Oversampling can only **lengthen** the effective time constant (narrow the bandwidth, lower noise) by digital averaging. It cannot make the response faster than the analog τ, because content above 0.318 Hz is already removed before the ADC. The analog τ is therefore fixed at 500 ms (the shortest response needed); longer time constants are implemented in software. The ADS1220 provides 20–1000 SPS, so even with X and Y multiplexed there are ≥ 10 samples per τ.

Settling after a step (channel switch, operating-point change): 3.5 s to 0.1 % (6.9τ), 6.9 s to 1 ppm (13.8τ).

### 2.11 Noise and SNR

The SNR is fixed at the drain node, before any amplifier, so the supply rails and later gain stages cannot change it. A transistor in subthreshold carries full shot noise on its drain current, which is far larger than the thermal noise of R_D:

$$
e_{n,R_D} = \sqrt{4 k_B T R_D} \approx 74\ \mathrm{nV/\sqrt{Hz}}
$$

$$
\frac{S_{i,\mathrm{MOS}}}{S_{i,R_D}} = \frac{2 q I_D}{4 k_B T / R_D} = \frac{I_D R_D}{2 k_B T / q} \approx \frac{7.5\,\mu\mathrm{A}\cdot 330\,\mathrm{k\Omega}}{51.7\,\mathrm{mV}} \approx 48
$$

Each drain therefore carries ≈ 510 nV/√Hz (r₀ ≫ R_D), ≈ 730 nV/√Hz differential, and the transistors dominate. The INA828 (≈ 11 nV/√Hz input-referred at G = 10) and everything after it are negligible. A finite r₀ lowers signal and noise in the same proportion. Since signal and noise both scale with the node impedance, the white-noise SNR depends only on the excitation, the drain current and the bandwidth:

$$
\mathrm{SNR} = \frac{g_m\,\delta V_{GS}}{\sqrt{2 q I_D B}} = \frac{\delta V_{GS}}{n\,k_B T/q}\sqrt{\frac{I_D}{2 q B}}
$$

R_D drops out, and so do the rails and every gain stage after the drain. With a 5 % Δg_m mismatch, two uncorrelated transistors and B = 0.5 Hz, this gives ≈ 80 dB from white noise alone; 1/f noise and drift reduce it.

The parameters that actually improve SNR are: a larger δV_GS (up to the onset of nonlinearity, now programmable), a larger I_D (SNR ∝ √I_D while in subthreshold), longer averaging (software τ), and device-level effects (reference frequency vs 1/f corner, active/blind matching, thermal stability).

### 2.12 Excitation Requirements

The excitation is generated digitally (D-3). Its relevant properties for the measurement are:

- **Frequency.** Clock-derived, so drift (±50 ppm) is irrelevant to θ. Resolution is set by the timer: f₀ = f_TIM/(N·ARR); with f_TIM = 160 MHz and N = 128 samples/period, ARR ≈ 2413 at 518 Hz, i.e. ≈ 0.2 Hz steps.
- **Amplitude.** Proportional to VDDA (the DAC reference on the LQFP64 package) and to the attenuator ratio; both are specified for ≤ 100 ppm/°C (AN-7). X/Y scale directly with the amplitude, so its stability is part of the measurement accuracy.
- **Distortion.** Harmonics on the gate produce drain signals at 2f₀ and 3f₀. They are suppressed by the band-pass (−10 dB at 2f₀, −18 dB at 3f₀), by the square-wave demodulator (even harmonics rejected, 3rd weighted 1/3) and by the small-signal operating point. With THD ≤ 0.3 % the error on X/Y is ≈ 0.003 · 0.13 · 0.33 ≈ 10⁻⁴.
- **Images.** A DAC update rate of N·f₀ ≈ 66 kS/s (N = 128) puts the first image at ≈ 65.8 kHz, attenuated by the reconstruction filter, the gate attenuator and finally the band-pass.
- **Phase.** The reconstruction filter and AC coupling add a fixed phase lag (a few degrees at f₀); it is removed with the rest of the chain phase by calibration.

### 2.13 Calibration

- **Chain gain and phase.** Mux position 4 (AN-29e) injects a known differential tone from MCU DAC1_OUT2 at the excitation frequency. Measuring it gives the chain gain and phase (filters, INA, AD630, post-filter) at the current frequency; θ is corrected numerically (rotate X/Y), so the reference phase itself does not need fine adjustment.
- **Common-mode leakage.** The same input can be configured to drive both sides with the tone (common mode) to measure the CM-to-DM leakage on-board (LAB-6). It scales with g_m and can be subtracted.
- **Sign convention.** Following the inverting common-source stage and the inverting post-filter: document the final sign of X for g_m,A > g_m,B after the first board measurement (LAB-9).
- **Bias.** Drain current is computed from the measured drain voltage and the DAC setting: I_D = (V_supply − V_D)/R_D. Measure each R_D in circuit once and store it.
