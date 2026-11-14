# Simulation index

> **Paths.** Paths that start with `simulations/` are relative to the repository root. All other backticked paths (`circuits/`, `tools/`, `ti-pspice-PSpiceFiles/`, `vendor/`, `archive/`, `docs/`) are relative to the PSpice for TI project, [`ti-pspice/`](ti-pspice/CLAUDE.md).

This file lists every simulation of the project, finished or planned. Each entry states the goal, the schematic that runs, the simulation parameters and the expected results. Below those it records the status, the result and the grade. The workflow that fills these entries is described in `ti-pspice/CLAUDE.md` under "Simulation workflow".

Identifiers: `C-xx` are completed simulations, `P-xx` are planned ones. A planned entry keeps its identifier when it is completed. A planned entry that is no longer required has the status "deprecated" with the reason and its replacement. It stays listed. The detailed results of each run are in `simulations/ti-pspice/docs/sim-results/<ID>.md`.

## Common definitions for the LIA tests

The LIA netlist (`ti-pspice-PSpiceFiles/LIA/LIA.net`, netlisted 26 October 2026) has these parameters:

| Parameter | Value in the schematic | Meaning |
|---|---|---|
| `f_osc` | 517 Hz | Input and reference frequency |
| `vdc` | 5 V | Supply, and twice the signal midpoint |
| `ost` | 0 V | Offset added to the input midpoint `vdc/2` |
| `p` | 0 deg | Phase of the input sine |
| `t_slope` | 100 ns | Rise and fall time of both reference square waves |

The input is `V4 = SIN({Vdc/2+ost} 2 {f_osc} 0 0 {p})`, so its amplitude is A = 2 V. The X reference V2 is high in the first half of each period. The Y reference V6 is delayed by a fixed 482.6 us.

Ideal theory for a +1/-1 square-wave demodulator, derived in `ti-pspice-PSpiceFiles/LIA/README.md`:

- VX = vdc/2 - (2A/pi) cos(p)
- VY = vdc/2 + (2A/pi) sin(p - d), where d = 360 deg x (T/4 - 482.6 us) / T is the timing error of the Y reference. For f_osc = 517 Hz, T = 1.934236 ms, T/4 = 483.559 us and d = 0.18 deg.
- R = sqrt((VX - 2.5)^2 + (VY - 2.5)^2) = 2A/pi = 1.2732 V for A = 2 V.
- A DC offset `ost` does not change VX or VY, as long as the signal stays inside the 0 V to 5 V rails.
- The RC output filter has tau = 10 kOhm x 10 uF = 0.1 s. The outputs settle as exp(-t / 0.1 s).

Measurement rule for settled values: average VX and VY over the last 50 whole periods of the run (96.7 ms at 517 Hz). PSpice's `max(V(VX))` also includes the 2f ripple, which is about 1.3 mV peak for A = 2 V. So it reads slightly higher than the mean.

Default run settings unless an entry says otherwise:

| Setting | Value | Reason |
|---|---|---|
| Analysis | `.TRAN 0 1 0 5u SKIPBP` | 1 s is 10 tau. A maximum step removes the 5.6 % error of C-03. The step still leaves a gain error of about (n x 2 pi f_osc x h)^2 / 12 at harmonic n. At the fundamental this is 0.036 % with 20 us, 0.003 % with 5 us and 0.0005 % with 2 us (P-05 time-step check). Use 2u when harmonics above the 3rd matter or when errors below 0.01 mV matter. A 2u run of 1 s takes about 3 min per step. P-01 to P-07 were run with 20u, so their VX values carry the 0.036 % error. |
| Initial conditions | `.IC V(VX)=2.5 V(VY)=2.5` | The filter capacitors start at the 2.5 V midpoint, not at 0 V. Validated in P-01. The remaining settling bias of the last-50-period mean is about 0.1 mV x abs(V - 2.5 V) / 1.27 V. Use `.TRAN 0 1.2 ...` when 0.1 mV matters. |
| Probes | `V(VX) V(VY) V(VX_DEMOD) V(VY_DEMOD) V(N00890)` | Only what the analysis needs. Saving all nodes produced a 2.95 GB file in C-07. |
| Output precision | `.OPTIONS NUMDGT=8` | The default four digits resolve only 1 mV. |

---

## Completed simulations

### C-01 SPDT_PREC select polarity

- **Goal:** confirm which throw of the behavioural TMUX6136 switch is connected for each SEL level.
- **Schematic:** `circuits/spdt_prec_select_test.cir` (S1 = 1 V, S2 = 2 V, SEL pulses 0 V to 5 V).
- **Parameters:** `.TRAN 0 3m 0 1u`.
- **Expected:** D = S1 while SEL is low, D = S2 while SEL is high, as the model header states.
- **Status:** done, 26 October 2026. **Result:** D = 0.9999 V with SEL low and 2.0000 V with SEL high. **Grade:** A. Details in `vendor/README.md`.

### C-02 INA828 gain

- **Goal:** confirm the INA828 model gain with RG = 5 kOhm.
- **Schematic:** `circuits/ina828_gain_test.cir`.
- **Parameters:** `.AC DEC 10 10 10k`, 1 V AC differential input.
- **Expected:** G = 1 + 50 kOhm / RG = 11 V/V (datasheet formula).
- **Status:** done. **Result:** 11.00 V/V from 10 Hz to 1 kHz, 11.002 V/V at 10 kHz. **Grade:** A.

### C-03 LIA settled outputs and time-step study (earlier circuit)

- **Goal:** compare the settled VX and VY with theory and find the cause of a 5.6 % shortfall.
- **Schematic:** `LIA/lia_sanity` as netlisted on 26 October 2026 before the parameter change (A = 0.25 V, f = 518 Hz, Y reference delayed by T/2).
- **Parameters:** `.TRAN 0 2 0 <max step> SKIPBP`, max step none, 20 us, 5 us and 2 us. `NUMDGT=8` for the reference run.
- **Expected:** VX = 2.5 V - (2/pi)(0.25 V) = 2.340845 V. VY = 5 V - VX because of the T/2 delay.
- **Status:** done. **Result:** 2.340903 V and 2.659089 V (0.04 % error) with a 20 us step. 5.6 % low without a maximum step. **Judge note (27 October 2026):** the conclusion that 20 us, 5 us and 2 us agree held only at four-digit precision. With eight digits, 20 us leaves a 0.036 % gain error (P-05 time-step check). **Grade:** A. Details in `ti-pspice-PSpiceFiles/LIA/README.md`. That README describes the earlier circuit. It is refreshed once the planned tests are graded.

### C-04 Differential amplifier, original AC sweep

- **Goal:** find why the AC output of the original schematic is zero.
- **Schematic:** `differential-amplifier/frequency_analysis`.
- **Parameters:** `.AC DEC 100 10 100k`.
- **Expected:** a band-pass peak of about 11 V/V near 520 Hz.
- **Status:** done. **Result:** output about 1e-17 V. Cause: the INA828 inputs have no DC path to ground and bias to -5.21 V. **Grade:** A. Details in `ti-pspice-PSpiceFiles/differential-amplifier/README.md`.

### C-05 Differential amplifier, corrected AC sweep

- **Goal:** measure the band-pass response once the input has a common-mode reference.
- **Schematic:** `circuits/diffamp_ac_fixed.cir` (100 kOhm from each input to ground).
- **Parameters:** `.AC DEC 100 10 100k`.
- **Expected:** peak 11.08 V/V (20.89 dB) at 520.7 Hz, -3 dB at 379 Hz and 715 Hz.
- **Status:** done. **Result:** 11.076 V/V at 524.8 Hz, -3 dB at 380.2 Hz and 708.0 Hz, within the 2.3 % sweep grid. **Grade:** A.

### C-06 Differential amplifier, corrected transient per frequency

- **Goal:** measure the output amplitude for a 15 mV input at several frequencies.
- **Schematic:** `circuits/diffamp_tran_fixed.cir`.
- **Parameters:** `.TRAN 0 25m 0`, `.STEP PARAM f LIST 50 300 500 518 550 800`. The 50 Hz case was rerun over 100 ms.
- **Expected:** 15 mV x |H(f)|, for example 166.2 mV at 518 Hz.
- **Status:** done. **Result:** within 0.1 % of the analytic values at every step. A 5 us maximum step gave the same values. **Grade:** A.

### C-07 LIA offset sweep (user GUI run)

- **Goal:** observe how the outputs change with the input DC offset.
- **Schematic:** `LIA/lia_sanity`, netlist of 26 October 2026, 20:56.
- **Parameters:** `.TRAN 0 2 0 20u SKIPBP`, `.STEP LIN PARAM ost -2 2 0.1`, p = 0, A = 2 V. All nodes saved.
- **Expected:** see P-03.
- **Status:** run by the user in the GUI. It took 8672 s. The result is archived in `archive/2026-10-26_lia_sanity_ost_sweep/`. The agents cannot read the binary `.dat`, so P-03 repeats this sweep with text output. **Grade:** not graded.

---

## Planned simulations

### P-01 Validation of the shorter run settings

- **Goal:** check that the default settings (1 s, `.IC` at 2.5 V, 20 us step) give the same settled values as a 2 s run from 0 V. If they do, every later test uses them.
- **Schematic:** `circuits/lia_baseline.cir`, a frozen copy of the LIA netlist of 26 October 2026, 20:56 (A = 2 V, no V7). It equals the current schematic with Vampl = 2 V and Vharm_ampl = 0.
- **Parameters:** run A: `.TRAN 0 2 0 20u SKIPBP` without `.IC`. Run B: the defaults. Both with p = 0 and ost = 0.
- **Expected:** VX = 2.5 - 1.2732 = 1.2268 V and VY = 2.5 - 1.2732 x sin(0.18 deg) = 2.4960 V in both runs. Runs A and B should agree within 0.1 mV. If `.IC` is ignored with SKIPBP, run B starts at 0 V and still settles to within 0.2 mV by 1 s. The dispatcher records which case occurs in the quirks file.
- **Status:** done, 27 October 2026.
- **Result:** Runs A and B agree within 0.1 mV after the `.IC` tail correction. The VY offset of +0.99 mV is explained by a 235 ns Y switching delay from the slew-limited demodulator, and VX stays +0.46 mV, an open point. See [sim-results/P-01.md](ti-pspice/docs/sim-results/P-01.md).
- **Grade:** A (judge, 27 October 2026). Both pass criteria met. The VY deviation is explained to 0.014 mV by measured switch and slew delays, and the 0.097 mV settling bias is derived independently. The VX deviation of +0.46 mV stays an open point, which is stated honestly.

### P-02 Input phase sweep

- **Goal:** verify that X and Y respond as cos and sin of the input phase over a full turn, and that the magnitude is independent of phase.
- **Schematic:** `circuits/lia_baseline.cir`.
- **Parameters:** defaults, ost = 0, `.STEP LIN PARAM p 0 360 15` (25 runs, about 20 min if one 1 s run takes about 45 s).
- **Expected:** VX = 2.5 - 1.2732 cos(p) and VY = 2.5 + 1.2732 sin(p - 0.18 deg). R = 1.2732 V at every step. The measured phase, atan2(VY - 2.5, 2.5 - VX), equals p - 0.18 deg. Pass limits: R within 0.5 %, phase within 1 deg.
- **Judge note from P-01:** at p = 0 the Y channel has an extra effective delay of about 235 ns (0.044 deg at 517 Hz). About 99 ns of it is op amp slew, which scales with the step at each edge, |4 V x sin(input phase at the edge)|. Each channel has this slew term, and it is largest when that channel switches near the input peaks. A delay makes the reference act later, so it reduces the Y lag: the phase at p = 0 is d - 0.044 deg (corrected by the judge after P-02, the first version of this note gave the wrong sign). The phase error is expected to vary with p by a few hundredths of a degree. The X channel shows the same effect near p = 90 deg. The analysis should fit and report this variation.
- **Status:** done, 27 October 2026.
- **Result:** R = 1.272742 V in both channels, 0.039 % below K, the same at every phase (spread 0.005 %). Both pass limits met: R within 0.2 % of K, and phase within 1 deg (0.23 deg of p - d, 0.05 deg of the ideal atan2 value). The residual shows a slew delay of the form sin p |sin p| (X) and cos p |cos p| (Y), with coefficient 0.48 mV against 0.41 mV predicted. The Y phase at p = 0 follows d - 0.044 deg, not d + 0.044 deg as the first judge note said. See [sim-results/P-02.md](ti-pspice/docs/sim-results/P-02.md).
- **Grade:** A (judge, 27 October 2026). Both pass criteria met at all 25 steps. The judge re-ran the script and got the same numbers, and checked VX at p = 90 deg (+0.98 mV) against the fitted phase and slew terms (+0.99 mV). The analyst correctly found the judge note's sign error. The command was reconstructed from the runner's circuit copy, and an unverified RON estimate was removed. The 0.039 % common gain deficit and the 17 % excess slew coefficient remain stated open points. Update: the gain deficit was later traced to the 20 us time step (P-05 time-step check, +0.007 mV at 2 us).

### P-03 Offset sweep and dynamic range

- **Goal:** find the input offset range over which the outputs stay correct, and describe the behaviour once the signal reaches the rails.
- **Schematic:** `circuits/lia_baseline.cir`.
- **Parameters:** defaults, p = 0, `.STEP LIN PARAM ost -2 2 0.1` (41 runs, about 30 min). A second, shorter sweep at p = 90 deg with ost -2 to 2 in steps of 0.25 checks the Y channel.
- **Expected:** the input spans vdc/2 + ost - 2 V to vdc/2 + ost + 2 V. It stays inside 0 V to 5 V while |ost| <= 0.5 V. In that range VX = 1.2268 V and VY = 2.4960 V, independent of ost. Beyond it, the op amps and the switch path clip, and VX moves towards 2.5 V. The analysis reports the ost value where VX departs from its flat value by more than 1 mV on each side. The analysis also plots `max(V(VX))` against ost next to the settled mean, for comparison with the GUI plot of C-07.
- **Status:** done, 27 October 2026.
- **Result:** VX and VY stay within 1 mV of their ost = 0 values for |ost| up to 0.5 V (P03a, VX and VY) and up to 0.5 V to 0.75 V (P03b, p = 90 deg). The steady demodulator output follows theory up to |ost| = 0.4 V, then sits on a floor (0.01 V to 0.02 V) or a ceiling (4.98 V to 4.99 V) from |ost| = 0.5 V. The output-stage swing is the limit the data show. Input-side limits are not separated. The absolute 50-period extremes come from reference-edge transients and are not the steady range. The 1f ripple of 3.92 mV per V of offset is derived and matches the measurement. Two asymmetries (VY at p = 0, VX at p = 90) stay open. See [sim-results/P-03.md](ti-pspice/docs/sim-results/P-03.md).
- **Grade:** A (judge, 27 October 2026, after one revision from B). The flat range of +/-0.5 V is met on both runs. Steady demodulator extremes now match theory within 10 mV, and the switching overshoots (0.37 V, under 1 us) are separated from them. The 1f ripple matches the derived 3.92 mV per V within 0.2 %, and the judge reproduced it. The limiting element (switch, op amp input or op amp output) and two small asymmetries stay open, because those nodes were not probed. The summary states what is missing.

### P-04 Dynamic range versus input amplitude

- **Goal:** check that VX - 2.5 V is proportional to the input amplitude, and find the largest amplitude before clipping.
- **Schematic:** `circuits/lia_v2.cir`, a frozen copy of the netlist of 27 October 2026, 14:38. In this netlist V4 is `SIN {Vdc/2+ost} {Vampl} {fin} 0 0 {p}`, V7 is `SIN 0 {Vharm_ampl} {f_osc*n_harm} 0 0 {p}` in series with V4, and the 2.5 V reference is V8 = `{Vref}`. The copy sets fin = 517 Hz and Vharm_ampl = 0, so it equals `lia_baseline.cir` at Vampl = 2 V.
- **Parameters:** defaults, p = 0, ost = 0, `.STEP PARAM Vampl LIST 0.01 0.03 0.1 0.3 1 1.5 2 2.25 2.5 2.75 3`.
- **Expected:** VX - 2.5 V = -(2/pi) x amp, for example -6.37 mV at 10 mV and -1.2732 V at 2 V. The response stays linear up to amp = 2.5 V, where the signal touches the rails. At small amplitudes, the switch charge injection and the op amp offset set the floor. The analysis reports that floor.
- **Status:** done, 27 October 2026.
- **Result:** VX - 2.5 V is linear with amplitude. The fitted offset is below 0.01 mV, and the 0.46 mV deviation at 2 V is a gain error of -0.037 %, not an offset. The VY channel has a square-law term of 0.114 mV/V^2, close to the slew prediction. The 0.97 mV VY error at 2 V is a constant lag of 0.0234 deg (126 ns) plus the slew part (111 ns), which sums to the 235 ns of P-01. The largest amplitude within 1 mV and 0.1 % is 2.5 V, and the first failure is at 2.75 V, where the demodulator floor clips. The upper edge drop is not closed (1.8 mV per V measured, 1.55 mV per V predicted). See [sim-results/P-04.md](ti-pspice/docs/sim-results/P-04.md).
- **Grade:** A (judge, 27 October 2026, after one revision from B). Linear to 2.5 V within 1 mV, failing at 2.75 V as predicted from the rails. The P-01 VX deviation is shown to be a 0.037 % gain error with an offset below 0.01 mV. The VY error at 2 V is split into the P-02 constant delay (126 ns) and the slew term (111 ns), which add to the 235 ns of P-01. The judge reproduced the fit. The 14 % excess in the upper-edge percentile drop stays an honest open point. It concerns the switching transients and has no effect on the settled outputs. Update: the 0.037 % gain error is the 20 us time step. At 2 us the VX deviation at 2 V is +0.007 mV (P-05 time-step check).

