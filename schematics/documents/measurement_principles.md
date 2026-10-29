# GMOS-LIA — Measurement Principles

Theory and design considerations behind the readout. Requirement IDs are defined in [requirements.md](../LIA-Readout/docs/requirements.md); implemented circuits are in [schematic_overview.md](../LIA-Readout/docs/schematic_overview.md); simulations in [simulation-plan.md](../../simulations/simulation-plan.md); firmware implementation of the excitation in [firmware_requirements.md](../../firmware/firmware_requirements.md).

Every equation is followed by its LaTeX source.

## 2. Measurement Principle & Design Considerations

### 2.1 Device and Sensing Mechanism

The GMOS is a micromachined CMOS-SOI pixel containing a transistor (29 nMOS devices in parallel, W = 204 µm, L = 4.15 µm) and an integrated heating resistor. The package used here provides six pixels: three **active** pixels (1–3, exposed, with catalytic layer) and three **blind** pixels (4–6, inert reference). One active and one blind pixel are measured at a time as a differential pair (AN-27); the other four are disconnected (drain and heater open). The gates are wired in two groups, `GATE_A` (pixels 1–3) and `GATE_B` (pixels 4–6), each with its own DC level and the same AC excitation (AN-3).

Gas combustion on the catalytic layer releases heat and raises the active pixel temperature by ΔT. This shifts the threshold voltage and subthreshold drain current of the active transistor relative to the blind one, and the difference appears as a differential signal between the two drain nodes. Because the blind pixel sees the same heater drive, ambient and supply conditions, common-mode drifts are rejected by the differential readout.

### 2.2 3T Readout Method

Each transistor is operated in a three-terminal configuration:

- **Gate:** DC bias plus a small sine excitation at the lock-in reference frequency.
- **Drain:** connected through a series load resistor R_D (330 kΩ) to a programmable supply.
- **Heater:** DC voltage, trimmed per side to equalize the drain currents of the active/blind pair.

The gate modulation δV_GS produces a drain-current modulation g_m·δV_GS, which R_D converts to a voltage. The lock-in output is therefore proportional to the differential transconductance:

$$
\Delta v_{d} = -(g_{m,A} - g_{m,B})\cdot \delta V_{GS}\cdot R_D
$$

```latex
\Delta v_{d} = -(g_{m,A} - g_{m,B})\cdot \delta V_{GS}\cdot R_D
```

