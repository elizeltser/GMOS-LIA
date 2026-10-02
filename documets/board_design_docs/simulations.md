
## 7. Simulation
 
The netlists in [`simulations/`](simulations/) use ideal op-amps and behavioral blocks so they run anywhere; each one notes where to drop in vendor models (TI OPA2192 and INA828 PSpice models, ADI AD630 macro-model) for a device-level run. They were cross-checked in ngspice with equivalent control scripts; the reference values below are from those runs.
 
| File | Analysis | What it shows |
|------|----------|---------------|
| `simulations/bpf_mc.cir` | AC + Monte Carlo (`.step` + `mc()`) | Band-pass gain/phase at 518 Hz, −3 dB edges, tolerance spread |
| `simulations/cmrr_mc.cir` | AC + Monte Carlo | System CMRR from R_D and drain-node capacitance mismatch |
| `simulations/chain_tran.cir` | Transient, 4 s | Full chain at a selected operating point: drain swing, X/Y after the τ = 500 ms filter |
| `simulations/quad_osc_tran.cir` | Transient, 0.8 s + `.four` | Quadrature oscillator start-up, amplitude, frequency, THD, reference divider level |
 
### 7.1 Running in LTspice
 
1. **File → Open**, set the file type to *Netlists (\*.cir, \*.net, …)*, open the `.cir` file, then **Run**. No schematic is needed; LTspice simulates the netlist directly.
2. **Results of `.meas`:** *View → SPICE Error Log*. For a stepped (Monte-Carlo) run, right-click inside the log → *Plot .step'ed .meas data*. This plots each measurement against the run index; export it with *File → Export data as text* for histograms.
3. **Nominal vs Monte-Carlo:** in `bpf_mc.cir` and `cmrr_mc.cir`, set `.param Nrun=1` and the tolerances to 0 for the nominal run; `Nrun=500` with the given tolerances for Monte-Carlo. `mc(x,tol)` draws a uniform value in x·(1 ± tol) for every step.
4. **Waveforms:** click a node in the waveform viewer, or use *Plot Settings → Add Trace* with e.g. `V(out)`, `V(xlpf)`, `V(dA)-V(dB)`.
5. **Vendor models:** download the TI/ADI model file, add `.include <file>` to the netlist, and replace the `E` element of the stage with an `X` subcircuit instance using the model's pin order.
### 7.2 Running in PSpice (e.g. the free PSpice for TI)
 
1. Draw the same circuit in the schematic editor, using `Rbreak`/`Cbreak` parts for the toleranced components and giving each a model with a deviation, e.g. `.model RTOL RES(R=1 DEV=0.1%)`, `.model CTOL CAP(C=1 DEV=1%)`.
2. *Simulation Settings → Analysis: AC Sweep*, and enable *Monte Carlo/Worst Case* with e.g. 500 runs, output variable `V(out)`.
3. In *Probe*, use *Performance Analysis* with the measurement `YatX(V(out),518)` for gain and `YatX(VP(out),518)` for phase; plot them as histograms over the runs.
4. TI's OPA2192 and INA828 models are native PSpice models and drop in directly.
### 7.3 Reference Values (ideal models)
 
| Simulation | Quantity | Python analytic | ngspice (60 runs) |
|------------|----------|-----------------|-------------------|
| Band-pass, nominal | Gain / phase at 518 Hz | 1.000 / 0° | 0.9999 / 0.76° (finite E-source gain) |
| Band-pass, nominal | −3 dB edges | 377 / 711 Hz | 379 / 713 Hz |
| Band-pass MC (0.1 % R, 1 % C) | Gain σ / phase σ | 0.06 dB / 0.66° | 0.06 dB / 0.56° |
| CMRR MC (0.1 % R_D, ±10 % C_node) | Median / worst | 56 dB / 48 dB (99 %) | 57 dB / 49 dB (min of 60) |
| Full chain, 5 % Δg_m, I_D = 7.5 µA | X / Y after 3.5 s | −0.190 V / 0 V | −0.190 V / +1.6 mV |
| Quadrature oscillator | Amplitude / frequency / THD (sin) | 517.6 Hz (ideal RC) | 6.33 Vpp / 520.7 Hz / 0.52 % |
 
### 7.4 Simulation Results (to be filled in)
 
#### Monte-Carlo
 
| Simulation | Runs | Tolerances | Gain at 518 Hz (mean / σ / min–max) | Phase at 518 Hz (mean / σ / min–max) | CMRR (median / min) | Notes |
|------------|------|------------|--------------------------------------|---------------------------------------|---------------------|-------|
| `bpf_mc.cir` | | | | | — | |
| `cmrr_mc.cir` | | | — | — | | |
| Device-level (vendor models) | | | | | | |
 
<!-- Add plots: -->
<!-- ![Band-pass Monte-Carlo gain histogram](simulations/results/bpf_mc_gain.png) -->
<!-- ![Band-pass Monte-Carlo phase histogram](simulations/results/bpf_mc_phase.png) -->
<!-- ![CMRR distribution](simulations/results/cmrr_mc.png) -->
 
#### Quadrature Oscillator
 
| Quantity | Simulation (vendor models) | Measured (board) |
|----------|----------------------------|------------------|
| Amplitude sin / cos (Vpp) | | |
| Frequency (Hz) | | |
| THD sin / cos (%) | | |
| Phase sin → cos (°) | | |
| Start-up time (s) | | |
 
<!-- ![Oscillator start-up and steady state](simulations/results/quad_osc_tran.png) -->
<!-- ![Oscillator spectrum](simulations/results/quad_osc_fft.png) -->
 
#### Selected Operating Point
 
| Parameter | Value |
|-----------|-------|
| I_D (A / B) | |
| V_D (A / B) | |
| Gate DC / excitation | |
| Δg_m assumed | |
| Drain AC swing, A (Vpp) | |
| Drain differential (Vpp) | |
| AD630 input (V peak) | |
| X / Y at ADC input (V) | |
| Settling time to 0.1 % (s) | |
 
<!-- Add plots: -->
<!-- ![Band-pass Bode plot](simulations/results/bpf_bode.png) -->
<!-- ![Full chain transient: drains, AD630 input, X/Y](simulations/results/chain_tran.png) -->
 