### P-05 Harmonic response using V7

- **Goal:** measure how the demodulator responds to harmonics of the input frequency.
- **Schematic:** `circuits/lia_v2_harm.cir` (as `lia_v2.cir` with Vharm_ampl = 0.2 V). V7 runs at `f_osc*n_harm` with phase `{p}`, so at p = 0 the harmonic starts at 0 deg, like the fundamental.
- **Parameters:** defaults, p = 0, ost = 0, Vharm_ampl = 0.2 V, `.STEP PARAM n_harm LIST 2 3 4 5 7`.
- **Expected:** a square-wave reference contains only odd harmonics, with weight 1/n. Each harmonic shifts the outputs by:
  - even n: delta VX = delta VY = 0. This is perfect rejection, limited only by duty-cycle and edge errors.
  - odd n: delta VX = -(2 Vharm_ampl / (n pi)) cos(p_h), with p_h = 0 here. For amp_h = 0.2 V that is 42.4 mV for n = 3, 25.5 mV for n = 5 and 18.2 mV for n = 7, at p_h = 0.
  - The rejection relative to an equal fundamental is therefore 1/n (-9.5 dB for n = 3) for odd harmonics. This is the known weakness of a switching lock-in. The test should confirm it. Signs of delta VY for odd n depend on the Y reference timing. The analysis derives them and states them before comparing.
- **Judge note (27 October 2026):** the first analysis found a VX deficit against theory of 0.35 %, 0.70 % and 2.0 % for n = 3, 5 and 7. This is close to (n x 2 pi f_osc x h)^2 / 12 with the maximum step h = 20 us, which gives 0.32 %, 0.88 % and 1.7 %. The same formula gives 0.035 % at the fundamental, close to the 0.037 % to 0.039 % gain deficit of P-01, P-02 and P-04. C-03 found no step dependence, but only with four-digit output. A time-step check follows: P05_step5u and P05_step2u (`lia_v2_harm.cir`, `.STEP PARAM n_harm LIST 2 3 7`, maximum step 5 us and 2 us), and P04_step5u and P04_step2u (`lia_v2.cir` at Vampl = 2 V). All other settings are as P-05. Expected: if the step is the cause, the deficit falls by 16 times at 5 us and 100 times at 2 us. The VY response to odd harmonics is set by the Y timing error, not by 1/n. The 1/n rule applies to VX only.
- **Status:** done, 27 October 2026.
- **Result:** at 2 us the VX deltas for n = 3 and 7 are -42.44 and -18.18 mV, against theory -42.44 and -18.19 mV. The VX loss of the 20 us run (0.31 % at n = 3) is the maximum-step error. The VX rejection follows 1/n within 0.01 dB, at -9.54 and -16.90 dB. VY deltas are +0.261 and +0.259 mV, within 0.01 mV of the timing plus slew theory (+0.25 mV). The +0.018 mV VX offset of the 20 us even run disappears at 2 us. VY does not follow 1/n, because the Y timing error gives the same error per volt for every odd n. The 20 us table is kept in the summary. See [sim-results/P-05.md](ti-pspice/docs/sim-results/P-05.md).
- **Grade:** A (judge, 27 October 2026, after the time-step check). At 2 us every check passes. VX follows 1/n within 0.04 %. VY odd-harmonic responses match the Y timing model within 0.01 mV. Even harmonics are rejected to below 0.01 mV. The analyst's open point on the growing VX deficit led to the time-step finding, which the 5 us and 2 us runs confirmed. It also explained the gain deficit of P-01 to P-04. The analyst correctly noted that VY moves by 0.015 mV with the step, against the judge's claim of no change. The convergence is slower than the h^2 model, probably because PSpice uses smaller steps near the switch edges. This and the residual of 0.001 to 0.004 mV stay stated open points. The judge reproduced the convergence table.

### P-06 Non-harmonic interference using V7

- **Goal:** check that an interferer at a frequency that is not a harmonic gives no DC error, only a filtered ripple.
- **Schematic:** as P-05.
- **Parameters:** defaults, Vharm_ampl = 0.2 V, `.STEP PARAM n_harm LIST 0.096711799 1.160541586` (50 Hz and 600 Hz).
- **Expected:** no change in the settled means beyond 0.1 mV. The ripple appears at |f_i - n f_osc| for odd n. For 50 Hz the main products are at 467 Hz and 567 Hz. Each has an amplitude of about (2/pi) x 0.2 V = 127 mV before the filter. The RC filter attenuates them to about 0.43 mV (at 467 Hz) and 0.36 mV (at 567 Hz). For 600 Hz the nearest product is at 83 Hz, giving about 2.4 mV of ripple.
- **Status:** done, 27 October 2026. **Result:** settled means change by at most 0.022 mV (limit 0.1 mV). The fitted amplitudes match the expected ones with ratios from 0.994 to 1.000, and the Y phases follow the 482.6 us reference delay. See [sim-results/P-06.md](ti-pspice/docs/sim-results/P-06.md).
- **Grade:** A (judge, 27 October 2026). Every expected item passes. The DC shifts are within 0.1 mV, and the 467 Hz, 567 Hz and 83 Hz products match theory within 0.1 %. The window residual is quantified, and the means are cross-checked with a least-squares fit. The judge reproduced the numbers. The remaining shifts of 0.02 mV and the 0.2 % to 0.6 % low ripple at 1 kHz are below the limits. They may come from the time step (see the P-05 judge note).

### P-07 Frequency mismatch (optional)

- **Goal:** show the output when the input frequency differs slightly from the reference.
- **Schematic:** `circuits/lia_v2_fin518.cir` (as `lia_v2.cir` with fin = 518 Hz). V4 is the input at Vampl = 2 V and 518 Hz. The references stay on `f_osc` = 517 Hz.
- **Parameters:** `.TRAN 0 3 0 20u SKIPBP`, no `.IC`, NUMDGT = 8.
- **Expected:** VX and VY beat at 1 Hz around 2.5 V. The amplitude is 1.2732 V x |H(1 Hz)| = 1.2732 V / sqrt(1 + (2 pi x 1 Hz x 0.1 s)^2) = 1.078 V. The beat is 90 deg out of phase between X and Y.
- **Status:** done, 27 October 2026.
- **Result:** beat amplitude 1.07765 V (VX) and 1.07764 V (VY), 0.041 % and 0.043 % below the ideal 1.07809 V and within 0.004 % of the calibrated model. Beat frequency 1.000 Hz within 3 ppm, X minus Y phase -89.82 deg as expected. The 1035 Hz ripple is 1.956 mV against 1.958 mV expected. The 0.035 % time-step error is visible at this precision. See [sim-results/P-07.md](ti-pspice/docs/sim-results/P-07.md).
- **Grade:** A (judge, 27 October 2026). Every expected item passes: the amplitude, the 1 Hz beat, the 90 deg X-Y phase, the 32.1 deg filter lag and the start transient. The analyst correctly found that at fin = 518 Hz the 2f ripple splits into 1035 Hz (1.958 mV) and 1033 Hz (0.654 mV) lines. In the 517 Hz case these merge into the 1.304 mV seen in P-01. The 0.04 % amplitude deficit matches the 20 us time-step error. The judge reproduced the fits. A 0.02 deg beat phase offset stays an open point.

### Batch 2: fault injection, full chain and front-end checks (requested 27 October 2026)

The user asked for nine further tests (P-09 to P-17). P-08 first validates the fast settings that most of them use. The new circuits are:

| Circuit | Content |
|---|---|
| `circuits/lia_v3_fast.cir` | `lia_v2.cir` with output capacitors `{cout}` (default 1 uF) and fault-injection parameters: `rser` (series resistance at the demodulator input), `dr1` (relative change of R1), `vos` (source in series with IN+ of U2 and U4), `aref`/`pref` (ripple on Vref), `kref` (0: ideal Vref, 1: Vref = V(VDC)/2 through an ideal buffer), `arail`/`prail` (ripple on the 5 V source), `rrail` (rail source resistance) and `iexc` (square excitation current drawn from the rail during the first half period, in phase with the X reference). Defaults reproduce `lia_v2.cir` apart from `cout`. |
| `circuits/chain_ss.cir` | Full chain on one 0 V to 5 V rail: sensor stand-in, INA828 (G = 11 V/V, REF = 2.5 V), Sallen-Key high-pass and low-pass with their ground returns moved to the 2.5 V reference, and the X/Y demodulator. Each INA828 input is biased to 2.5 V through 100 kOhm (DI-02). The sensor model is TBD (`simulations/design-context.md` section 1), so the stand-in is a floating differential source: sine `asin`, square `asq`, gated burst `aburst`, common mode `vcm`, DC differential `vdiff`, series resistance `rsens` per leg. |
| `circuits/frontend_mc.cir` | The front end of `chain_ss.cir` alone, with toleranced R and C models for a Monte Carlo AC run. |

Fast settings (used where an entry says "fast"):

| Setting | Value | Reason |
|---|---|---|
| Output capacitors | `cout` = 1 uF, so tau = 10 ms | Settling is most of the run time. The demodulator itself is unchanged. The 2f ripple grows 10 times, but the measurement is a whole-period mean. |
| Analysis | `.TRAN 0 0.15 0 5u SKIPBP` (`lia_v3_fast.cir`). `chain_ss.cir` runs without `SKIPBP`, so that the high-pass capacitors start from the bias point. | 15 tau. 5 us leaves a 0.003 % gain error at the fundamental (P-05 time-step check). |
| Initial conditions | `.IC V(VX)=2.5 V(VY)=2.5` | As the defaults. |
| Measurement window | Mean of the last 20 whole periods (38.68 ms at 517 Hz), from 111.3 ms | The settling bias of this mean is about abs(V - 2.5 V) x (tau / 38.68 ms) x exp(-11.13) = 3.8e-6 x abs(V - 2.5 V), so 4.8 uV at 2 V amplitude and below 0.5 uV at 0.2 V. Every fault test below is a difference against a baseline step of the same run, so this bias cancels further. |
| Signal level | Vampl = 0.2 V unless stated | Close to the Draft demodulator input of `simulations/design-context.md` section 4 (about 166 mV), as DI-09 recommends. Then 2A/pi = 127.324 mV. |
| Precision | `.OPTIONS NUMDGT=8` | Most expected effects are 0.05 mV to 2 mV. |

Setting a non-default parameter: PSpice allows one `.STEP` per run. Other non-default parameters are set by an edited copy of the circuit in the run folder or by `--extra ".PARAM ..."`. The dispatcher checks which works and records the result in `docs/simulation-quirks.md`.

### P-08 Validation of the fast settings

- **Goal:** confirm that the fast settings give the same settled VX and VY as the 1 s, 10 uF runs, so that P-09 to P-17 can use them.
- **Schematic:** `circuits/lia_v3_fast.cir`, all fault parameters at their defaults.
- **Parameters:** fast, p = 0, ost = 0, `.STEP PARAM Vampl LIST 0.2 2`. Probes V(VX), V(VY).
- **Expected:** at Vampl = 2 V the reference is P04_step5u (same 5 us step, 10 uF, 1 s): VX = 1.2268012 V and VY = 2.4969886 V ([sim-results/P-05.md](ti-pspice/docs/sim-results/P-05.md)). The fast run should agree within 0.02 mV in both channels. At 0.2 V, VX - 2.5 V = -127.324 mV within 0.01 mV, and VY - 2.5 V is close to -0.40 mV (the 0.18 deg Y timing error) plus a slew term that scales with A^2 and is below 0.01 mV here. The 2f ripple at VX is about 10 times the 1.3 mV of P-01 at 2 V, so about 13 mV peak. Pass: both channels within 0.02 mV of the reference at 2 V, and a measured settling bias of the window below 0.005 mV (compare the last 20 periods with the 20 periods before them, scaled by exp(-38.68 ms / tau)).
- **Status:** done, 27 October 2026.
- **Result:** at 2 V the fast VX and VY agree with the reference within 0.015 mV and 0.001 mV (corrected means). The 2 V settling bias is 4.7 uV. At 0.2 V, VX - 2.5 V = -127.3248 mV (0.001 mV from ideal). VY - 2.5 V = -0.344 mV, which is 0.053 mV above the -0.40 mV expected here. The expectation omitted the 126 ns lag and the slew term. With them, the model gives -0.340 mV (0.004 mV residual). The 2f VX ripple is 1.31 mV at 0.2 V and 13.06 mV at 2 V, so the 13 mV expectation holds only at 2 V. See [sim-results/P-08.md](ti-pspice/docs/sim-results/P-08.md).
- **Grade:** A (judge, 27 October 2026). Every pass criterion is met: 2 V agreement within 0.015 mV and 0.001 mV, and a 4.7 uV settling bias. The judge re-ran the script and got the same numbers. The two "fail as written" lines are errors of the entry, not of the run. The judge's VY expectation omitted the P-04 lag and slew terms, and the 13 mV ripple was the 2 V value. With the P-04 model, VY at 0.2 V agrees within 0.004 mV. The fast settings are accepted for P-09 to P-17. The 0.024 mV VY model residual at 2 V (mostly the 20 us origin of the P-04 constants) stays an open point.

### P-09 Full chain on a single 5 V rail

- **Goal:** run the sensor stand-in through the INA828, both filters and the demodulator on one 0 V to 5 V rail. Check the INA828 input and output against its supply limits and check that its inputs sit at 2.5 V.
- **Schematic:** `circuits/chain_ss.cir`, asin = 15 mV (the C-06 level, Draft in `simulations/design-context.md` section 4), rsens = 1 mOhm, vcm = 2.5 V.
- **Parameters:** run P09a: fast, `.TRAN 0 0.15 0 5u` (bias point on), `.STEP PARAM p LIST 0 90`. Probes V(INP), V(INN), V(VDIFF), V(HPF), V(VSAMPLE), V(VX), V(VY). Run P09b: `.DC LIN PARAM vcm 0 5 0.02` with vdiff = 10 mV and asin = 0, probes V(VDIFF), V(HPF), V(INP). P09b finds the common-mode range of the INA828 model on this supply.
- **Expected:** the ideal front-end transfer function of `ti-pspice-PSpiceFiles/differential-amplifier/README.md` section 3 gives |H(517 Hz)| = 11.079 V/V and a phase of +1.63 deg. Its phase slope is -0.442 deg/Hz. P09a:
  - DC level of INP and INN: 2.5 V within 1 mV (the INA828 bias current times 100 kOhm). VDIFF, HPF and VSAMPLE DC levels: 2.5 V within 5 mV (op amp and INA828 offsets). VSAMPLE amplitude 15 mV x 11.079 = 166.19 mV within 0.5 %.
  - The INA828 output swing is +/-166 mV around 2.5 V, far inside the rails. The INA828 input common mode is 2.5 V, which leaves about 0.5 V to the limits quoted in DI-02 (about 2 V from each rail, to be confirmed by P09b and the reviewer).
  - At p = 0: VX - 2.5 V = -(2/pi) x 166.19 mV x cos(1.63 deg) = -105.76 mV, and VY - 2.5 V = +3.01 mV minus the Y timing term (0.18 deg x 105.8 mV = 0.33 mV). At p = 90 deg: VX - 2.5 V close to +3.0 mV and VY - 2.5 V close to +105.76 mV. R = 105.80 mV at both phases. Pass limits: R within 0.5 % of 105.80 mV, and the measured front-end phase within 0.5 deg of +1.63 deg after the Y timing correction. The INA828 and op amp bandwidths are not in the ideal model. The analyst reports their extra phase.
  - P09b: VDIFF stays at 2.5 V + 110 mV (11 x 10 mV) within 1 mV over a common-mode window. The analyst reports the vcm range where it holds within 1 mV and compares it with DI-02. If the model does not limit the common mode at all, the analyst says so, because then the simulation cannot show the DI-02 risk.
- **Status:** done, 27 October 2026.
- **Result:** front-end gain 11.073 V/V (-0.055 % against 11.079 V/V) and phase +1.50 deg (-0.13 deg against +1.63 deg). R = 105.73 mV at p = 0 deg and 105.74 mV at p = 90 deg, -0.06 % against 105.80 mV, pass. The last-window settling bias is 0.45 uV, so the run is settled. The dispatcher's 2.402 V is a whole-run mean. The VDIFF value stays within 1 mV of 2.61 V for vcm from 2.02 V to 2.98 V, with clamp edges at 2.00 V and 3.00 V (consistent with DI-02, datasheet not verified). See [sim-results/P-09.md](ti-pspice/docs/sim-results/P-09.md).
- **Grade:** A (judge, 27 October 2026). Every stated criterion passes: input bias 2.5 V, stage offsets below 0.25 mV, amplitude -0.055 %, R -0.06 % and phase -0.13 deg (limit 0.5 deg). The judge re-ran the script and confirmed that the dispatcher's 2.402 V was a whole-run mean, not a settling problem. The INA828 model clamps the input common mode at 2 V from each rail. On 5 V this leaves 2.0 V to 3.0 V, so the 2.5 V bias has 0.5 V of margin on each side, and the DI-02 risk is visible in simulation. The 0.055 % gain and 0.13 deg phase deficit against the ideal filters are localised by stage, but their cause is not identified (not verified against the amplifier bandwidths). This stays an open point.

