
## 2. Measurement Principle & Design Considerations
 
### 2.1 Device and Sensing Mechanism
 
The GMOS is a micromachined CMOS-SOI pixel containing a transistor (29 nMOS devices in parallel, W = 204 µm, L = 4.15 µm) and an integrated heating resistor. Each package provides two usable differential channels, each composed of an **active** pixel (exposed, with catalytic layer) and a **blind** pixel (inert reference).
 
Gas combustion on the catalytic layer releases heat, raising the active pixel temperature by ΔT. This shifts the threshold voltage and subthreshold drain current of the active transistor relative to the blind one, and the difference appears as a differential signal between the two drain nodes. Because the blind pixel sees the same heater, ambient and supply conditions, common-mode drifts are rejected by the differential readout.
 
### 2.2 3T Readout Method
 
Each transistor is operated in a three-terminal configuration:
 
- **Gate:** DC bias plus a small sine excitation at the lock-in reference frequency.
- **Drain:** connected through a series load resistor R_D (≈ 330 kΩ) to a programmable supply.
- **Heater:** DC voltage, trimmed per pixel to equalize the drain currents of the active/blind pair.
The gate modulation δV_GS produces a drain-current modulation g_m·δV_GS, which R_D converts to a voltage. The lock-in output is therefore proportional to the differential transconductance:
 
$$
\Delta v_{d} = -(g_{m,A} - g_{m,B})\cdot \delta V_{GS}\cdot R_D
$$
 
The minus sign reflects the inverting common-source stage. The phase θ carries information on reactive elements in the signal path and is used for calibration.
 
### 2.3 Bench Setup → Board Block Mapping
 
| Bench instrument / setting | Board block | Notes |
|----------------------------|-------------|-------|
| SR860 reference out, 990 mV offset | Gate DC DAC + scaling op-amp + summing amp | Board range 0.97–1.2 V |
| SR860 reference out, 5 mVrms (≈ 14.1 mVpp) | Quadrature oscillator (518 Hz) + attenuating summing amp | Board: 5 mVpp |
| Lab supply on drain resistors | Drain DACs + scaling op-amps + R_D | Board range 2.7–3.5 V |
| Lab supply on heaters (2.7–2.9 V) | Heater DACs + driver op-amps | Board range 2.5–4.0 V |
| SR560: differential input, gain 20 V/V, BPF 300 Hz–1 kHz (6 dB/oct) | INA (G = 10, DC-coupled) → SK HPF → SK LPF → ×4 | Board: 40 V/V, 377–711 Hz (12 dB/oct) |
| SR860 demodulator (X, Y, R, θ) | AD630 pair + post-LPF (τ = 500 ms) + 24-bit ADC; R, θ computed in MCU/PC | |
 
As on the bench (SR560 differential input stage, then filters), the differential conversion happens first and the filtering is done once on the difference signal.
 
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
 
With I_DS = 5–10 µA and R_D = 330 kΩ the drain node sits at 50–250 mV. The 50 mV lower bound is kept so that the transistors can also be characterized with the heaters off (pixel at room temperature). At elevated pixel temperature the firmware keeps V_DS above the value in the table.
 
**AC drain swing.** The 3T stage is a common-source amplifier. Assuming r_0 ≫ R_D, with g_m = I_DS/(n·k_B·T/q):
 
$$
v_{d,pp} \approx g_m R_D\cdot \delta V_{GS,pp} = \frac{I_{DS} R_D}{n\cdot k_B T/q}\cdot \delta V_{GS,pp}
$$
 
| Pixel temperature | I_DS·R_D = 1.65 V (5 µA) | I_DS·R_D = 3.3 V (10 µA) |
|-------------------|--------------------------|--------------------------|
| 300 K | gain ≈ 40 → ≈ 200 mVpp | gain ≈ 80 → ≈ 400 mVpp |
| 673 K | gain ≈ 18 → ≈ 90 mVpp | gain ≈ 36 → ≈ 180 mVpp |
 
> (n = 1.6, δV_GS = 5 mVpp.) 
 
This is an upper bound. A finite r_0 lowers it. The bench data ([§2.5](#25-expected-signal-level-from-bench-data)) suggests the real stage gain is lower than this estimate. For clean small-signal operation the swing must also respect the V_DS limit:
 
$$
V_{DS,\mathrm{DC}} - \frac{v_{d,pp}}{2} > \frac{3 k_B T}{q}
$$
 
The drains carry this signal as **common mode** (both transistors share the gate excitation), which the readout must reject ([§2.7](#27-common-mode-rejection)).
 
The gate excitation must remain a small signal relative to n·k_B·T/q ≈ 41 mV (300 K) to 93 mV (673 K); 5 mVpp satisfies this.

# Noise analysis

 SNR is fixed at the drain node, before any amplifier, so the supply rails can't change it. A transistor in subthreshold has full shot noise on its drain current, and that is far larger than R_D's thermal noise:
$$
e_{n,R_D} = \sqrt{4 k_B T R_D} \approx 74\ \mathrm{nV/\sqrt{Hz}}, \qquad \sqrt{2}\,e_{n,R_D} \approx 105\ \mathrm{nV/\sqrt{Hz}}\ \text{(differential)}

$$
\frac{S_{i,\mathrm{MOS}}}{S_{i,R_D}} = \frac{2 q I_D}{4 k_B T / R_D} = \frac{I_D R_D}{2 k_B T / q} \approx \frac{7.5\,\mu\mathrm{A}\cdot 330\,\mathrm{k\Omega}}{51.7\,\mathrm{mV}} \approx 48
$$

So each drain carries about 520 nV/√Hz (assuming r₀ ≫ R_D), not 74 nV/√Hz, and the transistors dominate the noise. Since signal and noise both scale with g_m, the white-noise SNR depends only on the excitation, the drain current and the bandwidth:

$$
\mathrm{SNR} = \frac{g_m\,\delta V_{GS}}{\sqrt{2 q I_D B}} = \frac{\delta V_{GS}}{n\,k_B T/q}\sqrt{\frac{I_D}{2 q B}}
$$

R_D drops out, and so do the rails and every gain stage after the drain. With a 5 % Δg_m mismatch and the 500 ms filter (B = 0.5 Hz), this gives roughly 80 dB from white noise alone. The transistor's 1/f noise and drift add to that.

The things that actually improve SNR are:

- Gate excitation: larger δV_GS, up to where the response turns nonlinear.
- Drain current: SNR rises with √I_D while the device stays in subthreshold.
- Averaging time: a longer effective τ, which you already plan to do in software.
- Device-level effects: reference frequency relative to the 1/f corner, active/blind matching, and thermal stability.