The minus sign reflects the inverting common-source stage. The phase θ carries information on reactive elements in the signal path and is used for calibration ([§2.13](#213-calibration)).

### 2.3 Bench Setup → Board Block Mapping

| Bench instrument / setting | Board block | Notes |
|----------------------------|-------------|-------|
| SR860 reference out, 990 mV offset | DAC80508 ch4/ch5 → MFB summing stage per gate group (DC gain ≈ 1.008) | AN-5, 0.97–1.2 V |
| SR860 reference out, 5 mV (assumed rms ≈ 14.1 mVpp, README §9.2 item 3) | MCU DAC1_OUT1 sine (timer-triggered DMA table) → two MFB low-pass stages (gain −1/120) | AN-1…AN-4, programmable 0.5–20 mVpp, default 5 mVpp; [§2.12](#212-excitation-and-reference-generation) |
| Lab supply on drain resistors | One DAC80508 coarse/fine pair per side → difference amplifier → R_D (one per side) → TMUX1109 bank A → selected drain | AN-8…AN-12, [§2.14](#214-drain-bias-with-coarse-and-fine-dacs) |
| Lab supply on heaters (2.7–2.9 V) | One DAC80508 channel + op-amp driver + INA190 per side, switched to the selected pixel | AN-13…AN-18 |
| SR560: differential input, gain 20 V/V, BPF 300 Hz–1 kHz (6 dB/oct) | In-amp (G = 10, DC-coupled) → SK HPF → SK LPF (gain 1 or 4 at f₀, per front-end option) | 377–711 Hz, 12 dB/oct |
| SR860 demodulator (X, Y, R, θ) | Synchronous demodulator (AD630 or switch-based, decision D-18) with MCU square-wave references → LPF τ = 500 ms → ADS1220; R, θ in MCU/PC | AN-24…AN-26 |
| (none) | Mux position 4: precision dummy load (and optional test tone) | On-board calibration, AN-29e |

As on the bench (SR560 differential input, then filters), the differential conversion happens first and the filtering is done once on the difference signal.

### 2.4 Transistor Operating Point

The GMOS must operate in subthreshold (weak inversion), where the temperature coefficient of the current is maximal. Two conditions must hold simultaneously:

$$
V_{GS} < V_T \approx 1.33\ \mathrm{V}, \qquad V_{DS} > \frac{3 k_B T}{q}
$$

```latex
V_{GS} < V_T \approx 1.33\ \mathrm{V}, \qquad V_{DS} > \frac{3 k_B T}{q}
```

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

```latex
V_{DS} = V_{\mathrm{supply}} - I_{DS}\,R_D
```

With I_DS = 5–10 µA and R_D = 330 kΩ the drain node sits at 50–250 mV. The 50 mV lower bound is kept so the transistors can be characterized with the heaters off (pixel at room temperature). At elevated pixel temperature the firmware keeps V_DS above the value in the table. Once V_DS > 3k_BT/q, I_DS depends on V_GS and T and only weakly (through r₀) on V_DS; V_supply therefore sets V_D rather than I_D ([§2.14](#214-drain-bias-with-coarse-and-fine-dacs)).

**AC drain swing.** The 3T stage is a common-source amplifier. Assuming r₀ ≫ R_D, with g_m = I_DS/(n·k_B·T/q):

$$
v_{d,pp} \approx g_m R_D\cdot \delta V_{GS,pp} = \frac{I_{DS} R_D}{n\cdot k_B T/q}\cdot \delta V_{GS,pp}
$$

```latex
v_{d,pp} \approx g_m R_D\cdot \delta V_{GS,pp} = \frac{I_{DS} R_D}{n\cdot k_B T/q}\cdot \delta V_{GS,pp}
```

| Pixel temperature | I_DS·R_D = 1.65 V (5 µA) | I_DS·R_D = 3.3 V (10 µA) |
|-------------------|--------------------------|--------------------------|
| 300 K | gain ≈ 40 → ≈ 200 mVpp | gain ≈ 80 → ≈ 400 mVpp |
| 673 K | gain ≈ 18 → ≈ 90 mVpp | gain ≈ 36 → ≈ 180 mVpp |

> n = 1.6, δV_GS = 5 mVpp.

This is an upper bound; a finite r₀ lowers it, and the bench data ([§2.5](#25-expected-signal-level-from-bench-data)) suggest the real stage gain is lower. For clean small-signal operation the swing must also respect the V_DS limit:

$$
V_{DS,\mathrm{DC}} - \frac{v_{d,pp}}{2} > \frac{3 k_B T}{q}
$$

```latex
V_{DS,\mathrm{DC}} - \frac{v_{d,pp}}{2} > \frac{3 k_B T}{q}
```

The drains carry this signal as **common mode** (both transistors share the gate excitation), which the readout must reject ([§2.7](#27-common-mode-rejection)). The gate excitation must remain a small signal relative to n·k_B·T/q ≈ 41 mV (300 K) to 93 mV (673 K); the programmable range of AN-4 (≤ 20 mVpp) satisfies this, but the upper end should be checked for harmonic content (LAB-1).

### 2.5 Expected Signal Level (from Bench Data)

The SR860 reports X, Y and R as rms values of the input component at the reference frequency. Bench measurements gave at most 400 mV on X/Y with the SR560 at 20 V/V and a 5 mVrms excitation, so:

| Quantity | Bench (5 mVrms ≈ 14.1 mVpp excitation) | Board default (5 mVpp excitation) |
|----------|-----------------------------------------|-----------------------------------|
| Differential drain signal, rms | 400 mV / 20 = 20 mVrms | 7.1 mVrms |
| Differential drain signal, peak | 28.3 mV | 10.0 mV |
| Differential drain signal, peak-to-peak | 56.6 mVpp | 20.0 mVpp |

The board value scales with the excitation ratio (5 mVpp / 14.1 mVpp = 0.354); with programmable excitation (AN-4) the drain signal scales linearly with the setting. The bench figure is consistent with the device physics: the ideal r₀ ≫ R_D swing at bench excitation (0.6–1.1 Vpp) could not fit inside a 50–250 mV drain DC level, which indicates a lower real stage gain. The chain gain ([§2.9](#29-gain-distribution-headroom-and-demodulator-output)) is set from the **board default** column with ≥ 4× headroom.

- [ ] TODO: confirm on the bench: drain AC swing per drain and maximum X/Y at the planned operating points (LAB-1, LAB-2).

### 2.6 Front End: Differential Conversion First

The selected active and blind drains reach the in-amp through the TMUX1109 bank A switch of each side; R_D (one per side) sits on the board side of that switch, and the in-amp taps the R_D/switch node directly (D-19: the separate TMUX1104 readout muxes were removed). The in-amp is DC-coupled (G = 10), followed by a single band-pass (Sallen-Key HPF + Sallen-Key LPF).

**Drain loading.** The transistor behaves as an AC current source g_m·δV_GS feeding the drain node, and everything attached to the node is in parallel for that current:

$$
v_d = g_m\cdot \delta V_{GS}\cdot \left(R_D \parallel r_0 \parallel Z_{\mathrm{in}}\right)
$$

```latex
v_d = g_m\cdot \delta V_{GS}\cdot \left(R_D \parallel r_0 \parallel Z_{\mathrm{in}}\right)
```

A Sallen-Key filter connected directly to the drain would present Z_in of a few kΩ to tens of kΩ and attenuate the signal by tens of times. A CMOS- or FET-input in-amp has GΩ-level input resistance and pA bias current, so Z_in ≫ R_D without dedicated buffers. What remains is the drain-node capacitance: TMUX1109 on-capacitance (≈ 38 pF typ.), in-amp input and traces, ≈ 50–60 pF in total. It forms a pole with R_D:

$$
f_p = \frac{1}{2\pi R_D C_{\mathrm{node}}} \approx \frac{1}{2\pi\cdot 330\ \mathrm{k\Omega}\cdot 55\ \mathrm{pF}} \approx 8.8\ \mathrm{kHz}
$$

```latex
f_p = \frac{1}{2\pi R_D C_{\mathrm{node}}} \approx \frac{1}{2\pi\cdot 330\ \mathrm{k\Omega}\cdot 55\ \mathrm{pF}} \approx 8.8\ \mathrm{kHz}
```

This is far above f₀ (≈ 3.4° phase at 518 Hz, identical on both sides to first order); only the **mismatch** between the two nodes matters ([§2.7](#27-common-mode-rejection)). The switch R_on (≈ 2 Ω) in series with 330 kΩ adds no measurable noise (√(4k_BT·2 Ω) ≈ 0.2 nV/√Hz) and its pA leakage shifts the DC level by µV only. The in-amp bias current flows through R_D and shifts each drain DC level by I_B·R_D (≤ ≈ 0.3 mV for 1 nA), which is calibrated by the drain-voltage measurement.

**Polarity.** In the 2026-10-24 netlist the blind node drives the in-amp +IN and the active node −IN; the sign of X is fixed in firmware (§2.13).

**DC headroom.** The in-amp is DC-coupled, so it amplifies the DC mismatch between the drains: ±200 mV → ±2 V at its output. This fits on ±5 V (FE-A/B) and, around V_REF = 2.5 V, on a single 5 V supply (FE-C, 0.5–4.5 V). The HPF removes it; requirement AN-12b (≤ ±200 mV) is met by firmware using the drain-supply DACs.

**1/f noise and reference frequency.** The transistor 1/f corner is ≈ 200 Hz at typical I_DS, below the band-pass −3 dB edge (377 Hz). 518 Hz lies between the 10th (500 Hz) and 11th (550 Hz) harmonics of 50 Hz mains, 18 Hz from the 10th; with programmable frequency (AN-1) the reference can be moved within the pass band (e.g. ≈ 525 Hz) to increase that distance if mains pickup is found on the bench.

**DC leakage on the drain nodes.** Any DC current drawn from the node produces an offset (1 nA → 330 µV). Use guard rings and keep-outs around the drain traces; no other part (e.g. a current-sense amplifier) may connect to the drain node.

**Load resistor quality.** R_D sets both the signal gain and the CMRR. Use a matched pair of 0.1 %, ≤ 25 ppm/°C thin-film resistors from one reel, placed side by side.

### 2.7 Common-Mode Rejection

With the in-amp first, CM-to-DM conversion comes from mismatch between the two drain nodes (R_D and node capacitance), not from the filters. Monte-Carlo, 50 000 trials, C_node = 20 pF (SIM-2; to be re-run with 50–60 pF as SIM-12):

| R_D tolerance | C_node (20 pF) mismatch | In-amp CMRR | System CMRR median | 99 % worst |
|---------------|-------------------------|-------------|--------------------|------------|
| 0.05 % | ±5 % | 90 dB | 62 dB | 54 dB |
| **0.1 %** | **±10 %** | **90 dB** | **56 dB** | **48 dB** |
| 0.1 % | ±20 % | 90 dB | 52 dB | 42 dB |
| 1 % | ±10 % | 90 dB | 44 dB | 35 dB |
| 0.1 % | ±10 % | 80 dB | 56 dB | 48 dB |

The capacitive part scales with ω·R_D·ΔC. With C_node ≈ 55 pF and ±10 % mismatch (5.5 pF) it is ≈ 2π·518·330 kΩ·5.5 pF ≈ 5.9·10⁻³ (≈ 45 dB), mostly in quadrature (Y) and static; the on-board common-mode calibration measures and subtracts it. Keep the two drain paths (socket → switch → R_D → in-amp) strictly symmetric.

### 2.8 Band-Pass Filter Design

The band-pass is a 2nd-order Sallen-Key high-pass followed by a 2nd-order Sallen-Key low-pass, both tuned to f₀ = 518 Hz with Q = 1. At f₀ the high-pass contributes +90° and the low-pass −90°, so the filter has **0° phase at f₀**, with 40 dB/decade slopes on each side.

$$
H(s) = K_H K_L\,\frac{(s/\omega_0)^2}{(s/\omega_0)^2 + \frac{s}{Q\omega_0} + 1}\cdot\frac{1}{(s/\omega_0)^2 + \frac{s}{Q\omega_0} + 1}, \qquad \omega_0 = 2\pi\cdot 518\ \mathrm{Hz}
$$

```latex
H(s) = K_H K_L\,\frac{(s/\omega_0)^2}{(s/\omega_0)^2 + \frac{s}{Q\omega_0} + 1}\cdot\frac{1}{(s/\omega_0)^2 + \frac{s}{Q\omega_0} + 1}, \qquad \omega_0 = 2\pi\cdot 518\ \mathrm{Hz}
```

Trade-off between section Q, bandwidth and sensitivity to excitation-frequency changes (unity-gain sections):

| Section Q | Gain at f₀ | −3 dB band | Rel. attenuation 50 Hz / 150 Hz / 2f₀ / 3f₀ | Phase change over ±1 % frequency |
|-----------|-------------|------------|----------------------------------------------|----------------------------------|
| 0.707 | 0.74 | 318–843 Hz | −34 / −15 / −6 / −12 dB | 2.9° |
| **1 (selected)** | **1.00** | **377–711 Hz** | **−41 / −21 / −10 / −18 dB** | **4.6°** |
| 1.5 | 2.25 | 419–641 Hz | −48 / −27 / −16 / −25 dB | 6.9° |
| 2 | 4.0 | 441–608 Hz | −53 / −32 / −20 / −29 dB | 9.2° |

With the excitation clock-derived (±50 ppm), frequency drift does not move θ. When the frequency is changed on purpose, gain and phase of the filter change along the curve above and must be taken from the on-board calibration ([§2.13](#213-calibration)).

**Implementation 1 — unity-gain sections (FE-A, as drawn).** Ratio 4Q² = 4 for Q = 1:

| Section | Components | Relations | Values |
|---------|------------|-----------|--------|
| HPF | C1 = C2 = C (series), R_f (cap junction → output), R_g (+input → reference) | Q = ½·√(R_g/R_f), R_f = 1/(2·Q·ω₀·C), R_g = 4Q²·R_f | C = 33 nF, R_f = 4.64 kΩ, R_g = 18.7 kΩ |
| LPF | R1 = R2 = R (series), C1 (junction → output), C2 (+input → reference) | Q = ½·√(C1/C2), C2 = 1/(2·Q·ω₀·R), C1 = 4Q²·C2 | R = 4.64 kΩ, C2 = 33 nF, C1 = 132 nF (4 × 33 nF) |

**Implementation 2 — equal-component sections with gain K = 2 (FE-B, FE-C).** With R1 = R2 = R and C1 = C2 = C, a non-inverting gain K sets Q directly, for the low-pass and the high-pass alike:

$$
Q = \frac{1}{3-K}, \qquad f_0 = \frac{1}{2\pi RC}, \qquad |H(f_0)| = K\,Q; \qquad K = 2 \;\Rightarrow\; Q = 1,\ |H(f_0)| = 2
$$

```latex
Q = \frac{1}{3-K}, \qquad f_0 = \frac{1}{2\pi RC}, \qquad |H(f_0)| = K\,Q; \qquad K = 2 \;\Rightarrow\; Q = 1,\ |H(f_0)| = 2
```

Both sections: C = 33 nF C0G 1 %, R = 9.31 kΩ 0.1 % (f₀ = 518 Hz), gain resistors 10.0 kΩ / 10.0 kΩ 0.1 %. The band-pass then has **×4 at f₀**, 0° phase, Q = 1, and no ratioed part banks. Sensitivity: dQ/Q = K/(3−K)·dK/K = 2·dK/K, so 0.1 % gain resistors move Q by ≈ 0.2–0.3 %. To be confirmed by Monte-Carlo (SIM-14).

Use C0G/NP0 1 % capacitors and 0.1 % thin-film resistors. Tolerance spread at f₀ for implementation 1 (SIM-4):

| Components | Gain σ | Gain 99 % range | Phase σ | Phase 99 % range |
|------------|--------|-----------------|---------|------------------|
| R 0.1 %, C 1 % (C0G) | 0.06 dB | ±0.14 dB | 0.66° | ±1.6° |
| R 1 %, C 5 % | 0.31 dB | ±0.72 dB | 3.4° | ±8.2° |

### 2.9 Gain Distribution, Headroom and Demodulator Output

**Where the gain goes.** In a lock-in, offsets and slow drift that appear **before** the demodulator are DC and get chopped by the demodulator to f₀, where the post-filter removes them. Offsets, 1/f noise and drift that appear **after** the demodulator land directly on X and Y as baseline drift. For slow gas measurements the baseline matters most, so the rule is: put as much gain as headroom allows **before** the demodulator, and keep the post-filter gain small.

- The in-amp is DC-coupled and limited by the ±200 mV drain mismatch to G = 10.
- After the HPF there is no DC, so gain there is free (band-pass K = 2 per section, ×4).
- The demodulator's input range sets the upper limit before demodulation.
- The post-filter gain is chosen so the **ADS1220 full scale is reached before any analog stage clips**.

The three front-end options (decision D-18, [schematic_overview §4.9](../LIA-Readout/docs/schematic_overview.md#49-front-end-architecture-options-decision-d-18)) all give the same overall scale factor; they differ in where the gain sits:

| Stage | FE-A (AD630, ±5 V) | FE-B / FE-C (switch demodulator) |
|-------|--------------------|-----------------------------------|
| In-amp | ×10 → 0.1 V pk | ×10 → 0.1 V pk |
| Band-pass at f₀ | ×1 → 0.1 V pk | ×4 → 0.4 V pk |
| Demodulator | ±2 (AD630 Fig. 29), input limit ±0.8 V pk (−V_S + 4 to +V_S − 1 at ±5 V) | ±1, input limit ≈ ±2.4 V around the reference (rail-to-rail op-amp) |
| Demodulator DC output | 0.127 V | 0.255 V |
| Post-filter | −3 | −1.5 |
| ADC (default, 10 mV pk drain) | 0.38 V = 19 % FS | 0.38 V = 19 % FS |
| Drain level at ADC full scale | 53.6 mV pk | 53.6 mV pk (demodulator input then 2.14 V pk) |
| Post-demodulator drift referred to the drain (OPA2196 ≈ 1 µV/°C, ×2 noise gain) | ≈ 0.15 µV/°C | ≈ 0.08 µV/°C |

Because the drain signal scales with the excitation, the linear range of ≈ 53 mV pk covers the full programmable excitation range (AN-4, ≤ 20 mVpp) at the expected Δg_m. Firmware flags ADC and demodulator overload from |X|, |Y|.

The demodulator with a square-wave reference produces a DC output; the chain scale factor at the ADC input is the same for all options:

$$
V_{X,\mathrm{ADC}} - V_{\mathrm{ref}} = -G_{\mathrm{post}}\cdot\frac{2}{\pi}\,G_{\mathrm{pre}}\,\hat v_{\mathrm{diff}}\cos\theta \approx -38.2\,\hat v_{\mathrm{diff}}\cos\theta, \qquad V_{Y} \propto \sin\theta
$$

```latex
V_{X,\mathrm{ADC}} - V_{\mathrm{ref}} = -G_{\mathrm{post}}\cdot\frac{2}{\pi}\,G_{\mathrm{pre}}\,\hat v_{\mathrm{diff}}\cos\theta \approx -38.2\,\hat v_{\mathrm{diff}}\cos\theta, \qquad V_{Y} \propto \sin\theta
```

(G_pre·G_post = 20·3 for FE-A, 40·1.5 for FE-B/C; V_ref = VMID or V_REF.) To compare with SR860 readings (rms), use v̂_diff = √2·v_rms.

### 2.10 Demodulator Low-Pass Filter and Oversampling

The post-demodulator filter is first order with τ = 500 ms (f_c = 0.318 Hz, equivalent noise bandwidth 1/(4τ) = 0.5 Hz). It attenuates the 2f₀ ripple of the demodulator output by ≈ 70 dB, and the ADS1220 digital filter adds further rejection.

Oversampling can only **lengthen** the effective time constant (narrow the bandwidth, lower noise) by digital averaging. It cannot make the response faster than the analog τ, because content above 0.318 Hz is already removed before the ADC. The analog τ is therefore fixed at 500 ms (the shortest response needed); longer time constants are implemented in software. The ADS1220 provides 20–1000 SPS, so even with X and Y multiplexed there are ≥ 10 samples per τ.

Settling after a step (channel switch, operating-point change): 3.5 s to 0.1 % (6.9τ), 6.9 s to 1 ppm (13.8τ).

### 2.11 Noise and SNR

The SNR is fixed at the drain node, before any amplifier, so the supply rails and later gain stages cannot change it. A transistor in subthreshold carries full shot noise on its drain current, which is far larger than the thermal noise of R_D:

$$
e_{n,R_D} = \sqrt{4 k_B T R_D} \approx 74\ \mathrm{nV/\sqrt{Hz}}, \qquad \frac{S_{i,\mathrm{MOS}}}{S_{i,R_D}} = \frac{2 q I_D}{4 k_B T / R_D} = \frac{I_D R_D}{2 k_B T / q} \approx \frac{7.5\,\mu\mathrm{A}\cdot 330\,\mathrm{k\Omega}}{51.7\,\mathrm{mV}} \approx 48
$$

```latex
e_{n,R_D} = \sqrt{4 k_B T R_D} \approx 74\ \mathrm{nV/\sqrt{Hz}}, \qquad \frac{S_{i,\mathrm{MOS}}}{S_{i,R_D}} = \frac{2 q I_D}{4 k_B T / R_D} = \frac{I_D R_D}{2 k_B T / q} \approx \frac{7.5\,\mu\mathrm{A}\cdot 330\,\mathrm{k\Omega}}{51.7\,\mathrm{mV}} \approx 48
```

Each drain therefore carries ≈ 510 nV/√Hz (r₀ ≫ R_D), ≈ 730 nV/√Hz differential, and the transistors dominate. A finite r₀ lowers signal and noise in the same proportion. Since signal and noise both scale with the node impedance, the white-noise SNR depends only on the excitation, the drain current and the bandwidth:

$$
\mathrm{SNR} = \frac{g_m\,\delta V_{GS}}{\sqrt{2 q I_D B}} = \frac{\delta V_{GS}}{n\,k_B T/q}\sqrt{\frac{I_D}{2 q B}}
$$

```latex
\mathrm{SNR} = \frac{g_m\,\delta V_{GS}}{\sqrt{2 q I_D B}} = \frac{\delta V_{GS}}{n\,k_B T/q}\sqrt{\frac{I_D}{2 q B}}
```

R_D drops out, and so do the rails and every gain stage after the drain. With B = 0.5 Hz the differential noise referred to the drain is

$$
v_{n,\mathrm{drain}} = e_{n,\mathrm{diff}}\sqrt{\frac{1}{4\tau}} \approx 0.73\ \mu\mathrm{V}/\sqrt{\mathrm{Hz}}\cdot 0.71 \approx 0.52\ \mu\mathrm{V_{rms}}
$$

```latex
v_{n,\mathrm{drain}} = e_{n,\mathrm{diff}}\sqrt{\frac{1}{4\tau}} \approx 0.73\ \mu\mathrm{V}/\sqrt{\mathrm{Hz}}\cdot 0.71 \approx 0.52\ \mu\mathrm{V_{rms}}
```

i.e. ≈ 82 dB SNR at the default 10 mV pk drain signal; 1/f noise and drift reduce it.

**ADC and amplifier noise budget.** With the total gain of 60 (in-amp × band-pass × post-filter) the sensor noise at the ADC is ≈ 0.52 µV × 60 ≈ 31 µV rms. The ADS1220 at 20 SPS, gain 1, contributes a few µV rms (datasheet noise table), so the chain is **sensor-limited**; the ADC's noise-free resolution is ≈ 20 bits, and its 24 bits only guarantee that the ADC never limits. Amplifier noise referred to the drain: INA828 ≈ 7 nV/√Hz, INA333 ≈ 50 nV/√Hz (+0.2 % noise power against 730 nV/√Hz); later stages are divided by the preceding gain and negligible.

**What improves SNR:** a larger δV_GS (up to the onset of nonlinearity, programmable), a larger I_D (SNR ∝ √I_D in subthreshold), longer averaging (software τ), and device-level effects (reference frequency vs 1/f corner, active/blind matching, thermal stability).

### 2.12 Excitation and Reference Generation

The excitation sine and the two lock-in references are generated digitally by the MCU from one clock (D-3). The implementation (peripherals, register values, code structure) is specified in [firmware_requirements.md](../../firmware/firmware_requirements.md); this section states the principles it must satisfy.

**One sine, two references.** Both gate groups receive the **same** sine (AN-3). The X and Y references are logic square waves, X in phase with the sine and Y delayed by a quarter period. No analog cosine is needed: a square-wave demodulator only needs the switching instants.

**Coherence by integer ratio.** The sine is produced by DAC1 channel 1 stepping through an N-entry table, one entry per trigger from a sample timer; the references come from a second timer in output-compare toggle mode. Both timers run from the same 160 MHz kernel clock, and the reference timer's period is made an exact integer multiple of the sample period, so the two can never drift relative to each other:

$$
f_s = \frac{f_{\mathrm{TIM}}}{ARR_s+1}, \qquad f_0 = \frac{f_s}{N}, \qquad (ARR_r+1)(PSC_r+1) = \frac{N}{2}\,(ARR_s+1)
$$

```latex
f_s = \frac{f_{\mathrm{TIM}}}{ARR_s+1}, \qquad f_0 = \frac{f_s}{N}, \qquad (ARR_r+1)(PSC_r+1) = \frac{N}{2}\,(ARR_s+1)
```

In toggle mode each output changes state once per reference-timer period, so one reference period equals two timer periods = N samples. Channel 2 toggles half a timer period after channel 1, i.e. a quarter of the reference period: exactly 90°. Both timers are started by one hardware event (master/slave trigger), so the start offset is zero or a fixed number of clock cycles.

**Numbers (default).** f_TIM = 160 MHz, N = 128: ARR_s = 2412 → f_s = 66.31 kHz, f₀ = 518.03 Hz. Reference timer: PSC_r = 3, ARR_r = 38607 (= 16·2413 − 1). Frequency steps at 518 Hz ≈ 0.2 Hz; any ARR_s ≤ 4095 keeps a 16-bit reference timer in range (f₀ ≥ 305 Hz).

**Sample count and images.** N = 128 samples per period puts the first DAC image at f_s − f₀ ≈ 65.8 kHz. The MFB stage (f₀ = 4.95 kHz, 2nd order) attenuates it by ≈ 45 dB, the gate attenuation by 1/120 and finally the band-pass. Quantization: at the default 5 mVpp the DAC swings 0.6 Vpp (≈ 745 codes pp), SFDR ≈ 60 dB (THD ≈ 0.1 %, AN-7b).

**Amplitude.** Set by scaling the table (AN-4). It is proportional to VDDA, which is the DAC reference on the LQFP64 package, and to the MFB gain ratio. X/Y scale directly with it, so VDDA stability is part of the measurement accuracy (D-D: ferrite-filtered +3V3_D with firmware calibration against the DAC80508 internal reference, or a dedicated 3.3 V reference).

**Phase.** Sample 0 of the table is sin(0) and the X reference rises at sample 0, so X is nominally in phase with the DAC output. The MFB stage (≈ 8° lag at 518 Hz), the drain pole (≈ 3°), and the rest of the chain add a fixed lag that is removed by calibration (rotation of X/Y in firmware) or by rotating the table start index (360°/N = 2.8° per sample).

**Harmonics.** Harmonics on the gate produce drain signals at 2f₀ and 3f₀. They are suppressed by the band-pass (−10 dB at 2f₀, −18 dB at 3f₀), by the square-wave demodulator (even harmonics rejected, 3rd weighted 1/3) and by the small-signal operating point; with THD ≤ 0.3 % the error on X/Y is ≈ 10⁻⁴.

### 2.13 Calibration

- **DC chain check (mux position 4).** In position 4 of TMUX1109 bank A each side's drain path is connected to a 0.1 % precision resistor to GND (R_CAL ≈ 18 kΩ) instead of a pixel. With V_supply = 3 V the node sits at ≈ 155 mV and ≈ 8.6 µA flows, the same operating point as a pixel. The current is known two independent ways, (V_supply − V_node)/R_D and V_node/R_CAL, which checks the DAC, the bias amplifier, R_D, the switch and the drain sense against each other.
- **Heater chain check.** Bank B position 4 connects a 0.1 % dummy heater (680 Ω–1 kΩ) on each side, so each heater driver and its INA190 are verified against a known load.
- **Chain gain and phase (optional tone).** Returning the active-side R_CAL to GND through 100 Ω, and driving that 100 Ω from MCU DAC1_OUT2 through 10 kΩ, injects a known differential tone of ≈ 9 mVpp per 1 Vpp DAC amplitude at f₀ (close to the real signal). Measuring it gives the chain gain and phase at the current frequency; θ is corrected numerically (rotate X/Y). The blind side gets 100 Ω to GND for symmetry.
- **Common-mode leakage.** Excite both gates with the pixels selected but the drain supplies equal (or use matched pixels): the residual X/Y measures the CM-to-DM leakage, which scales with g_m and can be subtracted.
- **Zero offset.** With the muxes disabled (EN = 0) the demodulator input carries only noise: the averaged X/Y is the post-demodulator offset, subtracted in firmware.
- **Sign convention.** In-amp polarity (§2.6), the inverting common-source stage and the inverting post-filter set the sign of X; document it for g_m,A > g_m,B after the first board measurement (LAB-9).
- **Bias.** I_D = (V_supply − V_D)/R_D with V_supply from the coarse/fine DAC setting ([§2.14](#214-drain-bias-with-coarse-and-fine-dacs)); measure each R_D once in circuit and store it.

### 2.14 Drain Bias with Coarse and Fine DACs

Each side's drain supply is produced by a difference amplifier from two DAC80508 channels (coarse DAC2/DAC3, fine DAC6/DAC7):

$$
V_{SUP} = (1+k)\,V_{\mathrm{coarse}} - k\,V_{\mathrm{fine}}, \qquad k = \frac{R_F}{R_G}
$$

```latex
V_{SUP} = (1+k)\,V_{\mathrm{coarse}} - k\,V_{\mathrm{fine}}, \qquad k = \frac{R_F}{R_G}
```

The coarse step is (1+k)·LSB_c and the fine step k·LSB_f. With k = 1 (50 k/50 k, as drawn) the fine step equals one DAC LSB at gain 1 (38 µV): no gain in resolution. With **k = 0.1** (R_F = 10 kΩ, R_G = 100 kΩ) and the coarse channel at gain 2: coarse step ≈ 84 µV, fine step 3.8 µV over a 250 mV trim range, output up to ≈ 3.5 V.

Whether fine resolution matters depends on r₀: the drain current moves by ΔV_SUP/(R_D + r₀). With r₀ of a few MΩ (saturation) a 76 µV step changes I_D by a few pA, already below the 46 pA target; the fine trim is insurance in case LAB-7 shows a low r₀.

**Noise.** The transistor acts as a current source, so supply noise passes almost entirely to the drain node and adds to the differential signal (the two sides are uncorrelated). The DAC and op-amp noise (≈ 100–200 nV/√Hz) must therefore be filtered: 1 kΩ + 10 µF after the op-amp output (f_c ≈ 16 Hz, ≈ 30 dB at f₀), feedback taken at the op-amp output. The 10 mV DC drop at 10 µA is constant and included in the current calculation. Verify in SIM-20.

### 2.15 Single-Supply Referencing (V_REF)

An op-amp has no ground pin; it only sees node voltages relative to its two supply rails. Moving the signal zero from 0 V to V_REF = 2.5 V on a single 5 V supply therefore changes nothing in noise, gain or bandwidth, provided that:

1. **One reference node** feeds every reference point: in-amp REF pin, HPF and LPF returns, the demodulator's "zero" input, the post-filter +IN and the ADS1220 AIN1/AIN3. Then noise and drift on V_REF move all signals together and cancel in the differential ADC measurement X − V_REF. V_REF is star-routed from a low-impedance source (REF3325) with 1–10 µF local decoupling (verify its stable output-capacitor range).
2. **Headroom:** rail-to-rail outputs reach within ≈ 50 mV of the rails at light load, i.e. ≈ ±2.4 V around 2.5 V (more symmetric swing than the AD630 has at ±5 V, ≈ ±1 V).
3. **Input-stage transition region (important).** Rail-to-rail-input op-amps with two input pairs have a region where both pairs are active and offset, CMRR, noise and THD degrade. For the OPA2196 it is **(V+) − 3 V to (V+) − 1.5 V** (datasheet §7.3.6), i.e. **2.0–3.5 V on a 5 V rail**, exactly around V_REF = 2.5 V; its noise also rises from 15 to 24 nV/√Hz there. In the band-pass and the demodulator the inputs follow the signal around V_REF, so the OPA2196 is **not suitable** for the single-supply signal path. Use a zero-crossover (single input pair with charge pump) rail-to-rail op-amp such as the OPA2365 (2.2–5.5 V, 25 V/µs, 200 µV max offset; verify datasheet), or move V_REF below 2 V at the cost of asymmetric swing. On ±5 V (FE-A/FE-B) the signals sit around 0 V, 2 V below the transition region, so the OPA2196 remains fine there (verify at full scale: 2.14 V pk just touches the region).
4. **In-amp input range:** the drains sit at 50–250 mV with up to ±200 mV common-mode swing, i.e. down to ≈ 0 V. A rail-to-rail-input in-amp such as INA333 reaches only ≈ (V−) + 0.1 V, so its V− is taken from a small negative bias generator (LM7705, −0.23 V), which shifts the range to ≈ −0.13 V. The in-amp output and everything after it stay on 0…5 V. No −5 V rail is needed.

### 2.16 Switch-Based Synchronous Demodulator

A synchronous demodulator multiplies the signal by ±1 in step with the reference. With an op-amp, two equal resistors and an SPDT switch (FE-B: ±5 V, zero = GND; FE-C: single 5 V, zero = V_REF):

- input → R_i → −IN; R_f from −IN to the output (k = R_f/R_i = 1);
- switch common → +IN; switch inputs = signal and zero; switch select = reference square wave.

$$
V_{out}-V_{0} = (1+k)(V_{+}-V_{0}) - k\,(V_{in}-V_{0}) \;\Rightarrow\; \begin{cases} +(V_{in}-V_{0}) & V_{+}=V_{in}\\ -k\,(V_{in}-V_{0}) & V_{+}=V_{0}\end{cases}
$$

```latex
V_{out}-V_{0} = (1+k)(V_{+}-V_{0}) - k\,(V_{in}-V_{0}) \;\Rightarrow\; \begin{cases} +(V_{in}-V_{0}) & V_{+}=V_{in}\\ -k\,(V_{in}-V_{0}) & V_{+}=V_{0}\end{cases}
```

The positive half has gain exactly +1 regardless of the resistors; a mismatch k = 1 + δ only gives a demodulator gain of 1 + δ/2 and a small ripple at f₀ (removed by the post-filter). This is the topology of ADI's Analog Dialogue article "Synchronous Detectors Facilitate Precision Low-Level Measurements" (Fig. 4: an ADG619 switch toggles an amplifier between +1 and −1), the chopper principle of LT AN9 (Williams, 1986), and in essence the internal structure of the AD630.

**Error budget at 518 Hz:**

| Effect | Size | Comment |
|--------|------|---------|
| R_i/R_f mismatch (0.1 %) | 0.05 % gain | Fixed, calibrated |
| Switch R_on | 0 | In series with the op-amp +IN (high impedance) |
| Charge injection (TMUX1219 ≈ 10 pC, TMUX6136 ≈ 0.4 pC per edge) | ≈ nA average into low-impedance nodes | Negligible |
| Timing skew (≈ 20 ns) | ≈ 0.004° | MCU sets the reference phase anyway |
| Op-amp offset | 2·V_OS (≈ 200 µV for OPA2196) | Static; zero-offset calibration |
| Op-amp slew at each switch edge | OPA2196 (7.5 V/µs) or OPA2365 (25 V/µs): < 0.03 µs, negligible | Avoid slow zero-drift parts (e.g. 0.16 V/µs): ≈ 0.1 % amplitude-dependent error |
| Op-amp input transition region | OPA2196: 2.0–3.5 V on a 5 V rail | FE-B (±5 V, signal around 0 V): fine. FE-C (around 2.5 V): use a zero-crossover op-amp (§2.15) |
| Harmonic response | Odd harmonics at 1/n, even rejected | Same as the AD630 with a square reference |

The topology was verified in simulation with an ideal switch (SIM-D1); vendor-model verification is SIM-10…SIM-13.