### P-10 Coherent pickup on the reference and the rail

- **Goal:** measure the DC error from a ripple at f_osc on Vref, on the 5 V rail, and from an excitation current that loads the rail (DI-04).
- **Schematic:** `circuits/lia_v3_fast.cir`, Vampl = 0.2 V, ost = 0, p = 0.
- **Parameters:** fast. Each run steps its own baseline. Probes V(VX), V(VY), V(REF), V(VDC).

  | Run | Fixed settings | `.STEP` |
  |---|---|---|
  | P10a0, P10a90 | kref = 0, pref = 0 or 90 | `PARAM aref LIST 0 1m` |
  | P10b | kref = 0, prail = 0 | `PARAM arail LIST 0 1m` |
  | P10c | kref = 1, prail = 0 | `PARAM arail LIST 0 1m` |
  | P10d | kref = 0, rrail = 1 Ohm | `PARAM iexc LIST 0 10m` |
  | P10e | kref = 1, rrail = 1 Ohm | `PARAM iexc LIST 0 10m` |

  The rail resistance (1 Ohm) and excitation current (10 mA) are test values. The real ones are TBD (`simulations/design-context.md` section 1).
- **Expected:** the demodulator output is Vin in the +1 state and 2 Vref - Vin in the -1 state. The X -1 state is the first half period, and the Y -1 state runs from T/4 to 3T/4. A Vref ripple a sin(wt + pref) therefore adds 2a sin(wt + pref) in the -1 state only. The readout is VX and VY relative to the mean of Vref.

  | Run | Expected delta VX | Expected delta VY |
  |---|---|---|
  | P10a0 | +(2/pi) a = +0.6366 mV | below 0.005 mV |
  | P10a90 | below 0.005 mV | -(2/pi) a = -0.6366 mV |
  | P10b | below 0.005 mV (op amp PSRR only, input and Vref ideal) | below 0.005 mV |
  | P10c | Vref ripple 0.5 mV, so +0.3183 mV | below 0.005 mV |
  | P10d | below 0.005 mV | below 0.005 mV |
  | P10e | Vref falls by 5 mV in the first half. Absolute VX shift -5.000 mV, mean Vref shift -2.500 mV, so -2.500 mV relative to Vref | Absolute -2.500 mV, relative 0 |

  Pass: each delta within 0.01 mV or 3 % of the expected value, whichever is larger. P10b and P10d also give the size of the rail coupling through the op amps and the switch model, which the analyst reports.
- **Status:** done, 27 October 2026.
- **Result:** all 15 checks pass. The reference responses are +0.6366 mV (aref, pref = 0) and -0.6363 mV (pref = 90 deg), and +0.3183 mV with kref = 1. The 10 mA rail step gives -2.5001 mV in the readout of VX. The absolute VY shift is -2.5058 mV, which the Y reference delay of 482.6 us explains. A 1 mV rail ripple couples at 2.6e-4 V/V (-72 dB) into VY and 8.9e-6 V/V (-101 dB) into VX. See [sim-results/P-10.md](ti-pspice/docs/sim-results/P-10.md).
- **Grade:** A (judge, 27 October 2026). All 15 checks pass, relative to the mean of V(REF) as defined. The judge re-ran the script. A 1 mV Vref ripple at f_osc gives 0.637 mV of DC error, the full (2/pi) weight. Rail ripple with an ideal reference couples below 0.0003 mV. A reference derived from the rail carries half of it. The entry's P10e VY expectation (0 relative, -2.500 mV absolute) ignored the 482.6 us Y delay. The analyst derived the correct -0.005 mV and -2.505 mV, which match. The entry mixed two limits (0.01 mV and below 0.005 mV). Both hold.



### P-11 Resistor mismatch with input offset

- **Goal:** measure the DC and scale error from a mismatch of R1 against R2 in the X channel (DI-05).
- **Schematic:** `circuits/lia_v3_fast.cir`, Vampl = 0.2 V, p = 0.
- **Parameters:** fast. Run P11p with ost = +0.3 V and run P11m with ost = -0.3 V, each with `.STEP PARAM dr1 LIST -10m -1m 0 1m 10m` (sorted, see the quirk on `.STEP LIST`). Probes V(VX), V(VY).
- **Expected:** with R1 = R2 (1 + delta), the -1 state output is Vref - (1 + delta)(Vin - Vref). Averaging over a period gives delta VX = -(delta / 2) x ost - (delta / 2) x (2A/pi), with 2A/pi = 127.324 mV. VY does not change.

  | delta | ost = +0.3 V | ost = -0.3 V |
  |---|---|---|
  | +0.1 % | -0.2137 mV | +0.0863 mV |
  | -0.1 % | +0.2137 mV | -0.0863 mV |
  | +1 % | -2.1366 mV | +0.8634 mV |
  | -1 % | +2.1366 mV | -0.8634 mV |

  The input spans 2.5 V + 0.3 V +/- 0.2 V, inside the flat range of P-03. Pass: each delta within 0.005 mV or 1 % of the table, whichever is larger, and delta VY below 0.005 mV.
- **Status:** done, 27 October 2026.
- **Result:** all eight VX deltas pass (largest difference 0.0004 mV at dr1 = +1 %), and delta VY stays below 0.0002 mV. The VX offset term of -0.153 mV/V at dr1 = 0 is a timing effect of the test bench and the switch model (100 ns reference duty offset and 46 ns switch delay asymmetry). It is not the op amp or the switch on-resistance. It changes the deltas by at most 0.0008 mV. See [sim-results/P-11.md](ti-pspice/docs/sim-results/P-11.md).
- **Grade:** A (judge, 27 October 2026). All 16 deltas pass within 0.0005 mV of (delta/2)(ost + 2A/pi). The judge re-ran the script. The analyst explained the extra -0.153 mV per V of ost at dr1 = 0 with diagnostic runs: -0.103 mV/V from the reference duty (the PULSE width is counted after the 100 ns rise, so the -1 state lasts T/2 + 100 ns, which the judge checked: -2 x 100 ns / T = -0.103 mV/V) and -0.048 mV/V from unequal switch delays (41 ns and 87.5 ns) in the behavioural switch model. It does not affect the mismatch deltas. It also explains most of the P-03 offset slope (-0.148 mV/V).

### P-12 Driver output impedance at the demodulator input

- **Goal:** measure the gain and phase error when the demodulator input node is driven through a series resistance (DI-06).
- **Schematic:** `circuits/lia_v3_fast.cir`, Vampl = 0.2 V, ost = 0, p = 0.
- **Parameters:** fast, `.STEP PARAM rser LIST 1m 10 100 1k`. Probes V(VX), V(VY), V(N00890).
- **Expected:** a channel draws current only in its -1 state, (Vnode - Vref) / 10 kOhm through R2 or R4. With eps = rser / 10 kOhm, the node gain is g1 = 1 / (1 + eps) when one channel is in the -1 state and g2 = 1 / (1 + 2 eps) when both are. Over the four quarter periods this gives VX - 2.5 V = -(A / 2pi)(1 + 2 g1 + g2) and VY - 2.5 V = (A / 2pi)(2 g1 - g2 - 1). Relative to the rser = 1 mOhm step:

  | rser | delta VX | delta VY | X gain error |
  |---|---|---|---|
  | 10 Ohm | +0.1275 mV | below 0.001 mV | -0.100 % |
  | 100 Ohm | +1.2544 mV | -0.0062 mV | -0.985 % |
  | 1 kOhm | +11.091 mV | -0.482 mV | -8.71 % |

  The node voltage V(N00890) should show steps of eps or 2 eps times (Vin - Vref) at the quarter-period boundaries. Pass: deltas within 2 % of the table or 0.005 mV, whichever is larger.
- **Status:** done, 27 October 2026.
- **Result:** VX deltas and gain errors match theory. VY at 1 kOhm is -0.458 mV, against -0.482 mV in the entry, because the entry omits the Y edge delay. With the 235 ns delay of P-01 the theory gives -0.456 mV. Node steps are eps (Vin - Vref) at the Y edges only. See [sim-results/P-12.md](ti-pspice/docs/sim-results/P-12.md).
- **Grade:** A (judge, 27 October 2026). Every X delta and gain error matches the exact theory within 0.002 mV (-0.0998 %, -0.985 %, -8.71 %). The judge re-ran the script and got the same numbers. The VY value at 1 kOhm fails the entry as written (-0.458 mV against -0.482 mV), but the entry omitted the Y timing error. With the 235 ns Y delay the exact theory gives -0.456 mV. The "2 eps" node step in the entry was wrong: the node gain is 1/(1 + 2 eps) when both channels are in the -1 state, but a visible step occurs only at the Y edges, because the X edges fall at zero input. The analyst found both entry errors. Note for the reviewer: 10 Ohm already reaches the 0.1 % Draft major threshold.

### P-13 Op amp offset

- **Goal:** confirm that an offset at the non-inverting input of the demodulator op amp appears doubled at the output.
- **Schematic:** `circuits/lia_v3_fast.cir`, Vampl = 0.2 V, ost = 0, p = 0. The source `vos` is in series with IN+ of both U2 and U4.
- **Parameters:** fast, `.STEP PARAM vos LIST -25u 0 25u` (sorted, because the order `0 25u -25u` was rejected, see the `.STEP LIST` quirk in `docs/simulation-quirks.md`). Probes V(VX), V(VY).
- **Expected:** the output is (1 + R1/R2)(V+ + vos) - (R1/R2) Vin in both states, so the offset adds 2 vos. Delta VX = delta VY = +50 uV at vos = 25 uV and -50 uV at -25 uV. Pass: within 2 uV. The analyst also reports the offset already present at vos = 0 (the model's own offset), from the residual against theory.
- **Status:** done, 27 October 2026.
- **Result:** the shift is -2 vos in both channels, so the magnitude matches 2 vos within 0.16 uV (limit 2 uV). The entry's +2 vos sign does not match the netlist orientation. Model offset at vos = 0: -0.89 uV in VX and -3.95 uV in VY against the P-08 model. See [sim-results/P-13.md](ti-pspice/docs/sim-results/P-13.md).
- **Grade:** A (judge, 27 October 2026). The magnitude is 2 |vos| within 0.16 uV in both channels. The sign is reversed against the entry because the test source V_VOSX N00695 N00695P {vos} puts IN+ at the switch output minus vos. This is an error of the judge's fixture orientation, not of the circuit. The physics (gain 2 from IN+ to the output in both states) is confirmed. The judge re-ran the script. The model's own offset is below 2 uV input-referred in both channels.

### P-14 Filter tolerance Monte Carlo

- **Goal:** find the spread of the front-end phase and gain at f_osc for given component tolerances, and compare the error of reading X alone with the error of reading R (DI-08).
- **Schematic:** `circuits/frontend_mc.cir`. Resistors 1 % and capacitors 5 %, uniform. These are test values. The tolerances are TBD in `simulations/design-context.md` section 6.
- **Parameters:** `.AC LIN 1 517 517`, `.MC 500 AC VP([VSAMPLE]) YMAX OUTPUT ALL SEED=17`, `.OPTIONS NUMDGT=8`, run P14_mc2 (1638 s). The run gives 499 random samples (Pass 2 to Pass 500) plus the nominal section. Both CSDF columns hold the complex V(VSAMPLE), so VP and VM are derived from it (deg and V/V).
- **Expected:** a numpy Monte Carlo of the ideal transfer function (200 000 samples, same tolerances, RG included) gives:

  | Quantity | Mean | Std | 2.5 % to 97.5 % |
  |---|---|---|---|
  | Phase shift from nominal | +0.10 deg | 3.36 deg | -6.40 deg to +6.67 deg |
  | Gain error, R | -0.13 % | 3.59 % | -6.86 % to +6.77 % |
  | Gain error, X alone (phase not corrected) | -0.30 % | 3.60 % | -6.97 % to +6.69 % |
  | Extra error of X over R | -0.17 % | 0.23 % | -0.82 % to 0 % |

  The nominal run should give |H| = 11.079 V/V and +1.63 deg (P-09). With 500 runs the sampled standard deviation has a relative uncertainty of about 3 %, so the PSpice phase std should fall in 3.1 deg to 3.6 deg. The analyst stores the numpy script in `simulations/ti-pspice/docs/sim-results/scripts/P-14_mc.py`. Pass: phase std and gain std within those bands. The analyst states that the gain spread affects X and R equally, and that computing R removes only the extra X error.
- **Status:** done, 27 October 2026.
- **Result:** 499 samples. Phase std 3.443 deg (band 3.1 to 3.6 deg, pass). Gain std 3.617 % (R) and 3.635 % (X), both in the 3.48 % to 3.70 % band, pass. Nominal 11.0732 V/V and +1.518 deg, 0.055 % and 0.11 deg below the ideal values, the same offset as P-09. With the entry's definition (phase calibrated at nominal) the extra X rows agree within 2 standard errors: PSpice -0.180 % (mean), 0.246 % (std), -0.884 % (2.5 %) against entry -0.17 %, 0.23 %, -0.82 %, and numpy reproduces the entry. A total-phase reading (not calibrated) gives about 0.04 % more negative values. See [sim-results/P-14.md](ti-pspice/docs/sim-results/P-14.md).
- **Grade:** A (judge, 27 October 2026, after one revision from B). Phase std 3.44 deg and gain std 3.62 % are inside their bands. With the entry's definition (phase calibrated at the nominal circuit), the extra X error of -0.180 % mean, 0.246 % std and -0.88 % at 2.5 % matches the reference within 2 standard errors. The judge recomputed these from the CSDF. The first version used the uncalibrated total phase and wrongly called the entry inconsistent. That reading is kept as a secondary row. The run has 499 random samples plus the nominal. The nominal offset (-0.055 %, -0.11 deg) is the same as in P-09 and stays open. For the reviewer: about 76 % of samples are beyond the Draft 1 deg phase limit.

### P-15 Noise floor of the front end

- **Goal:** find the output noise density of the front end at f_osc and the smallest sensor amplitude the lock-in resolves.
- **Schematic:** `circuits/chain_ss.cir` with acmag = 1 (AC differential input of 1 V on V_SIN) and asin = 0.
- **Parameters:** `circuits/chain_ss_P15.cir` with acmag = 1 V and asin = 0. The run has cout = 1 uF, so its RC is tau = 10 ms, not 0.1 s. Runs P15a_noise517c (`.AC LIN 1 517 517`) and P15b_noise_dec (`.AC DEC 50 10 100k`, 201 points), each with `.NOISE V([VSAMPLE]) V_SIN 1` (the print interval 1 is needed for the tables), `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5` and probe `V([VSAMPLE])`. The noise tables are in the `.out` files, not in the `.csd`.
- **Expected:** the demodulator multiplies by a +/-1 square wave, which folds the noise at each odd harmonic n f_osc to DC with weight (4 / (n pi))^2 / 2. The band-pass makes the harmonic terms small (|H(3 f_osc)| = 1.39 V/V against 11.08 V/V), so the DC density at VX is about 0.90 x e_out(517 Hz). The analyst computes the exact factor from the AC sweep. The output RC has an equivalent noise bandwidth 1 / (4 tau) = 2.5 Hz for tau = 0.1 s (`simulations/design-context.md` section 5). For SNR = 1 the smallest input amplitude is A_min = (pi / 2) x 0.90 x e_out x sqrt(2.5 Hz) / 11.08 V/V, which is about 0.20 x e_out (A_min in V for e_out in V/sqrt(Hz)). The datasheet noise of the INA828 and OPAx192 is not recorded in the project. The analyst compares the .NOISE contributions with the datasheet values and cites them. The demodulator and its 10 kOhm resistors cannot be included in `.NOISE`, because the switches change state. The analyst estimates their noise from datasheet values and states that the estimate is not simulated.
- **Status:** done, 27 October 2026.
- **Result:** fold-down factor 0.9014 (index 0.90). A_min for SNR = 1 is 28.4 nV at 2.5 Hz and 89.8 nV at 25 Hz (front end only). Input-referred noise 12.68 nV/sqrt(Hz). R_R16 gives 8.28 nV/sqrt(Hz), 0.91 of its 4kTR, not exactly 1:1. INA828 datasheet and demodulator values not verified. See [sim-results/P-15.md](ti-pspice/docs/sim-results/P-15.md).
- **Grade:** A (judge, 27 October 2026). The exact fold-down factor (0.901) and A_min = 28.4 nV for tau = 0.1 s agree with the entry's formula within 0.25 %. The judge re-ran the script. The judge checked the datasheet values on the TI product pages: INA828 7 nV/sqrt(Hz) and OPA192 5.5 nV/sqrt(Hz). The analyst had recalled 4.5 nV/sqrt(Hz), which a judge note in the summary corrects. The effect on A_min is below 1 %. Main finding: the 5 kOhm gain resistor gives 42.6 % of the output noise power, so a higher in-amp gain lowers the floor. The demodulator noise is an estimate, not simulated.

### P-16 Overload recovery

- **Goal:** measure how long the chain takes to return to within 1 mV after an input burst that drives the INA828 beyond the rails.
- **Schematic:** `circuits/chain_ss.cir`, asin = 15 mV, burst at f_osc of 10 periods (19.34 ms) starting at 50 periods (96.71 ms).
- **Parameters:** fast, `.TRAN 0 0.3 0 2u` (run P16_2u; the 5 us runs P16_overload and P16_gear failed to converge, see `docs/simulation-quirks.md`), `.STEP PARAM aburst LIST 0 0.5`, asin = 15 mV, cout = 1 uF (tau = 10 ms in the run, not 0.1 s), `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`. With 0.5 V differential the INA828 would need +/-5.5 V around 2.5 V, so it clips at both rails. Probes V(VDIFF), V(HPF), V(VSAMPLE), V(VX), V(VY).
- **Expected:** the aburst = 0 step is the reference waveform. Recovery is measured from the end of the burst (116.05 ms) as the time after which the difference from the reference stays below 1 mV.
  - VSAMPLE: each Sallen-Key stage has a Q of about 1, so its envelope decays with a time constant of about Q / (pi f0) = 0.6 ms. From a 2.5 V overload to 1 mV takes about 0.6 ms x ln(2500) = 4.7 ms per stage. A recovery time below 10 ms is expected. A longer time means saturation memory (a coupling capacitor charged during clipping), which the analyst identifies from V(HPF) and V(VDIFF).
  - VX and VY: once VSAMPLE has recovered at time t_VS, the outputs decay as exp(-t / tau). With dV the difference from the reference at t_VS, the recovery time is t_VS + tau x ln(dV / 1 mV). The analyst checks that the measured time matches this within 10 %, and scales the result to tau = 0.1 s (10 times the RC part).
- **Status:** done, 27 October 2026.
- **Result:** VSAMPLE recovers 6.21 ms after the burst (limit 10 ms). VX and VY agree with t_VS + tau ln(dV/1 mV) within 0.05 %, with tau = 10 ms as run. No saturation memory beyond the ms-scale filter time constants. The value scaled to tau = 0.1 s (662 ms) is not simulated. See [sim-results/P-16.md](ti-pspice/docs/sim-results/P-16.md).
- **Grade:** A (judge, 27 October 2026). VSAMPLE recovers in 6.2 ms (expected below 10 ms). VX and VY match t_VS + tau ln(dV/1 mV) within 0.05 %, and no saturation memory is found. The judge re-ran the script. The run used tau = 10 ms. The 0.66 s recovery for tau = 0.1 s is an arithmetic scaling, not a simulation, and the analyst says so. The recovery requirement and the overload level are TBD.

### P-17 Square-wave excitation through the band-pass

- **Goal:** check the calibration when the sensor signal is a square wave, whose harmonics pass the band-pass with a different gain and phase.
- **Schematic:** `circuits/chain_ss.cir`, asin = 0, asq = 15 mV (a square of +/-15 mV differential, high in the first half period).
- **Parameters:** fast, `.TRAN 0 0.15 0 2u` (2 us, because harmonics up to the 7th matter, see `docs/simulation-quirks.md`). A second run with asin = 15 mV and asq = 0 at the same step gives the sine calibration. Probes V(VSAMPLE), V(VX), V(VY).
- **Expected:** a square of amplitude A has harmonics (4A / (n pi)) sin(n w t), and the square reference weighs harmonic n by 2 / (n pi). With H(f) the ideal front end, VX - 2.5 V = -(8 A / pi^2) x sum over odd n of |H(n f)| cos(phi_n) / n^2, and VY - 2.5 V = (8 A / pi^2) x sum of s_n |H(n f)| sin(phi_n) / n^2 with s_n = +1 for n = 1, 5, 9 and -1 for n = 3, 7, 11. Numerically (n up to 399): VX - 2.5 V = -132.94 mV, VY - 2.5 V = +5.00 mV and R = 133.03 mV. The fundamental alone gives -134.65 mV. The harmonics therefore lower X by 1.27 %, mostly through n = 3 (|H| = 1.39 V/V, phase -138.5 deg). A calibration that treats the square as its fundamental is off by -1.27 %, which is above the 0.1 % major error threshold (Draft, `simulations/design-context.md` section 7). The predicted ratio of the square response to the sine response is (4/pi) x 0.98725 = 1.2570. The Y timing error and the INA828 and op amp bandwidths shift these values slightly. Pass: VX within 0.5 % of -132.94 mV, and the measured ratio within 0.2 % of 1.2570.
- **Status:** done, 27 October 2026.
- **Result:** square/sine VX ratio 1.25700 against 1.2570 (ideal 1.25701), pass. Square VX = -132.872 mV, +0.049 % against -132.94 mV, pass. X shift -1.276 % from the fundamental, above the 0.1 % major threshold. Square VY = +4.326 mV against the entry's +5.00 mV, because the 482.6 us Y timing gives -0.43 mV (ideal 4.570 mV). See [sim-results/P-17.md](ti-pspice/docs/sim-results/P-17.md).
- **Grade:** A (judge, 27 October 2026). The square/sine ratio matches 1.2570 to 0.001 %, and square VX is within 0.05 % of the prediction. A calibration that treats the square as its fundamental is therefore 1.28 % off, which is above the Draft 0.1 % major threshold. The judge re-ran the script. The entry's VY of +5.00 mV assumed a Y reference at exactly T/4. With the 482.6 us delay the ideal is +4.57 mV. The remaining -0.24 mV is mostly the -0.13 deg front-end phase deficit found in P-09. A +0.058 mV VY excess above n = 7 stays an open point.

### Batch 3: tests proposed by the batch-2 design review

Entries P-18 to P-22 (deprecated on 7 November 2026, see Batch 4) are the tests R-01 to R-05 of [design-review/2026-10-27_batch2.md](design-review/2026-10-27_batch2.md), taken over by the judge on 27 October 2026 with the reviewer's expected values. Circuit names were renamed from R-0n to the P numbers. P-21 also depends on the switch decision of DI-01 and uses assumed TMUX1136 parameters (CS = 10 pF is not from the datasheet).

### P-18 Sensor source impedance, gain loading and noise

- **Goal:** measure the gain and the input-referred noise of the chain when the sensor has a series resistance, with the 100 kOhm bias resistors in place (DI-11).
- **Schematic:** `circuits/chain_ss_P15.cir` (acmag = 1 V, asin = 0). Source resistance is the existing parameter `rsens` (resistors `R_SP` and `R_SN`).
- **Parameters:** `.AC LIN 1 517 517`, `.NOISE V([VSAMPLE]) V_SIN 1`, `.STEP PARAM rsens LIST 1m 100 1k 10k 100k`, `.OPTIONS NUMDGT=8`, probe `V([VSAMPLE])`. The noise tables are in the `.out` file. One run, five steps.
- **Expected:** with 100 kOhm from each input to VREF, the gain from the source EMF to VSAMPLE is 11.0732 V/V (P-14 nominal) times 200 kOhm / (200 kOhm + 2 rsens). The input-referred density relative to V_SIN is sqrt(12.68^2 + 2 x 4kT (Rs || 100 kOhm) + 2 x (0.17 pA x (Rs || 100 kOhm))^2) divided by the loading factor. The current-noise term is below 2.2 nV/sqrt(Hz) up to 10 kOhm.

  | rsens | Gain (V/V) | Loading | Input-referred noise (nV/sqrt(Hz)) | A_min, tau = 0.1 s (nV) |
  |---|---|---|---|---|
  | 1 mOhm | 11.0732 | 1.0000 | 12.68 | 28.4 |
  | 100 Ohm | 11.0621 | 0.9990 | 12.82 | 28.7 |
  | 1 kOhm | 10.964 | 0.9901 | 14.06 | 31.5 |
  | 10 kOhm | 10.067 | 0.9091 | 23.77 | 53.2 |
  | 100 kOhm | 5.537 | 0.5000 | 88.6 | 198 |

  Pass: gain within 0.2 % of the table and noise within 5 %. The noise of the INA828 model for the current-noise term is not known, so the analyst reports the 1 kOhm and 10 kOhm rows against the table and states the difference. A_min uses fold = 0.9014 from P-15 for every row. The Thevenin noise of Rs is added without correlation.
- **Status:** deprecated, 7 November 2026. Not required for LIA-AFE-Eval: single-rail chain with 100 kOhm bias resistors. On LIA-AFE-Eval the drains are fed through R_D = 330 kOhm and the sensor loading and noise are in P-29 and P-30.

### P-19 Reference tracking with a shared reference node

- **Goal:** show that a ripple at f_osc on one shared reference node (INA828 REF, filter returns, demodulator reference) produces no DC error, and measure the tracking error that is left (DI-04).
- **Schematic:** `circuits/chain_ss_P19.cir`, a copy of `chain_ss.cir` in which `V_VREF VREF 0 {vref}` is replaced by `V_VREF0 VREF0 0 {vref}` and `V_RIP VREF VREF0 SIN(0 {aref} {f_osc} 0 0 {pref}) AC 1`, and the parameters `aref=0 pref=0` are added to the `.PARAM` line. acmag = 0, asin = 15 mV (Draft level).
- **Parameters:**
  - Run P19a (linear): `.AC LIN 1 517 517`, probes `V([VSAMPLE])`, `V([VREF])`, `V([VDIFF])`, `V([HPF])`. `V_SIN` AC magnitude 0 (`acmag` = 0).
  - Run P19b (confirmation): fast, `.TRAN 0 0.15 0 5u`, `.STEP PARAM aref LIST 0 1m` with pref = 0, then a second run with pref = 90 deg. Probes `V([VX])`, `V([VY])`, `V([VREF])`, `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`. Readout = VX and VY minus the mean of V(VREF) over the last 20 periods (as P-10).
- **Expected:**
  - Derivation. The in-amp, both filters and the demodulator are referenced to one node, so the demodulator input is Vref + s and the output is Vref +/- s. A ripple a on Vref leaves no DC term. The nodal solution with ideal op amps gives V(VSAMPLE) - V(VREF) = Vd x 11.0793 /1.6300 deg whatever the reference resistance (`simulations/design-review/scripts/batch2_calc6.py`). The finite loop gain of the followers (Aol at 517 Hz is 10 MHz / 517 Hz = 19 300) and the INA828 bandwidth (640 kHz at G = 10, a lag of 0.046 deg = 8.1e-4 rad) leave a tracking error of the order of 1e-3.
  - P19a: V(VSAMPLE) - V(VREF) for a 1 V AC ripple is below 2e-3 in magnitude. (For comparison, an isolated demodulator reference would give 1.) Pass: below 2e-3.
  - P19b: delta VX (pref = 0) and delta VY (pref = 90 deg) relative to mean Vref are below 0.005 mV for a 1 mV ripple. The separate-reference result of P-10 is 0.6366 mV, so the improvement factor is at least 127. Pass: both below 0.005 mV, and the ratio to 0.6366 mV is reported.
  - If P19a gives more than 2e-3, the analyst identifies the stage (V(VDIFF) - V(VREF), V(HPF) - V(VREF), V(VSAMPLE) - V(VREF)).
- **Status:** deprecated, 7 November 2026. Not required for LIA-AFE-Eval: the board has no 2.5 V reference node. The in-amp REF, the filter returns and the demodulator zero are all GND.

### P-20 Origin of the -0.055 % and -0.13 deg front-end deficit

- **Goal:** separate the follower models from input capacitance as the cause of the P-09 deficit.
- **Schematic:** `circuits/frontend_mc_nominal.cir` (or `frontend_mc.cir` without `.MC`). Variants as edited copies:
  - P20a: `X_U2` and `X_U3` replaced by ideal buffers `E_U2 HPF 0 N07629 0 1` and `E_U3 VSAMPLE 0 N08020 0 1`. The INA828 stays.
  - P20b: as P20a plus a 6.4 pF capacitor from N07629 to VREF and a 6.4 pF capacitor from N08020 to VREF.
  - P20c: ideal buffers and an ideal in-amp `E_INA VDIFF VREF INP CM 11`. This is the wiring check.
- **Parameters:** `.AC LIN 1 517 517`, `.OPTIONS NUMDGT=8`, probe `VM([VSAMPLE])`, `VP([VSAMPLE])`. Three runs of a few seconds.
- **Expected:** P20c reproduces the analytic values 11.0793 V/V and +1.6300 deg within 0.001 %. P20a gives 11.0794 V/V and +1.570 deg (the INA828 gain of 11.000074 V/V and phase of -0.060 deg from P-09). P20b changes P20a by -0.058 % and -0.034 deg (`simulations/design-review/scripts/batch2_calc4.py`), so 11.0730 V/V and +1.536 deg. The measured P-14 nominal is 11.0732 V/V and +1.518 deg.
  - If P20a is already at 11.0732 V/V and +1.52 deg, the OPA192 model causes the deficit. If P20a is at 11.0794 V/V and +1.57 deg and P20b is within 0.02 deg of P-14, the follower input capacitance is the cause.
  Pass: P20c within 0.001 %. The result for P20a and P20b is reported, not judged.
- **Status:** deprecated, 7 November 2026. Not required for LIA-AFE-Eval: the deficit belongs to the unity-gain OPAx192 front end. The board front end (K = 2, OPA2196) is measured in P-24.

### P-21 Switch with 5 V part parameters and reference impedance

- **Goal:** rerun the demodulator with the TMUX1136 data of DI-01 and measure the effect of charge injection into a reference with finite resistance (DI-01, DI-09, finding F-A).
- **Schematic:** `circuits/lia_v3_fast_P21.cir`, a copy of `lia_v3_fast.cir` with Vampl = 0.2 V, ost = 0, p = 0, kref = 0, and these edits. The instance lines of `X_U1` and `X_U3` use `RON=2 CS=10P CD=20P QINJ=6P TAU=5N ILK=3P`. `E_REF REF 0 VALUE ...` becomes `E_REF REFB 0 VALUE ...` with a new `R_RREFS REFB REF {rrefs}` and the parameter `rrefs=1m`. CS = 10 pF is an assumption, because the datasheet source-off capacitance was not read. A second copy `lia_v3_fast_P21b.cir` keeps the original switch parameters (QINJ = 0.4P) as the baseline.
- **Parameters:** fast, `.TRAN 0 0.15 0 5u SKIPBP`, `.STEP PARAM rrefs LIST 1m 10 1k 5k`, `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`, probes `V(VX)`, `V(VY)`, `V(REF)`.
- **Expected:** the baseline step (rrefs = 1 mOhm) gives VX - 2.5 V = -127.325 mV and VY - 2.5 V = -0.344 mV (P-08), within 0.01 mV. The DC shift with rrefs is at most Q x 2 f_osc x rrefs (a bound, the sign and exact size depend on the edge order in the model):

  | rrefs | Bound, 6 pC | Bound, 0.4 pC |
  |---|---|---|
  | 10 Ohm | 0.06 uV | 0.004 uV |
  | 1 kOhm | 6.2 uV | 0.41 uV |
  | 5 kOhm | 31 uV | 2.1 uV |

  Pass: the VX and VY shifts relative to the rrefs = 1 mOhm step stay within the bound (+10 %) or 0.002 mV, whichever is larger. The analyst reports the measured value over the bound. The spike at node N00695 is not resolved with the 5 us step and is reported as not measurable. A finding of more than the bound means the charge model of SPDT_PREC differs from the assumption.
- **Status:** deprecated, 7 November 2026. Not required for LIA-AFE-Eval: the board runs the TMUX6136 on ±15 V (DI-01 is resolved by the separate ±15 V input) and its demodulator zero is GND. P-28 covers the switch.

### P-22 DC step at the sensor input

- **Goal:** measure the chain response and recovery to a sudden DC change at the sensor input (baseline shift, switch-on), including the input clipping of the in-amp.
- **Schematic:** `circuits/chain_ss_P22.cir`, a copy of `chain_ss.cir` in which `R_SP SP3 INP {rsens}` is replaced by `V_STEP SP3 SPS PULSE(0 {dvstep} {tstep} 1u 1u 1 2)` and `R_SP SPS INP {rsens}`, with `dvstep=0 tstep=20m` added. asin = 15 mV, cout = 1 uF (tau = 10 ms in the run).
- **Parameters:** `.TRAN 0 0.3 0 2u` (2 us as P-16, because 5 us fails when the in-amp clips), `.STEP PARAM dvstep LIST 0 50m 100m 300m`, `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`, probes `V(VDIFF)`, `V(VSAMPLE)`, `V(VX)`, `V(VY)`.
- **Expected:** the step response of the ideal chain (INA828 gain 11, high-pass and low-pass of the netlist) has a peak of 3.14 V per volt of input step at 0.47 ms, and the output returns to within 1 mV after 5.1 ms (50 mV), 5.2 ms (100 mV). `simulations/design-review/scripts/batch2_calc3.py` gives these values.

  | dvstep | VDIFF step (11 x dvstep) | Peak abs(VSAMPLE - 2.5 V) | Time until within 1 mV |
  |---|---|---|---|
  | 50 mV | 0.55 V | 0.157 V | 5.1 ms |
  | 100 mV | 1.1 V | 0.314 V | 5.2 ms |
  | 300 mV | 3.3 V, so VDIFF would reach 5.8 V | about 0.67 V (VDIFF clipped near 4.85 V, 2.35 V step x 0.285) | about 5.6 ms |

  The mean of VX and VY returns to the dvstep = 0 value within 0.01 mV from 240 ms after the step (24 tau). A DC input is rejected by the demodulator mean (0.5 v + 0.5 (2 Vref - v) = Vref). During the transient the VX ripple at f_osc is about 39 mV per volt of VSAMPLE excursion (tau = 10 ms), so 12 mV at the 0.314 V peak. Pass: the VSAMPLE peak within 15 % of the table (the 300 mV row within 30 %), recovery time within 1 ms of the table, and the final VX and VY within 0.01 mV. The analyst reports if the INA828 model clips the step at a value other than 4.85 V.
- **Status:** deprecated, 7 November 2026. Not required for LIA-AFE-Eval: single-rail chain. The board version is P-32.

---

## Batch 4: LIA-AFE-Eval schematic (requested 7 November 2026)

The user asked to simulate the current LIA-AFE-Eval topology as closely as possible. Entries P-23 to P-34 replace the planned single-rail entries P-18 to P-22, which are deprecated below. The comparison of the board netlist with the earlier circuits is in [`schematics/LIA-AFE-Eval/docs/reviews/2026-11-07_schematic_rev0.2.md`](../schematics/LIA-AFE-Eval/docs/reviews/2026-11-07_schematic_rev0.2.md) §2.

**Value sources.** The values in these entries come from the LIA-AFE-Eval netlist exported on 7 November 2026 (commit 3429288, A-01 and A-02 fixed afterwards in the working copy, connectivity checked) and from [`schematics/LIA-AFE-Eval/docs/requirements.md`](../schematics/LIA-AFE-Eval/docs/requirements.md) rev E. `simulations/design-context.md` was moved to this board on the same day. Every expected value below is from `simulations/ti-pspice/docs/sim-results/scripts/afe_eval_expected.py` (run with `--mc`) unless stated. The bench ±5 V input is set slightly above 5 V so that +5VA is 5.0 V to 5.2 V (DC-3, E-12). The circuit default is v5 = v5n = 5.3 V. The smoke runs below used 5.0 V.

**Circuits.**

| Circuit | Content |
|---|---|
| `circuits/afe_eval.cir` | The whole analog chain of the board, element names as the KiCad designators: bench inputs through B5819W and the 1 Ohm rail resistors, excitation MFB (U1B, R59, gate load), drain bias (U10A/B, R60/C74, R25/R31), TMUX1109 on-path, pixel stand-ins, heater drivers (U9A/B, 15 Ohm shunts, INA190 stand-ins), INA828 and the K = 2 band-pass (U2, U3), TMUX6136 on ±15 V with U26/U27 and the Sallen-Key post-filters. OPA2196 uses the TI model `OPAx196` from `nom_pspti.lib`. Deviations from the netlist are listed in its header. |
| `circuits/afe_demod.cir` | The demodulator sheet alone, driven at BPF_OUT by an ideal sine, with ideal rails `vpa`, `vna`, `v15`. |
| `circuits/gen_exc_stair.py` | Writes `circuits/afe_eval_stair.cir`, in which the NUCLEO DAC sine is a 128-sample, 12-bit staircase. |

**Smoke test (7 November 2026, not graded).** Runs `smoke_afe_op` (`.AC DEC 20 100 5k`, bias point) and `smoke_afe_tran` (`.TRAN 0 80m 0 5u`, cpf = 15 nF) of `afe_eval.cir`, and `smoke_afe_demod` (`.TRAN 0 60m 0 2u`) of `afe_demod.cir`, all with status done. Bias point: +5VA 4.820 V, GATE 0.99460 V (hand value 0.99458 V), VSUP_A 2.63252 V, DRN_A 0.15745 V. Transient: gate 5.003 mVpp, BPF_OUT 394.87 mV pk at 167.12 deg, X_OUT -244.99 mV, Y_OUT -55.98 mV, settled within 0.01 mV from 30 ms. Against the ideal chain (drain 9.9914 mV pk, front end 39.587 V/V at +0.014 deg) the front end with vendor models reads -0.17 % in gain and -1.53 deg in phase. The demodulator alone gave X_OUT 254.69 mV for 400 mV pk (ideal 254.65 mV). These numbers are a first look. P-24 and P-27 measure them properly.

**Conventions of `afe_eval.cir`.** INA828 VIN+ is DRN_B and VIN- is DRN_A, so the active pixel (side A) enters with a minus sign. More pixel current lowers the drain. TMUX6136 SEL = 1 connects SxA (BPF_OUT), so the demodulator output is +BPF_OUT while REF_X is high. With REF_X high in the first half period and REF_Y delayed by T/4, a BPF_OUT sine A sin(wt + phi) gives X_OUT = (2/pi) A cos(phi) and Y_OUT = -(2/pi) A sin(phi). Parameters are changed with a one-value `.STEP PARAM <name> LIST <value>`, because `--extra ".PARAM"` cannot redefine them (`docs/simulation-quirks.md`).

**Fast settings for this batch.** `.STEP PARAM cpf LIST 15n` sets C13 to C16 to 15 nF, so each post-filter pole has tau = 3 ms instead of 0.3 s. The filter settles to 1e-6 in 50 ms. The 2f0 ripple at X_OUT is then 2.6e-3 of the 2f0 component at X_DEM_OUT, about 1.1 mV pp at 250 mV. Measure means over 20 whole periods (38.61 ms at 518 Hz) from 60 ms, in a `.TRAN 0 0.1 0 5u` run (2u where an entry asks for it). Use `.OPTIONS NUMDGT=8`.

### Applicability of the earlier entries to LIA-AFE-Eval

| Entries | Still valid for LIA-AFE-Eval | Superseded by |
|---|---|---|
| C-01 | Yes. The SPDT_PREC model is the TMUX6136 stand-in in `afe_eval.cir`. | — |
| C-02 | The INA828 gain formula, yes. The value 11 V/V, no (board RG = 5.62 kOhm). | P-24 |
| C-03 to C-07, P-01 to P-08 | Method only: time step, `.IC`, settling windows, ripple and slew models. The circuit is the single-rail OPAx192 demodulator with an RC filter. | P-27, P-28 |
| P-09, P-14 to P-17 | No. Single 5 V rail, unity-gain filters, OPAx192, 100 kOhm bias resistors. | P-24, P-25, P-30, P-32, P-27 |
| P-10 | No. The board demodulator is referred to GND, not to a 2.5 V reference. | P-23 (rails) |
| P-11 to P-13 | The mechanisms carry over (R78/R79 mismatch, driver impedance, 2 vos). The numbers do not. | P-28 |

### P-23 Operating point and rails of the board

- **Goal:** check the DC operating point of every stage on the real rails, and the margins to the rails and to the DAC80508 reference limit.
- **Schematic:** `circuits/afe_eval.cir`, defaults (v5 = v5n = 5 V, v15 = 15 V, vgdac = 1.0 V, vdrc_a = vdrc_b = 2.4 V, ida = idb = 7.5 uA, vda = 0, heaters off), then heaters on.
- **Parameters:** run P23a: `.OP` with `.STEP PARAM vda LIST 0`. Run P23b: `.OP` with `.STEP PARAM vh_a LIST 1.25 2.0` (heater A at 2.5 V and 4.0 V, AN-14 via LIA-Readout). Run P23c: `.DC LIN PARAM v5 4.6 5.6 0.05` with probes V(P5VA), V(P5VP), V(X_OUT), V(GATE), V(VSUP_A). The node voltages are in the `.out` bias table.
- **Expected:**
  - GATE = (1 + R5/R6) x 1.0 V - (R5/R6) x 1.65 V = 0.99458 V within 0.3 mV (OPA2196 offset ±100 uV max, SBOS869 as read in the 2026-10-29 review).
  - VSUP_A = 1.1 x 2.4 V - 1 kOhm x 7.5 uA = 2.6325 V, DRN_A = VSUP_A - 330 kOhm x 7.5 uA = 0.1575 V, both within 1 mV. Same for side B.
  - INA_OUT = 9.897 x (DRN_B - DRN_A) plus offset, below 2 mV at equal drains. HPF_OUT and BPF_OUT below 1 mV (the high-pass blocks the INA828 offset). X_OUT and Y_OUT below 0.5 mV (2 Vos of U26A plus Vos of U26B).
  - +5VA = v5 - V_F(D5) - 1 Ohm x I(+5VA). The diode model is generic, so the analyst reports the rail and current and compares V_F with the B5819W datasheet curve, marked not verified if the curve is not read. With +5VA below 5.0 V, VDD/2 is below the 2.5 V internal reference of the DAC80508 (finding F-01 of the 2026-10-29 review). The analyst states, from P23c, which bench voltage v5 gives +5VA = 5.0 V.
  - P23b: HFB_A = 2 x DAC1 = 2.5 V and 4.0 V within 1 mV. U9A output = HFB_A + 15 Ohm x I_htr, with I_htr = 4.0 V / 604.5 Ohm = 6.62 mA, so 4.099 V at 4.0 V. +5VP is 4.82 V in the smoke run without heater current. With 6.6 mA more it drops by about 7 mV in R32 plus the diode change. Pass: the U9A output stays at least 0.2 V below +5VP (Draft headroom margin, `simulations/design-context.md` §7), HSENSE_B = 25 x 15 Ohm x 6.62 mA = 2.48 V within 2 %.
  - Pass for all runs: every op amp output and input at least 0.2 V inside its rails, and no input of U26A, U27A, U3A, U3B in the OPA2196 transition region (V+ - 3 V to V+ - 1.5 V) at DC.
- **Status:** done, 7 November 2026
- **Result:** GATE 0.99460 V, VSUP_A 2.6325 V and the drains at 0.1575 V match the expected values, with +5VA at 5.12 V for v5 = 5.3 V and 5.0 V for v5 = 5.18 V, and the heater at 4.0 V keeps 0.99 V of headroom to +5VP. The zero-signal X_OUT is about -0.05 mV analytic, because the .OP leaves the post-filter unsettled. [sim-results/P-23.md](ti-pspice/docs/sim-results/P-23.md)
- **Grade:** A (main session, 7 November 2026). Four rounds with the Opus judge agent (C, C, C, B). The rounds found that the printed .OP of `afe_eval.cir` is a pseudo-transient that leaves the post-filter and the OPAx196 internal MID nodes unsettled (options.inc PTRAN tolerances), so the zero-signal X_OUT values of the bias tables are artefacts and the settled value (about -0.05 mV) is analytic. A tight-tolerance .OP did not finish in 23 min. All other checks are on settled nodes, within 0.12 uV. The last B items (settling table, INA828 model bias explaining the drain difference, chain-offset bound with a datasheet worst case of 0.91 mV, wording) were applied and checked by the main session, which also fixed one unit slip (150 pA).

### P-24 Front-end AC response with vendor models

- **Goal:** measure the in-amp and K = 2 band-pass response of the board with the INA828 and OPAx196 models, and the extra gain and phase error of the finite amplifier bandwidth.
- **Schematic:** `circuits/afe_eval.cir`, defaults, acexc = 1 (AC through the excitation and the pixel stand-in).
- **Parameters:** `.AC DEC 200 50 20k` with `.STEP PARAM acexc LIST 1`, probes `V(DRN_A)`, `V(DRN_B)`, `V(INA_OUT)`, `V(HPF_OUT)`, `V(BPF_OUT)`. The analyst divides each node by V(DRN_B) - V(DRN_A). A second run P24b replaces `X_U2`, `X_U3A`, `X_U3B` by ideal blocks (edited copy `afe_eval_P24b.cir`: `E_U2 INA_OUT 0 VALUE {9.8968*(V(DRN_B)-V(DRN_A))}` and ideal op amps as `E` sources with gain 1e7). P24b is the wiring check.
- **Expected:** ideal front end: peak 39.587 V/V at 518.03 Hz, |H(518 Hz)| = 39.587 V/V at +0.014 deg, -3 dB band 377.5 Hz to 710.9 Hz, phase slope -0.4424 deg/Hz, |H(50 Hz)| = 0.3722, |H(1036 Hz)| = 12.18, |H(1554 Hz)| = 4.881, |H(5 kHz)| = 0.4295 V/V. INA828 stage 9.8968 V/V. Pass: P24b within 0.01 % and 0.01 deg of these values. With vendor models the smoke run gave -0.17 % and -1.53 deg at 518 Hz. The analyst reports the vendor-model gain and phase at 518 Hz per stage (INA_OUT, HPF_OUT, BPF_OUT), and the phase change for a ±30 % change of the op amp gain-bandwidth (estimated by scaling, marked as an estimate), because a phase that moves with temperature reads as an X error.
- **Status:** done, 7 November 2026
- **Result:** the ideal-block wiring check P24b matches the closed form within 0.0002 % and 0.00001 deg at every check point (peak 39.587 V/V at 518.03 Hz, band 377.49 Hz to 710.90 Hz). With the INA828 and OPAx196 models the front end is -0.024 % and -0.177 deg off the ideal at 518 Hz, -0.25 deg at 2f0 and -0.36 deg at 3f0, and the stop band above 10 kHz rises above the ideal (+90 % at 20 kHz). A ±30 % op-amp GBW change moves the 518 Hz phase by -0.050 deg to +0.027 deg (scaling estimate). The front end explains only -0.18 deg of the -1.53 deg smoke-run lag; the 10 pF cmux adds -0.62 deg, and -0.74 deg is left for P-27. See [sim-results/P-24.md](ti-pspice/docs/sim-results/P-24.md).
- **Grade:** A (main session, 7 November 2026). The Opus judge agent graded C, then B after one revision. The B listed four last-digit and label corrections (analytic band edges 377.492 Hz and 710.894 Hz with -0.002 Hz and +0.004 Hz differences, remainder -0.078 %, slope difference +0.08 %, one row label), which the main session applied as specified. Every other number was reproduced by the judge.

### P-25 Band-pass tolerance Monte Carlo (SIM-14 for the board)

- **Goal:** find the gain and phase spread at 518 Hz for the first build (C0G ±5 %, decision E-5) and for the ±1 % rework.
- **Schematic:** `circuits/afe_mc.cir`, a copy of the front end of `afe_eval.cir` (U2, U3 and their parts, ideal differential source at the INA828 inputs, 1 V AC) with `.MODEL RTOL RES(R=1 DEV=0.1%)` on R9 to R13, R70 to R73 and R10, and `.MODEL CTOL CAP(C=1 DEV=5%)` on C9 to C12 (the literal tolerance form of `docs/simulation-quirks.md`). Copy P25b with `DEV=1%`.
- **Parameters:** `.AC LIN 1 518 518`, `.MC 500 AC VP([BPF_OUT]) YMAX OUTPUT ALL SEED=17`, `.OPTIONS NUMDGT=8`. Two runs.
- **Expected:** numpy with the same uniform tolerances (200 000 samples):

  | C tolerance | Gain error mean | Gain std | Gain 2.5 % to 97.5 % | Phase std | Phase 2.5 % to 97.5 % |
  |---|---|---|---|---|---|
  | 5 % | +0.24 % | 7.13 % | -12.2 % to +14.7 % | 3.31 deg | -6.3 deg to +6.6 deg |
  | 1 % | +0.01 % | 1.43 % | -2.6 % to +2.8 % | 0.67 deg | -1.3 deg to +1.3 deg |

  Pass: each std within ±10 % of the table (500 samples). SIM-14 asks for gain 4.00 ± 1 % and phase 0 ± 2 deg per band-pass. The 5 % build is expected to fail it, and the 1 % rework to pass it for phase and to fail it for gain on about half of the boards (gain std 1.43 % against a ±1 % limit, numpy yield 47.6 %). (Corrected by the main session on 7 November 2026: the first version said 2.5 % of the boards, which mixed up the 95 % interval of ±2.6 % with the yield.) The analyst states this against SIM-14. The spread is calibrated out per board, so the result decides whether the filter can be used without a per-board calibration.
- **Status:** done, 7 November 2026
- **Result:** Both builds reproduce the numpy gain and phase spread within ±10 % (gain std 7.00 % and 1.41 %, phase std 3.36 deg and 0.68 deg), and about half of the 1 % boards fail the SIM-14 gain limit (48.1 % pass), see [sim-results/P-25.md](ti-pspice/docs/sim-results/P-25.md)
- **Grade:** A (main session, 7 November 2026). The Opus judge agent graded B. Its five items (unexplained 0.019 deg nominal difference with the ruled-out causes and the BPF_OUT load as the remaining candidate, the absolute-phase yields, the corrected SIM-14 wording, the uniform default distribution cited from the PSpice Reference Guide, and a scripted numpy yield) were applied by the analyst. The main session re-ran P-25_mc.py and checked each item. PSpice spreads match numpy within 2 %: gain std 7.00 % and 1.41 %, phase std 3.36 deg and 0.68 deg.

### P-26 Excitation chain (SIM-19 for the board)

- **Goal:** verify the gate amplitude, phase, distortion, DAC image and the stability of U1B with the gate load.
- **Schematic:** `circuits/afe_eval.cir` (P26a, P26c) and `circuits/afe_eval_stair.cir` from `python circuits/gen_exc_stair.py --periods 60` (P26b).
- **Parameters:**
  - P26a: `.AC DEC 100 10 1MEG`, `.STEP PARAM cgate LIST 50p 1n`, acexc = 1 set by an edited copy, probe `V(GATE)`, `V(GOUT)`.
  - P26b: `.TRAN 0 0.1 0 1u`, probes `V(GATE)`, `V(EXC_DAC)`. FFT of the last 40 periods.
  - P26c: step response. Edited copy with `V_EXC EXC_DAC 0 PULSE(1.65 1.95 1m 10n 10n 5m 10m)`, `.TRAN 0 4m 0 50n`, `.STEP PARAM cgate LIST 50p 1n`, probe `V(GOUT)`, `V(GATE)`.
- **Expected:**
  - P26a: |H(518 Hz)| = 1/119.93 V/V, phase +171.73 deg (8.27 deg behind the ideal -1/120). MFB f0 = 4.95 kHz, Q = 0.728. The 1 nF load changes the gate phase at 518 Hz by about R59 x C x w = 0.019 deg. DAC image at 65.786 kHz: the MFB gives -44.9 dB relative to 518 Hz.
  - P26b: gate amplitude 5.0 mVpp within 1 % (vexc_a = 0.3 V pk, AN-4 default), THD at most 0.3 % (AN-7b via LIA-Readout), image at 65.786 kHz at most -40 dBc. The ZOH image is -42.08 dBc before the filter (sinc ratio 1/127) and -87.0 dBc at the gate with the ideal MFB. (Corrected by the judge on 7 November 2026: the first version gave -84.2 dBc and -129 dBc from an extra factor in the script.) Pass for the image is "below -80 dBc". The ZOH adds a half-sample delay of 1.41 deg to the phase of P26a.
  - P26c: GATE step = -0.3 V / 120 = -2.5 mV. A second-order low-pass with Q = 0.728 overshoots by 5.1 %. Pass: overshoot at most 6.1 % at 50 pF and at 1 nF, and no ringing above 100 kHz (which would mean low phase margin of U1B). The 2026-10-29 review estimated 79 deg at 100 pF and 55 deg at 1 nF.
- **Status:** done, 7 November 2026
- **Result:** gate 5.00194 mVpp (target 5.0 mVpp), MFB 1/119.92 V/V at +171.70 deg at 518 Hz, THD 0.027 % (limit 0.3 %), DAC image -83.3 dBc at the gate (limit -40 dBc), ZOH lag 1.416 deg, step overshoot 5.23 % (limit 6.1 %), no ringing. The vendor MFB passes the 66 kHz image 4 dB more than the ideal (op-amp output impedance feedthrough, not verified). See [sim-results/P-26.md](ti-pspice/docs/sim-results/P-26.md).
- **Grade:** A (main session, 7 November 2026). The Opus judge agent graded C, then B after one revision. The four B items (residual identified as higher ZOH images, 5.00194 mVpp arithmetic, grid dependence of the EXC_DAC harmonics, the 0.29 dB transient-against-AC image gap with its limit) were fixed by the analyst and checked by the main session. The entry's ZOH image values were wrong in the expected-value script (extra factor) and were corrected by the judge.

### P-27 Full chain: scale factor and phase over a full turn (SIM-13 for the board)

- **Goal:** measure the X/Y transfer of the whole board from the gate to X_OUT and Y_OUT, with vendor models, over the excitation phase.
- **Schematic:** `circuits/afe_eval.cir`, vda = 10 mV (drain amplitude at nominal gate drive), fast settings.
- **Parameters:** `.TRAN 0 0.1 0 5u`, `.STEP LIN PARAM pexc 0 315 45` (8 steps). PSpice allows one `.STEP` per run, so cpf = 15n is set in an edited copy `afe_eval_fast.cir`. Probes `V(X_OUT)`, `V(Y_OUT)`, `V(BPF_OUT)`, `V(GATE)`. Mean over 20 periods from 60 ms.
- **Expected:** the drain amplitude is 10 mV x 1.00055 (MFB) x 0.99858 (R_D with 50 pF) = 9.9914 mV pk. R = sqrt(X^2 + Y^2) = 25.202 x 9.9914 mV = 251.80 mV with the ideal front end. The phase at BPF_OUT is phi = pexc + 171.73 - 3.07 + 0.01 = pexc + 168.67 deg (ideal). X_OUT = R cos(phi) and Y_OUT = -R sin(phi). With vendor models the smoke run at pexc = 0 gave R = 251.30 mV and phi = 167.13 deg. Pass: R constant over pexc within 0.2 %, phi - pexc constant within 0.2 deg (X/Y orthogonality, AN-25 via LIA-Readout), R within 0.5 % of the P-24 vendor-model gain times 2/pi times 9.9914 mV. The analyst reports the scale factor X_OUT / v_drain in V/V (ideal 25.202) for comparison with E-9 (25.5 at G = 10).
- **Judge note (7 November 2026, after P-24):** the expected phase above used 50 pF at the drain. `afe_eval.cir` also has the TMUX1109 drain capacitance cmux = 10 pF on DRN_A and DRN_B, so the node has 60 pF. With 60 pF the R_D lag is 3.687 deg and the amplitude factor 0.99793, so the drain amplitude is 10 mV x 1.00055 x 0.99793 = 9.9848 mV pk and phi = pexc + 171.73 - 3.69 + 0.01 deg (ideal front end). P-24 measured the vendor-model front end at -0.024 % and -0.177 deg against the ideal. Together these predict phi = pexc + 167.87 deg. The smoke run gave 167.13 deg, so about -0.7 deg is not explained yet. The analyst measures the phase at GATE, DRN_A, DRN_B, INA_OUT and BPF_OUT separately (add these probes) and locates it.
- **Status:** done, 7 November 2026
- **Result:** R constant to 0.054 % and phi - pexc constant to 0.0026 deg over the turn. R is 251.366 mV, which matches 2/pi x 39.5775 x 9.9765 mV (the measured differential drain amplitude) to 0.000 %, and 251.368 mV with the closed-form MFB and 71 pF (-0.001 %). The scale factor R / |DRN_A| is 25.194 V/V, 0.033 % below the ideal 25.202 V/V. The drain stage carries the judge's remainder. The INA828 model adds 10 pF and 1 pF at the drain nodes, so the node is 71 pF and the chain phase is pexc + 167.11 deg (the judge note's 167.87 deg assumed 60 pF). See [sim-results/P-27.md](ti-pspice/docs/sim-results/P-27.md).
- **Grade:** A (main session, 7 November 2026). The Opus judge agent graded B. Its eight corrections were applied by the analyst (two-node 71 pF drain model in the script, E-9 scale-factor split -0.022 % front end, -0.008 % feedthrough, -0.003 % demodulator, gate amplitudes, max step, whole-period settling windows). The one disputed number (251.347 mV) was settled by the main session: the analyst had used the single-ended drain factor. The remaining -0.7 deg of the smoke run is the INA828 model input capacitance (10 pF per input, 1 pF across), so DRN_A sees 71 pF. A run without these capacitances was not made.

### P-28 Demodulator linearity, offset and OPA2196 transition region (SIM-10, SIM-11 for the board)

- **Goal:** measure the demodulator gain and offset from 1 mV to full scale on the real ±5VA rails, and the error when the U26A input enters the OPA2196 input transition region.
- **Schematic:** `circuits/afe_demod.cir`.
- **Parameters:** `.TRAN 0 0.1 0 2u`, cpf = 15n (default of this circuit). Run P28a: `.STEP PARAM ain LIST 1m 10m 100m 0.4 1 1.5 2 2.5 3`, p = 0, vpa = vna = 4.6 V. Run P28b: same steps with vpa = 5.0 V (edited copy). Run P28c: `.STEP PARAM ain LIST 0`, then `.STEP PARAM vos_in LIST -0.1 0 0.1` (DC at BPF_OUT, zero signal). Run P28d: p = 90 deg, ain = 0.4 V and 2 V. Probes `V(X_OUT)`, `V(Y_OUT)`, `V(D1)`, `V(X_DEM)`.
- **Expected:**
  - X_OUT = (2/pi) ain cos(p): 0.6366 mV at 1 mV, 254.65 mV at 0.4 V, 1273.2 mV at 2 V. Linearity within 0.1 % from 10 mV to the largest amplitude that keeps U26A +IN out of the transition region (AN-25 via LIA-Readout).
  - The transition region starts at V+ - 3 V, so at 1.6 V for +5VA = 4.6 V and at 2.0 V for 5.0 V. The +IN of U26A carries BPF_OUT in the +1 state, so the first ain inside the region is 2 V at 4.6 V and 2.5 V at 5.0 V. The analyst reports the X error at each ain in both runs. Full scale at the AN-23a drain level (50 mV pk) is 1.979 V pk at BPF_OUT (P-24 ideal gain), so this is the error at full scale.
  - Clipping: X_DEM swings ±ain. U26A clips when ain approaches +5VA minus its output swing. The analyst reports the first ain where X departs from linear by more than 1 %.
  - P28c: X_OUT and Y_OUT at zero signal below 0.5 mV (2 Vos of U26A plus Vos of U26B, OPA2196 ±100 uV max) and independent of the DC at BPF_OUT within 0.01 mV per 100 mV (the square reference averages a DC to zero).
  - P28d: X_OUT below 0.2 % of R, Y_OUT = -(2/pi) ain.
- **Status:** done, 7 November 2026
- **Result:** with the 0.048 mV zero-signal offset removed, the demodulator gain is linear to 0.002 % from 10 mV to 3 V at 4.6 V and 5.0 V, and the full-scale quadrature error is 0.084 % of R (0.048 deg), but the OPA2196 transition region is not tested by the model and needs a bench check. See [sim-results/P-28.md](ti-pspice/docs/sim-results/P-28.md).
- **Grade:** A (judge agent, 7 November 2026, third round after C and B). Re-run of P-28_linearity.py reproduces every scripted number. Linearity (-0.00065 % offset-corrected, 10 mV to 3 V at 4.6 V and 5.0 V), the zero-signal offset and DC rejection, and the full-scale quadrature error (0.084 % of R, 0.048 deg) pass. The OPA2196 transition region is correctly reported as not tested, because the OPAx196 model has no common-mode offset step. The decomposition of the edge error into delay, slew and recovery terms is not unique, and the summary says so.

### P-29 System CMRR with node capacitance (SIM-12 for the board)

- **Goal:** find the leakage of a common-mode drain signal into X and Y from the R_D and node-capacitance mismatch.
- **Schematic:** `circuits/afe_cmrr_mc.cir`, a copy of the drain and front-end part of `afe_eval.cir` with one common AC current source driving both pixel nodes (`I_CM` of 1 V / 330 kOhm into each drain), R25 and R31 on `.MODEL RD RES(R=1 DEV=0.1%)`, C_PIXA and C_PIXB on `.MODEL CN CAP(C=1 DEV=10%)` (cnode = 50 pF), ideal TMUX1109 path.
- **Parameters:** `.AC LIN 1 518 518`, `.MC 200 AC VM([BPF_OUT]) YMAX OUTPUT ALL SEED=5`, `.OPTIONS NUMDGT=8`, probes `V(DRN_A)`, `V(DRN_B)`, `V(BPF_OUT)`. CMRR = |common-mode drain amplitude| / |differential at the in-amp|.
- **Expected:** numpy, same uniform tolerances: median 49.8 dB, 5 % point 41.5 dB, 95 % point 63.9 dB. With the capacitance matched, median 64.6 dB. The INA828 CMRR (at least 100 dB at G = 10, AN-23 via LIA-Readout) is far below this. Pass: median within 1.5 dB of 49.8 dB, which meets the 48 dB median of SIM-12 with a margin of only 1.8 dB. The analyst reports the split of the leakage into X and Y (the capacitance part is in quadrature, so it goes mainly into Y after the phase calibration).
- **Status:** done, 7 November 2026
- **Result:** The median system CMRR is 49.3 dB against 49.7 dB expected with the corrected board model, which meets the SIM-12 target of at least 48 dB, and about 97 % of the leakage power goes to Y, the quadrature output, see [sim-results/P-29.md](ti-pspice/docs/sim-results/P-29.md).
- **Grade:** A (main session, 7 November 2026). The Opus judge agent graded B. Its four items (X/Y phase reference corrected by the 4.30 deg drain lag, normal .MC pass counting, script-quoted 41.6 dB, analyst limits and the unexplained 0.015 deg) were applied by the analyst. The main session re-ran P-29_mc.py: median CMRR 49.28 dB (SE 0.56 dB) against 49.7 dB expected and the 48 dB SIM-12 target, X std 0.081 % and Y std 0.445 % of the common mode, 96.8 % of the leakage power in Y.

### P-30 Noise at X_OUT (SIM-16 for the board)

- **Goal:** find the input-referred noise of the board and check that the amplifiers add at most 10 % of the noise power (AN-23 via LIA-Readout).
- **Schematic:** `circuits/afe_eval.cir` with two noise sources added in an edited copy `afe_eval_P30.cir`: the shot noise of each pixel as `I` sources is not available in `.NOISE`, so each pixel gets a resistor of 2 kT/(q I_D) (thermal current noise equal to 2qI_D, 6.894 kOhm at 7.5 uA) in parallel with the current sink, and a noiseless behavioural source G = -V/R across it that cancels its DC and AC load, so the bias and the drain impedance are unchanged. (Corrected by the main session on 7 November 2026: the first version said 6.9 MOhm and had no compensation, the P-30 analyst found it.) AC input on V_EXC (acexc = 1).
- **Parameters:** `.AC LIN 1 518 518` and `.AC DEC 50 10 100k`, each with `.NOISE V([BPF_OUT]) V_EXC 1`, `.OPTIONS NUMDGT=8`. The noise tables are in the `.out` file.
- **Expected:** shot noise 511.6 nV/sqrt(Hz) and R_D thermal 73.9 nV/sqrt(Hz) per side at the drain, 731.0 nV/sqrt(Hz) differential. The amplifier budget for 10 % of the power is 243.7 nV/sqrt(Hz) input-referred. The INA828 (7 nV/sqrt(Hz), P-15) and RG are far below it. The VSUP filter (R60, C74) passes DAC noise with 0.0307 at 518 Hz. Square-wave fold-down factor 0.9011. Post-filter ENBW 0.4167 Hz (two poles of 0.3 s). X_OUT noise from the sensor alone: 16.83 uV rms. Pass: input-referred total at 518 Hz within 2 % of 731 nV/sqrt(Hz) plus the amplifier terms, and the amplifier share at most 10 % of the power. Pixel 1/f noise and the GMOS model are TBD and not included.
- **Status:** done, 7 November 2026
- **Result:** Drain-referred sensor noise 729.0 nV/sqrt(Hz) matches the corrected expectation (0.00 %). The largest amplifier term is the INA828 input current noise (1.2 % of the power), and the amplifier share is 2.1 % of the power. The fold-down factor is 0.9011. The summary is [sim-results/P-30.md](ti-pspice/docs/sim-results/P-30.md).
- **Grade:** A (main session, 7 November 2026). The Opus judge agent graded C, then B. The C round found that the full .NOISE tables were in the .out and that the largest amplifier term is the INA828 input current noise in the 329 kOhm drain impedance (80.8 nV/sqrt(Hz), 1.20 % of the power), which the entry expectation had omitted. The four B items (X_OUT gain explanation, unrounded comparison values, grouped-table details, a heading) were applied and checked by the main session. Drain-referred sensor noise 729.0 nV/sqrt(Hz) as expected, amplifier share 2.1 % of the power against the 10 % budget, X_OUT 16.78 uV rms from the sensor and 16.96 uV rms in total. The entry's first noise-source description (6.9 MOhm, no load compensation) was wrong and was corrected after the analyst found it.

### P-31 Power-up with the ±15 V input first (SIM-18 for the board)

- **Goal:** show that no op amp latches or stays at a rail when the board is switched on in the specified order, J4 (±15 V) first and J5 (±5 V) second (DC-3, E-12), and that the TMUX6136 ESD path carries no current in that order.
- **Schematic:** `circuits/afe_eval_P31.cir`, a copy of `afe_eval.cir` with u15 = u5 = 0, cpf = 15n, and with the TMUX6136 ESD path added as stand-ins: a `DSCHOTTKY` diode from each of BPF_OUT, D1, D2, REF_X, REF_Y to P15V and from M15V to each of them (the real ESD cells are not modelled). The references and EXC_DAC run from t = 0, as from a NUCLEO that is already on.
- **Parameters:** `.TRAN 0 0.3 0 5u`, t15 = 10 ms, t5 = 50 ms, `.STEP PARAM tramp LIST 1m 5m 20m`. vda = 10 mV. Probes `V(P15V)`, `V(M15V)`, `V(P5VA)`, `V(M5VA)`, `V(BPF_OUT)`, `V(X_OUT)`, `V(Y_OUT)`, `V(GATE)`, `V(VSUP_A)`, and the current of each ESD stand-in.
- **Expected:** before 50 ms only the TMUX6136 rails are up. BPF_OUT is 0 V and the references swing 0 V to 3.3 V inside ±15 V, so no ESD stand-in conducts more than 1 nA. After the ±5 V ramp X_OUT and Y_OUT reach the P-27 value at pexc = 0 within 1 mV. The slowest part is the post-filter. With cpf = 15n it is a double pole at tau = 200 kOhm x 15 nF = 3 ms, so X_OUT and Y_OUT settle within 1 mV about 25 ms after the end of the ramp. VSUP_A follows the R60/C74 filter (tau 10 ms), but the drain DC is removed by the high-pass and does not set the X and Y settling. At the board value cpf = 1.5u (tau 0.3 s per pole) the settling would take about 2.3 s and fail the 250 ms limit, which applies to cpf = 15n only (corrected 8 November 2026, the first text expected about 100 ms from 10 tau of R60/C74). Note (8 November 2026): REF_X and REF_Y are the SEL1 and SEL2 logic inputs, rated to VDD + 0.3 V (SCDS397B section 5.1), so with the references on before J4 the expectation of no conduction cannot hold. No op amp output stays at a rail after the ramp. Pass: settled within 1 mV by 250 ms for every tramp, and ESD stand-in current below 1 nA throughout. The other order (±5 V first) is excluded by the bench procedure and is not simulated. Power-down is not simulated.
- **Status:** done, 8 November 2026
- **Result:** X_OUT and Y_OUT settle within 1 mV of their final values 74 ms to 86 ms after the start (12 ms to 26 ms after the ramp end, set by the 3 ms post-filter, not by VSUP_A) for every tramp with no rail latch. The ESD check fails for a real reason: REF_X drives SEL1 into the unpowered +15 V rail before J4 (diode forward 0.55 V, 32.0 uC, rail at 3.24 V, peak 2.45 A through the 1 Ohm placeholder), and the board has no series resistor. After the rails are up every stand-in is reverse biased, and the -5 uA DC and the edge spikes are DSCHOTTKY artifacts, see [sim-results/P-31.md](ti-pspice/docs/sim-results/P-31.md)
- **Grade:** A, 8 November 2026: numbers recomputed from the raw CSDF points (charge balance closes within 0.1 uC), forward conduction separated from the CJO and -IS artifacts by the diode voltage, pin type and decoupling checked against the KiCad netlist and SCDS397B (peaks, charge and bias-point explanation corrected by the judge).

### P-32 Overload and DC step at the drains

- **Goal:** measure the recovery after a large drain signal and after a step of the drain DC (DAC trim, pixel switching).
- **Schematic:** `circuits/afe_eval.cir`, fast settings. Copy `afe_eval_P32.cir` adds `V_DSTEP` in series with V_DAC2 (`PULSE(0 {dstep} 50m 1u 1u 1 2)`), so VSUP_A steps by 1.1 dstep through the R60/C74 filter (tau 10 ms).
- **Parameters:** `.TRAN 0 0.3 0 2u` (2 us as P-16). Run P32a: `.STEP PARAM vda LIST 10m 50m 100m`. Run P32b: `.STEP PARAM dstep LIST 0 20m 100m` with vda = 10 mV. Probes `V(INA_OUT)`, `V(BPF_OUT)`, `V(X_OUT)`, `V(Y_OUT)`, `V(DRN_A)`.
- **Expected:** P32a: 50 mV gives BPF_OUT = 1.979 V pk and X_OUT about 1.26 V (AN-23a linear input). 100 mV gives 3.96 V pk. On the bench rails of this circuit (+5VA = 5.12 V, -5VA = -5.13 V, P-23) nothing clips at 100 mV. The OPAx196 output limit at about 1 mA load (about 60 mV from the rail) puts the first clipping at U3B (BPF_OUT about 5.06 V pk) at about 128 mV drain amplitude (corrected 8 November 2026, the first text assumed the ±4.6 V rails of P-28). The analyst reports the clipping margin and the X error. P32b: a step of 1.1 dstep at VSUP_A reaches the drain with the 10 ms R60/C74 time constant. INA_OUT moves by -9.897 x 1.1 x dstep (DRN_A is the inverting input), so -0.218 V at 20 mV and -1.09 V at 100 mV. The band-pass rejects the slow step. X_OUT and Y_OUT return to their baseline within 0.1 mV within 30 ms of the end of the R60/C74 settling. The 100 mV step is half of the AN-12b mismatch range and must not clip.
- **Status:** done, 8 November 2026
- **Result:** The chain to BPF_OUT is linear in gain to 0.01 % up to 100 mV drain amplitude. R stays within 0.022 % of linear scaling and the phase of (X, Y) turns by -0.099 deg at 100 mV, from the falling slew (6.63 V/us, OPAx196 model) of U27A at the Y edges. This is the -0.78 % Y_OUT error. Nothing clips on the 5.12 V bench rails (margin 1.09 V at X_DEM), and the first clipping is estimated at about 128 mV drain amplitude at U3B. The 100 mV drain DC step gives a peak X_OUT disturbance of 3.8 mV that is back within 0.1 mV after 23 ms and does not clip. See [sim-results/P-32.md](ti-pspice/docs/sim-results/P-32.md)
- **Grade:** A, 8 November 2026: numbers recomputed from the CSDF files and the script re-run, the Y_OUT error explained as a -0.099 deg phase rotation by the U27A falling slew (model within 4 %), the cross-check difference traced to edge-spike sampling on diverging time grids, and the recovery by the post-filter impulse model (corrections applied by the judge).

### P-33 Heater driver and drain bias amplifier (SIM-8, SIM-20 for the board)

- **Goal:** check the heater driver headroom from +5VP and its stability with cable capacitance, and the range and noise of the drain bias amplifier.
- **Schematic:** `circuits/afe_eval.cir`. The heater feedback node is connected to the switch in this circuit, but not in the netlist (finding A-02 of the 2026-11-07 review). The result is valid only after that fix.
- **Parameters:** P33a: `.DC LIN PARAM vh_a 0 2.3 0.05` with rhtr = 300, 600 and 1.2 kOhm (three edited copies), probes `V(HSH_A)`, `V(HFB_A)`, `V(HSENSE_B)`, `V(P5VP)`, `V(HPIX_A)`. P33b: `.TRAN 0 2m 0 50n` with vh_a stepped by an edited `V_DAC1 DAC1 0 PULSE(1.5 1.6 0.5m 1u 1u 1 2)`, `.STEP PARAM chtr LIST 100p 1n 10n`. P33c: `.DC LIN PARAM vdrc_a 0.4 3.3 0.05` (run with a 0.05 V step instead of the planned 0.01 V, which would take about 2.7 h. The 0.05 V grid resolves a step in the deviation, see the summary), probes `V(VSUP_A)`, `V(U10AO)`, `V(DRN_A)`. P33d: `.NOISE V([VSUP_A]) V_DAC2 1` at 518 Hz with a 100 nV/sqrt(Hz) DAC noise source in series with V_DAC2 (SIM-20).
- **Expected:**
  - P33a: HFB_A = 2 x vh_a until U9A saturates. U9A must give HFB_A + 15 Ohm x I. At 4.0 V on 600 Ohm (I = 6.62 mA) it needs 4.10 V. The analyst reports the largest HFB_A for each heater, and the margin to +5VP. AN-14 asks for 4.0 V. With 300 Ohm (13.3 mA) the INA190 output reaches 25 x 0.2 V = 5 V, so HSENSE clips at 3.3 V above 8.8 mA (finding F-09 of the 2026-10-29 review).
  - P33b: overshoot below 10 % and no oscillation at 10 nF.
  - P33c: VSUP_A = 1.1 x vdrc_a - 7.5 mV, linear within 1 mV from 0.5 V to 3.5 V (AN-9 via LIA-Readout). The +IN of U10A crosses the transition region (V+ - 3 V = 1.8 V at 4.82 V). The analyst reports the largest step in the deviation from linear (finding F-08 of the 2026-10-29 review).
  - P33d: DAC noise at VSUP_A 1.1 x 100 nV/sqrt(Hz) x 0.0307 = 3.4 nV/sqrt(Hz), plus R60 thermal (4.07 nV/sqrt(Hz) x 0.0307). Pass: at most 50 nV/sqrt(Hz) (AN-10 via LIA-Readout).
- **Status:** done, 7 November 2026
- **Result:** The heater driver reaches HFB_A equal to 2 vh_a within 1 mV up to 4.60 V on the 600 Ohm and 1.2 kOhm heaters, but the 300 Ohm heater is limited by the output swing of the OPAx196 model to 4.27 V, the heater step passes at 100 pF with 1.8 % overshoot and fails at 1 nF and 10 nF with 22.5 % and 58.4 % overshoot (poorly damped, no sustained oscillation), the drain bias follows 1.1 vdrc_a - 7.5 mV within 0.02 mV over the whole window, and the VSUP_A noise is 3.4 nV/sqrt(Hz) at 518 Hz, see [sim-results/P-33.md](ti-pspice/docs/sim-results/P-33.md)
- **Grade:** A, 8 November 2026: numbers recomputed from the CSDF files, the 300 Ohm limit is explained by the OPAx196 output swing curve (ceiling 4.267 V against 4.275 V simulated), the overshoot by the 1.47 kOhm model output impedance, and the scripts reproduce every number.

### P-34 Interference and harmonic rejection with the Sallen-Key post-filter (SIM-15 for the board)

- **Goal:** measure the rejection of mains, mains harmonics and signal harmonics at X_OUT with the board filters.
- **Schematic:** `circuits/afe_demod.cir` (demodulator and post-filter, interferer at BPF_OUT scaled by the front-end gain at its frequency) and a check with `circuits/afe_eval.cir` for 3f0.
- **Parameters:** cpf = 1.5u is needed for the beat products. To avoid the 3 s settling of the two 0.3 s poles, start the post-filters at their settled state: `.IC V(X_OUT)=0.25465 V(NC13)=0.25465 V(U26BP)=0.25465 V(Y_OUT)=0 V(NC14)=0 V(U27BP)=0` (p = 0, ain = 0.4 V gives X = (2/pi) x 0.4 V). `.TRAN 0 1 0 5u SKIPBP`, measure the beat amplitude by a least-squares fit at the beat frequency over the last 0.5 s, ain = 0.4 V, `.STEP PARAM fi LIST 50 500 550 1036 1554` with ai = 0.4 V x |H(fi)| / |H(f0)| per step (edited copies, one per fi, because ai changes with fi). Probes `V(X_OUT)`, `V(Y_OUT)`.
- **Expected:** relative to an f0 signal of equal amplitude at the drains, the largest beat product at X_OUT is -158 dB at 50 Hz, -61 dB at 500 Hz (18 Hz beat), -71 dB at 550 Hz (32 Hz beat), -127.3 dB at 1036 Hz (coherent sum of n = 1 and n = 3, factor 8/(3 pi); the earlier -130 dB omitted the n = 3 product), and the 3f0 term is demodulated to DC with -27.7 dB (weight 1/3 times the band-pass). SIM-15 asks for 50 Hz at least 60 dB, 500 and 550 Hz at least 30 dB, 2f0 at least 40 dB and 3f0 at least 25 dB. Pass: each measured value within 2 dB of the prediction, or below the numerical floor where the prediction is under -100 dB. The 2f0 ripple at X_OUT is 0.4244 x ain x 2.6e-7, below 0.1 uV.
- **Status:** done, 8 November 2026
- **Result:** All SIM-15 limits pass (50 Hz -155 dB, 500 Hz -61 dB, 550 Hz -71 dB, 2f0 -123 dB, 3f0 -27.7 dB), and every product matches the prediction with the Sallen-Key feedthrough within 0.6 dB, but the 50 Hz and 518 Hz terms fail the ideal-post-filter prediction and the 2f0 ripple of 453 nV fails the 0.1 uV check, [sim-results/P-34.md](ti-pspice/docs/sim-results/P-34.md)
- **Grade:** A, 8 November 2026: all SIM-15 limits pass, every product and the 2f0 ripple agree within 0.6 dB with the Sallen-Key feedthrough model (L = 81.6 uH from the reference run), and the script reproduces every number (three wording errors corrected by the judge).

## Batch 5: proposals of the Batch 4 design review (planned 8 November 2026)

P-35 to P-43 are the proposals R-06 to R-14 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md). Circuit paths are relative to `simulations/ti-pspice/`. P-37, P-40 and P-41 are bench entries for the owner. P-35 depends on the owner's decision on the series resistors of findings F-01 and F-02. One change to the reviewer's text: P-35 keeps the P-31 stand-ins without an area factor, because the area factor also scales RS.

### P-35 Series resistors on the switch pins and the power sequences

- **Source:** proposal R-06 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** show that 1 kOhm in series with REF_X, REF_Y (SEL1, SEL2) and with BPF_OUT (S1A, S2A) keeps every switch pin current below 10 % of the 30 mA rating in the power-up, power-down and fault orders, without changing the demodulator result.
- **Precondition:** the owner accepts the 1 kOhm series resistors of F-01 and F-02. The circuit copy models them before the schematic changes.
- **Schematic:** `circuits/afe_eval_R06.cir`, a copy of `afe_eval_P31.cir` with `R_SELX KEX_PIN REF_X_S 1k`, the same for Y, 1 kOhm between BPF_OUT and the S1A and S2A pins, a 25 Ohm source resistance in V_REFX and V_REFY (assumed STM32F303 output resistance, not verified), the stand-ins as in P-31 (one `DSCHOTTKY` model, area 1), and V_DAC0 to V_DAC7 gated by a ramp that follows P5VA (a `VALUE` source with `limit`). Do not give the stand-ins an area factor. It divides RS by the area (0.08 Ohm / 1e-6 = 80 kOhm), so it acts as a series resistor (P-31 judge). Forward conduction is read from the diode voltage, as in P-31.
- **Parameters:** `.TRAN 0 1.2 0 5u`, cpf = 15n. Orders: (a) references from t = 0, J4 at 10 ms, J5 at 50 ms (as P-31). (b) Power-down: J5 off at 0.6 s, J4 off at 0.7 s. (c) Fault: J4 off at 0.6 s with J5 on, vda = 50 mV. Probes: stand-in currents, P15V, BPF_OUT, X_OUT, Y_OUT.
- **Expected:** peak SEL current (3.3 - 0.55) / (1 kOhm + 25 Ohm) = 2.7 mA (calc1: 2.6 mA with 0.6 V). The +15 V rail reaches 2.7 V with a time constant of 11.4 ms, so about 1.6 V at 10 ms before J4. The fault case (c): BPF_OUT at 1.98 V gives (1.98 - 0.55) / 1.01 kOhm = 1.4 mA, and 3.4 mA at the 4 V of 100 mV drain. The edge delay is 9.5 ns at SEL and 14 ns at the S pins, so X_OUT and Y_OUT final values differ from P-27 by less than 0.2 mV (delta term 4 f0 A delta: 4 x 518 x 2 V x 12 ns = 0.05 mV at A = 2 V, 5 uV at 0.2 V). Pass: all forward stand-in currents below 3 mA (capacitive edge current and the -IS reverse current of the stand-in model excluded, as in P-31), forward conduction only in the first 40 ms, final values within 0.2 mV of P-27.
- **Status:** planned.

### P-36 Heater loop compensation

- **Source:** proposal R-07 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** find the smallest change that gives at most 10 % overshoot at 1 nF and 25 % at 10 nF, and measure the phase margin with `.AC`.
- **Schematic:** `circuits/afe_eval_P33b.cir` copies: (a) Cf across R20 of 10, 22 and 47 pF, (b) Rs of 10 and 22 Ohm between HFB_A and the switch (outside the feedback), (c) U9A from the OPAx192 model of `vendor/sbom862f/`. Loop-gain copy: the feedback broken at R20 with a 1 GH and 1 GF pair.
- **Parameters:** transient as P-33b (0.1 V step on DAC1, `.STEP chtr LIST 100p 1n 10n`, 50 ns step). `.AC DEC 50 1k 10Meg` for the loop gain, probes `V(HFB_A)` and the loop node.
- **Expected:** the baseline reproduces P-33b (1.8 %, 22.5 %, 58.4 % within 1 point) and gives about 19 deg phase margin at 10 nF. No value is predicted for the options: the hand model of calc2 gave 46 deg to 59 deg and failed to reproduce the baseline. A zero at 1/(2 pi R20 Cf) is 319 kHz, 145 kHz and 68 kHz for the three Cf, next to the observed rings of 370 kHz and 122 kHz, which is why they are tested. A smaller Zo is not testable with the black-box model, so the result is an upper bound on the ring. Pass: the baseline reproduces P-33b within 1 point. The best option gives overshoot of at most 10 % at 1 nF and at most 25 % at 10 nF, and a phase margin of at least 55 deg at 1 nF and at least 40 deg at 10 nF (the overshoot limits correspond to zeta 0.59 and 0.40, phase margin about 59 deg and 43 deg). The `.AC` phase margin agrees with the transient overshoot within 10 deg.
- **Status:** planned.

### P-37 Heater swing on the bench

- **Source:** proposal R-08 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** measure the real heater output swing and the headroom with 300 Ohm and 600 Ohm dummy heaters.
- **Schematic:** the board, dummy heater of 300 Ohm 0.1 % 1 W and of 600 Ohm in the calibration position (component_selection lists a 1.00 kOhm dummy heater, wiring not re-read, a socket card with the resistors is an alternative). DMM on TP3, +5VP, HFB_A, HSH_A (the shunt input).
- **Parameters:** DAC1 from 0 V to 2.3 V in 0.1 V steps with J5 set for +5VA = 5.00 V and again at 5.20 V.
- **Expected (calc2):** HFB_A follows 2 x DAC1 within 1 mV up to 4.56 V (600 Ohm, +5VP 5.09 V) or 4.45 V (4.97 V), and up to 4.14 V or 4.04 V on 300 Ohm. Below these, the typical part follows. Pass: ceiling at least 4.0 V + 0.2 V = 4.2 V on the heater actually used. The 300 Ohm result is expected to fail that (4.04 V to 4.14 V), which is the F-05 finding.
- **Status:** planned.

### P-38 Drain compliance and the TMUX1109 clamp

- **Source:** proposal R-09 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** show the drain voltage and the INA_OUT behaviour when VSUP_A is swept through the range 0.5 V to 3.5 V at 7.5 uA.
- **Schematic:** `circuits/afe_eval.cir` with an ESD diode from DRN_A to ground (`.MODEL DESD D(IS=1p N=1)`, anode at ground) and the pixel stand-in unchanged.
- **Parameters:** `.DC LIN PARAM vdrc_a 0.4 3.3 0.05` as P33c. Probes `V(DRN_A)`, `V(INA_OUT)`, `I(D_ESD)`.
- **Expected:** DRN_A = 1.1 x vdrc_a - 7.5 mV - 2.475 V for vdrc_a above about 1.99 V (drain above -0.3 V). Below it the diode carries the part of the pixel current that R_D cannot supply: at vdrc_a = 0.46 V the supply gives (0.5 - (-0.4)) / 330 kOhm = 2.7 uA, the diode gives 4.8 uA, and the drain sits at 0.0259 x ln(4.8 uA / 1 pA) = -0.40 V. INA_OUT leaves the linear relation 9.897 x (DRN_B - DRN_A) below that point. Pass: the model reproduces the clamp and the analyst reports the DAC2 value where DRN_A crosses -0.5 V (calc4: 1.80 V).
- **Status:** planned.

### P-39 Phase-sweep calibration on simulated data

- **Source:** proposal R-10 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** check the ellipse fit of section 5 against known errors before it is used on the board.
- **Schematic:** (a) the P-27 data (`sim-runs/P27_phase`, 8 phases) with no new run. (b) `circuits/afe_eval_fast.cir` with three injected errors: `dly` = 2 us on REF_Y (eps = 360 x 518 Hz x 2 us = 0.373 deg), R84 +0.2 %, and a 0.3 mV offset source in series with the U26A +IN.
- **Parameters:** `.STEP LIN PARAM pexc 0 315 45` as P-27, `.TRAN 0 0.1 0 5u`, cpf = 15n. Fit from the last 20 periods of 60 ms to 100 ms.
- **Expected:** (a) centre within 10 uV of zero, b / a within 0.1 % of 1 (P-27: R spread 0.054 %), eps within 0.03 deg (P-27: phi_XY - phi_BPF from -0.008 deg to +0.023 deg). (b) eps = 0.37 deg + the (a) value within 0.003 deg, b / a differs from (a) by +0.1 % (R84 +0.2 % gives a scale error of 0.1 % in Y), the centre moves by 0.3 mV x 2 = 0.6 mV in the channel of the offset (gain 2 for U26A input offset in the -1 state, the same weight as P-23). Pass: recovered values within 3 uV, 20 ppm and 0.002 deg of the injected ones.
- **Status:** planned.

### P-40 Calibration procedure on the board

- **Source:** proposal R-11 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** run section 5 on the first board and record the residuals.
- **Schematic:** the board with the sequence of step 0, DMM 6.5 digits on X_OUT and Y_OUT through 10 MOhm, generator on TP15.
- **Parameters:** steps 0 to 6 of section 5.3. Repeat step 2 four times over 2 h at constant temperature, and once with a 10 K change (hair dryer on the board, logging TP temperature).
- **Expected:** step 2 and step 3 centres agree within 5 uV if there is no excitation-synchronous pickup. Repeatability of step 2 is 2 uV to 6 uV (calc3 for 10 s). Offsets between 0 and 0.5 mV (RSS of Vos at the maximum 0.5 mV). Step 4 gain within the P-25 limits. Linearity to 0.05 % up to 90 mV. Supply ripple response below 10 uV for 20 mV at 518 Hz. The drift over 10 K is at most 45 uV (4.5 uV/K worst case). Pass: (1) the four repeats of step 2 agree within 6 uV (1 sigma, calc3 for 10 s averaging). (2) the sweep centre of step 3 differs from the step 2 zero by at most 5 uV, or the difference is explained as excitation-synchronous pickup. (3) the fit residual is at most 10 uV rms. (4) b / a is within 0.2 % of 1 and |eps| is at most 0.05 deg. (5) the step 4 gain is within the P-25 limits and the X/Y beat phase is 90 deg ± 0.05 deg and agrees with 90 deg + eps of step 3 within 0.01 deg. (6) R / amplitude is constant to 0.05 % from 10 mV to 90 mV. (7) a 20 mV ripple at 518 Hz on +5VA moves X_OUT by less than 10 uV. (8) the offset change over 10 K is at most 45 uV.
- **Status:** planned (bench).

### P-41 Post-filter capacitor leakage and settling

- **Source:** proposal R-12 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** measure the insulation resistance of C13 to C16 through the DC gain of the post-filter.
- **Schematic:** the board, DMM on X_DEM (demodulator output test loop) and X_OUT, with a DC-like X value (excitation at 10 mV drain and p = 0).
- **Parameters:** wait 12 s, 10 readings each of X_DEM and X_OUT with the same meter on the same range. Repeat for Y. Then a step of excitation phase and 20 min of X_OUT logging after it.
- **Expected:** X_OUT = X_DEM x (1 - 400 kOhm / R_IR). For R_IR of 1 GOhm the difference is 0.04 % (100 uV at 245 mV), for 400 MOhm 0.10 % (245 uV). Meter accuracy 0.002 % allows 5 uV. Pass: R_IR above 400 MOhm for all four capacitors. The settling log shows the two-pole decay with tau = 0.3 s ±20 % and no tail above 1 uV after 20 s (dielectric absorption).
- **Status:** planned (bench).

### P-42 Output impedance of the post-filter op amp and the stopband floor

- **Source:** proposal R-13 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** find how much of the 2f0 ripple and the comb depends on the op-amp model, and check the model against the datasheet ZO.
- **Schematic:** `circuits/afe_demod_P34_f1036.cir` with U26B (and U27B) unchanged as the baseline, and a copy in which they use the OPAx192 model of `vendor/sbom862f/`. The OPAx196 output resistance cannot be changed in the black-box model, so the OPAx192 copy is a sensitivity case only.
- **Parameters:** as P-34 for the 1036 Hz run (`.IC`, `.TRAN 0 1 0 5u SKIPBP`, cpf = 1.5u), fit the 1036 Hz and 2072 Hz lines.
- **Expected:** the OPAx196 case reproduces 453 nV and 180 nV. The datasheet ZO scaling (calc4) predicts 216 nV to 281 nV and 87 nV to 112 nV for an OPAx196 with the datasheet ZO. The OPAx192 case is reported and has no prediction. Pass: the analyst reports L from the quadrature part and the ratio to 81.6 uH.
- **Status:** planned.

### P-43 BPF_OUT clipping threshold

- **Source:** proposal R-14 of [design-review/2026-11-08_batch4.md](design-review/2026-11-08_batch4.md), taken over on 8 November 2026 with the reviewer's expected values.
- **Goal:** confirm the clipping drain amplitude of U3B (open point 1 of P-32).
- **Schematic:** `circuits/afe_eval_P32a.cir`.
- **Parameters:** `.STEP PARAM vda LIST 110m 120m 130m 140m`, `.TRAN 0 0.3 0 2u`, probes as P-32a plus `V(Y_DEM)`.
- **Expected:** BPF_OUT peak 39.571 x 0.1097 V = 4.34 V at the 110 mV step (measured drain 109.7 mV). The model clips at about 5.06 V (60 mV swing), which is a drain amplitude of 128 mV. Between 120 mV and 130 mV the peak stops growing linearly. The datasheet maximum swing (500 mV, 4.62 V, 117 mV drain) is not in the model. Pass: first clipping between 125 mV and 132 mV.
- **Status:** planned.

## Batch 6: gate filter with the NUCLEO-F303RE DAC (requested 8 November 2026)

The user asked how well the gate filter (MFB U1B with R59 and the gate load) turns the stepped DAC sine of the NUCLEO-F303RE into a clean sine, including THD. The first NUCLEO of LIA-AFE-Eval is the NUCLEO-F303RE (requirements rev E, IF-2). Its DAC is 12-bit, with VREF+ tied to VDDA = 3.3 V on the NUCLEO. Circuit paths are relative to `simulations/ti-pspice/`. Expected values are from `docs/sim-results/scripts/P-44_expected.py` (closed form: exact DFT of the codes, zero-order hold, ideal MFB with R59 and 50 pF). Note: `firmware/firmware_requirements.md` describes the STM32U575 production firmware, not the F303. The sample count N = 128 is taken from it (FW table, "Samples per period"), as in P-26.

### P-44 DAC staircase through the gate filter: waveform, THD and images

- **Goal:** show how close the gate signal is to a pure sine for the F303 DAC staircase, and which part of the remaining distortion the filter can and cannot remove. Measure the gate amplitude, THD, THD+N to 20 kHz, the ZOH images and the residual from a fitted sine, for several sample counts, the 8-bit mode, the maximum amplitude, a realistic DAC output (settling, buffer off) and DAC code errors.
- **Schematic:** `circuits/afe_eval.cir` (reference run with the ideal `SIN` source) and staircase copies written by `python circuits/gen_exc_stair.py --periods 32 --n <N> --bits <b> --amp <A> --out afe_eval_P44_<tag>.cir`. Realistic DAC (P44b): edited copies of the N = 128 file with an RC between the PWL source and EXC_DAC (`V_EXC` drives node `EXC_IDEAL`, `R_DAC EXC_IDEAL EXC_DAC 1k`, `C_DAC EXC_DAC 0 {tau/1k}`) for tau = 0.5 us and 1 us, and a buffer-off copy with `R_DAC` = 15 kOhm and no capacitor. STM32F303 DAC data assumed from the STM32F303xD/E datasheet (DocID026415, DAC table): settling 3 us typical and 4 us maximum for a full-scale step, buffer output range 0.2 V to VDDA - 0.2 V, DNL ±2 LSB, INL ±4 LSB, output impedance 15 kOhm with the buffer off. These values were not read from the PDF in this session (st.com did not respond), so they are marked not verified until the owner checks them.
- **Parameters:** `.TRAN 0 60m 0 1u`, `.OPTIONS NUMDGT=8`, probes `V(EXC_DAC)`, `V(GOUT)`, `V(GATE)`. Window: the last 20 whole periods of 518 Hz before 30 T (19.305 ms to 57.915 ms). Runs:

  | Run | Source | N | Bits | Amplitude (V pk at the DAC) | Other |
  |---|---|---|---|---|---|
  | P44_ref | `afe_eval.cir`, ideal SIN | — | — | 0.3 | numerical floor of the THD measurement |
  | P44a_N32, N64, N128, N256 | staircase | 32, 64, 128, 256 | 12 | 0.3 (5 mVpp gate, AN-4) | |
  | P44a_8b | staircase | 128 | 8 | 0.3 | DAC 8-bit mode |
  | P44a_max | staircase | 128 | 12 | 1.2 (20 mVpp gate, firmware maximum) | |
  | P44b_tau05, tau1 | staircase + RC | 128 | 12 | 0.3 | DAC settling |
  | P44b_off | staircase + 15 kOhm | 128 | 12 | 0.3 | buffer off |
  | P44c_ac | `afe_eval.cir`, acexc = 1 (edited copy) | — | — | — | `.AC DEC 100 10 1MEG`, probes `V(GATE)`, `V(EXC_DAC)` |

  Analysis (script `docs/sim-results/scripts/P-44_analysis.py`): least-squares fit of DC and of k f0 for k = 1 to 20 and of the images at N f0 ± f0 and 2 N f0 ± f0 on a uniform 0.1 us grid over the window. THD = rss of h2 to h20 divided by h1. THD+N = rms of the gate minus DC and fundamental, after a 20 kHz brick-wall filter (FFT of the window), divided by the fundamental rms. Residual = rms of the gate minus DC and fundamental, without a filter. Plots: (1) one period of EXC_DAC scaled by -1/120 and of GATE minus DC, overlaid with the fitted sine, (2) the residual, (3) the line spectra of EXC_DAC and GATE in dBc, for N = 32 and N = 128. P44c: the code-error Monte Carlo of `P-44_expected.py` repeated with the measured H(f) of P44c_ac instead of the ideal MFB, 2000 boards.
- **Expected (`P-44_expected.py`, ideal MFB):** |H(518 Hz)| = 1/119.93 V/V at +171.73 deg. Relative to 518 Hz the filter is flat (within 0.2 dB) up to 2.6 kHz (5th harmonic), -3.2 dB at 5.18 kHz, -20.4 dB at 16.06 kHz, -45.0 dB at 65.79 kHz and -57.1 dB at 132.1 kHz. So the filter removes the ZOH images but not the low harmonics.

  | N | Bits | DAC amplitude | Gate amplitude | DAC image at (N-1) f0 | Gate image | THD (h2 to h20) | THD+N to 20 kHz | Residual |
  |---|---|---|---|---|---|---|---|---|
  | 32 | 12 | 0.3 V pk | 4.9936 mVpp | -29.83 dBc | -50.27 dBc | 0.066 % | 0.404 % | 7.19 uV rms |
  | 64 | 12 | 0.3 V pk | 5.0000 mVpp | -35.99 dBc | -68.75 dBc | 0.034 % | 0.036 % | 1.09 uV rms |
  | 128 | 12 | 0.3 V pk | 5.0015 mVpp | -42.08 dBc | -87.02 dBc | 0.031 % | 0.033 % | 0.59 uV rms |
  | 256 | 12 | 0.3 V pk | 5.0023 mVpp | -48.13 dBc | -105.19 dBc | 0.020 % | 0.021 % | 0.38 uV rms |
  | 128 | 8 | 0.3 V pk | 5.0156 mVpp | -42.08 dBc | -87.02 dBc | 0.609 % | 0.616 % | 10.93 uV rms |
  | 128 | 12 | 1.2 V pk | 20.0077 mVpp | -42.08 dBc | -87.02 dBc | 0.007 % | 0.008 % | 0.70 uV rms |

  The ideal 12-bit THD at N = 128 is set by the quantization error (0.320 LSB rms for these codes), which is periodic and appears as harmonics. P-26 measured 0.027 % for h2 to h10 with the same codes. DAC code errors (assumed model, not a datasheet shape: independent code errors uniform in ±1 LSB, so adjacent-code DNL stays within ±2 LSB, plus an INL bow or S-curve of 4 LSB peak) at N = 128 and 0.3 V pk: THD 0.087 % median and 0.120 % at the 95th percentile. At 1.2 V pk: 0.058 % and 0.088 %. A 4 LSB bow alone gives 0.036 % at 0.3 V pk and 0.072 % at 1.2 V pk. P44b: an RC of tau is linear, so it adds no harmonic. It delays the fundamental by 360 x 518 Hz x tau = 0.093 deg at 0.5 us and 0.186 deg at 1 us, and lowers the first image by 20 log10 |1 + j 2 pi (N-1) f0 tau| = -0.18 dB at 0.5 us. The buffer-off 15 kOhm adds to R6 = 120 kOhm, so the gate amplitude falls to 5.0 mVpp x 120 / 135 = 4.44 mVpp (-11 %) and the MFB response changes. The analyst computes the expected gain, phase and corner from the closed form with R6 = 135 kOhm and reports them.
- **Pass:**
  - P44_ref: the THD of the ideal SIN run is the numerical floor. It must be at least 10 dB below the expected staircase THD (below 0.010 % for N = 128). If not, the dispatcher tightens the solver options (RELTOL, VNTOL, maximum step) and records the change in `docs/simulation-quirks.md`.
  - P44a: gate amplitude and the image within 1 % and 1 dB of the table, and THD within ±20 % of the table, or within the floor of P44_ref.
  - Requirements: N = 128 at 12 bit meets gate THD at most 0.3 % (AN-7b via LIA-Readout), 5.0 mVpp within 1 % (AN-4) and image at most -80 dBc (P-26). The analyst states the same for every run, including the code-error Monte Carlo at the 95th percentile.
  - P44b: phase shift within 0.02 deg and image change within 0.5 dB of the expected values. Buffer off: gate amplitude within 1 % of the closed form.
  - P44c: the measured |H| within 0.5 dB of the ideal MFB up to 100 kHz. P-26 found the vendor MFB passes the 66 kHz image 4 dB more than the ideal, so above 100 kHz the measured H is used and the difference is reported.
  - Settling: the fundamental amplitude differs by less than 0.01 % between the two halves of the window.
- **Status:** done, 8 November 2026.
- **Result:** Gate amplitude, phase, THD, settling, the RC runs and the buffer-off run pass. The gate image at N = 128 is -83.1 dBc and meets the -80 dBc requirement. Against the ideal-MFB entry values it fails the 1 dB limit at N = 64 to 256, 8 bit and 1.2 V, but it matches the closed form with the simulated MFB within 0.22 dB (feedthrough into a rising output impedance above 20 kHz, fitted values, as in P-26). The 8-bit mode fails the 0.3 % THD requirement (0.61 %). See [sim-results/P-44.md](ti-pspice/docs/sim-results/P-44.md).
- **Grade:** A (Opus judge, 8 November 2026). All numbers reproduced by the script and checked independently (N = 128 gate 5.0019 mVpp, THD 0.0309 %, image -83.09 dBc, buffer off 4.4462 mVpp). The image FAILs are shown to be ideal-MFB expectation errors (GOUT output-stage feedthrough), and the EXC_DAC, window and floor differences are explained.

---

## Manual actions needed before the planned runs

| For | Action in Capture |
|---|---|
| All runs | Keep the PSpice (Probe) window closed while agents simulate. Capture itself may stay open. |
| P-04 to P-07 | Done on 27 October 2026, 14:38. Frozen as `circuits/lia_v2*.cir`. Note that the schematic default is fin = 518 Hz and Vharm_ampl = 1 V, so a GUI run of `lia_sanity` now includes a mismatch and a harmonic. |
| Optional | Set the V6 delay to `{0.25/f_osc}`, so the Y reference follows `f_osc`. This removes the 0.18 deg error. |
