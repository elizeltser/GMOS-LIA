# Simulation index

This file lists every simulation of the project, finished or planned. Each entry states the goal, the schematic that runs, the simulation parameters and the expected results. Below those it records the status, the result and the grade. The workflow that fills these entries is described in `CLAUDE.md` under "Simulation workflow".

Identifiers: `C-xx` are completed simulations, `P-xx` are planned ones. A planned entry keeps its identifier when it is completed. The detailed results of each run are in `docs/sim-results/<ID>.md`.

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
- **Result:** Runs A and B agree within 0.1 mV after the `.IC` tail correction. The VY offset of +0.99 mV is explained by a 235 ns Y switching delay from the slew-limited demodulator, and VX stays +0.46 mV, an open point. See [sim-results/P-01.md](sim-results/P-01.md).
- **Grade:** A (judge, 27 October 2026). Both pass criteria met. The VY deviation is explained to 0.014 mV by measured switch and slew delays, and the 0.097 mV settling bias is derived independently. The VX deviation of +0.46 mV stays an open point, which is stated honestly.

### P-02 Input phase sweep

- **Goal:** verify that X and Y respond as cos and sin of the input phase over a full turn, and that the magnitude is independent of phase.
- **Schematic:** `circuits/lia_baseline.cir`.
- **Parameters:** defaults, ost = 0, `.STEP LIN PARAM p 0 360 15` (25 runs, about 20 min if one 1 s run takes about 45 s).
- **Expected:** VX = 2.5 - 1.2732 cos(p) and VY = 2.5 + 1.2732 sin(p - 0.18 deg). R = 1.2732 V at every step. The measured phase, atan2(VY - 2.5, 2.5 - VX), equals p - 0.18 deg. Pass limits: R within 0.5 %, phase within 1 deg.
- **Judge note from P-01:** at p = 0 the Y channel has an extra effective delay of about 235 ns (0.044 deg at 517 Hz). About 99 ns of it is op amp slew, which scales with the step at each edge, |4 V x sin(input phase at the edge)|. Each channel has this slew term, and it is largest when that channel switches near the input peaks. A delay makes the reference act later, so it reduces the Y lag: the phase at p = 0 is d - 0.044 deg (corrected by the judge after P-02, the first version of this note gave the wrong sign). The phase error is expected to vary with p by a few hundredths of a degree. The X channel shows the same effect near p = 90 deg. The analysis should fit and report this variation.
- **Status:** done, 27 October 2026.
- **Result:** R = 1.272742 V in both channels, 0.039 % below K, the same at every phase (spread 0.005 %). Both pass limits met: R within 0.2 % of K, and phase within 1 deg (0.23 deg of p - d, 0.05 deg of the ideal atan2 value). The residual shows a slew delay of the form sin p |sin p| (X) and cos p |cos p| (Y), with coefficient 0.48 mV against 0.41 mV predicted. The Y phase at p = 0 follows d - 0.044 deg, not d + 0.044 deg as the first judge note said. See [sim-results/P-02.md](sim-results/P-02.md).
- **Grade:** A (judge, 27 October 2026). Both pass criteria met at all 25 steps. The judge re-ran the script and got the same numbers, and checked VX at p = 90 deg (+0.98 mV) against the fitted phase and slew terms (+0.99 mV). The analyst correctly found the judge note's sign error. The command was reconstructed from the runner's circuit copy, and an unverified RON estimate was removed. The 0.039 % common gain deficit and the 17 % excess slew coefficient remain stated open points. Update: the gain deficit was later traced to the 20 us time step (P-05 time-step check, +0.007 mV at 2 us).

### P-03 Offset sweep and dynamic range

- **Goal:** find the input offset range over which the outputs stay correct, and describe the behaviour once the signal reaches the rails.
- **Schematic:** `circuits/lia_baseline.cir`.
- **Parameters:** defaults, p = 0, `.STEP LIN PARAM ost -2 2 0.1` (41 runs, about 30 min). A second, shorter sweep at p = 90 deg with ost -2 to 2 in steps of 0.25 checks the Y channel.
- **Expected:** the input spans vdc/2 + ost - 2 V to vdc/2 + ost + 2 V. It stays inside 0 V to 5 V while |ost| <= 0.5 V. In that range VX = 1.2268 V and VY = 2.4960 V, independent of ost. Beyond it, the op amps and the switch path clip, and VX moves towards 2.5 V. The analysis reports the ost value where VX departs from its flat value by more than 1 mV on each side. The analysis also plots `max(V(VX))` against ost next to the settled mean, for comparison with the GUI plot of C-07.
- **Status:** done, 27 October 2026.
- **Result:** VX and VY stay within 1 mV of their ost = 0 values for |ost| up to 0.5 V (P03a, VX and VY) and up to 0.5 V to 0.75 V (P03b, p = 90 deg). The steady demodulator output follows theory up to |ost| = 0.4 V, then sits on a floor (0.01 V to 0.02 V) or a ceiling (4.98 V to 4.99 V) from |ost| = 0.5 V. The output-stage swing is the limit the data show. Input-side limits are not separated. The absolute 50-period extremes come from reference-edge transients and are not the steady range. The 1f ripple of 3.92 mV per V of offset is derived and matches the measurement. Two asymmetries (VY at p = 0, VX at p = 90) stay open. See [sim-results/P-03.md](sim-results/P-03.md).
- **Grade:** A (judge, 27 October 2026, after one revision from B). The flat range of +/-0.5 V is met on both runs. Steady demodulator extremes now match theory within 10 mV, and the switching overshoots (0.37 V, under 1 us) are separated from them. The 1f ripple matches the derived 3.92 mV per V within 0.2 %, and the judge reproduced it. The limiting element (switch, op amp input or op amp output) and two small asymmetries stay open, because those nodes were not probed. The summary states what is missing.

### P-04 Dynamic range versus input amplitude

- **Goal:** check that VX - 2.5 V is proportional to the input amplitude, and find the largest amplitude before clipping.
- **Schematic:** `circuits/lia_v2.cir`, a frozen copy of the netlist of 27 October 2026, 14:38. In this netlist V4 is `SIN {Vdc/2+ost} {Vampl} {fin} 0 0 {p}`, V7 is `SIN 0 {Vharm_ampl} {f_osc*n_harm} 0 0 {p}` in series with V4, and the 2.5 V reference is V8 = `{Vref}`. The copy sets fin = 517 Hz and Vharm_ampl = 0, so it equals `lia_baseline.cir` at Vampl = 2 V.
- **Parameters:** defaults, p = 0, ost = 0, `.STEP PARAM Vampl LIST 0.01 0.03 0.1 0.3 1 1.5 2 2.25 2.5 2.75 3`.
- **Expected:** VX - 2.5 V = -(2/pi) x amp, for example -6.37 mV at 10 mV and -1.2732 V at 2 V. The response stays linear up to amp = 2.5 V, where the signal touches the rails. At small amplitudes, the switch charge injection and the op amp offset set the floor. The analysis reports that floor.
- **Status:** done, 27 October 2026.
- **Result:** VX - 2.5 V is linear with amplitude. The fitted offset is below 0.01 mV, and the 0.46 mV deviation at 2 V is a gain error of -0.037 %, not an offset. The VY channel has a square-law term of 0.114 mV/V^2, close to the slew prediction. The 0.97 mV VY error at 2 V is a constant lag of 0.0234 deg (126 ns) plus the slew part (111 ns), which sums to the 235 ns of P-01. The largest amplitude within 1 mV and 0.1 % is 2.5 V, and the first failure is at 2.75 V, where the demodulator floor clips. The upper edge drop is not closed (1.8 mV per V measured, 1.55 mV per V predicted). See [sim-results/P-04.md](sim-results/P-04.md).
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
- **Result:** at 2 us the VX deltas for n = 3 and 7 are -42.44 and -18.18 mV, against theory -42.44 and -18.19 mV. The VX loss of the 20 us run (0.31 % at n = 3) is the maximum-step error. The VX rejection follows 1/n within 0.01 dB, at -9.54 and -16.90 dB. VY deltas are +0.261 and +0.259 mV, within 0.01 mV of the timing plus slew theory (+0.25 mV). The +0.018 mV VX offset of the 20 us even run disappears at 2 us. VY does not follow 1/n, because the Y timing error gives the same error per volt for every odd n. The 20 us table is kept in the summary. See [sim-results/P-05.md](sim-results/P-05.md).
- **Grade:** A (judge, 27 October 2026, after the time-step check). At 2 us every check passes. VX follows 1/n within 0.04 %. VY odd-harmonic responses match the Y timing model within 0.01 mV. Even harmonics are rejected to below 0.01 mV. The analyst's open point on the growing VX deficit led to the time-step finding, which the 5 us and 2 us runs confirmed. It also explained the gain deficit of P-01 to P-04. The analyst correctly noted that VY moves by 0.015 mV with the step, against the judge's claim of no change. The convergence is slower than the h^2 model, probably because PSpice uses smaller steps near the switch edges. This and the residual of 0.001 to 0.004 mV stay stated open points. The judge reproduced the convergence table.

### P-06 Non-harmonic interference using V7

- **Goal:** check that an interferer at a frequency that is not a harmonic gives no DC error, only a filtered ripple.
- **Schematic:** as P-05.
- **Parameters:** defaults, Vharm_ampl = 0.2 V, `.STEP PARAM n_harm LIST 0.096711799 1.160541586` (50 Hz and 600 Hz).
- **Expected:** no change in the settled means beyond 0.1 mV. The ripple appears at |f_i - n f_osc| for odd n. For 50 Hz the main products are at 467 Hz and 567 Hz. Each has an amplitude of about (2/pi) x 0.2 V = 127 mV before the filter. The RC filter attenuates them to about 0.43 mV (at 467 Hz) and 0.36 mV (at 567 Hz). For 600 Hz the nearest product is at 83 Hz, giving about 2.4 mV of ripple.
- **Status:** done, 27 October 2026. **Result:** settled means change by at most 0.022 mV (limit 0.1 mV). The fitted amplitudes match the expected ones with ratios from 0.994 to 1.000, and the Y phases follow the 482.6 us reference delay. See [sim-results/P-06.md](sim-results/P-06.md).
- **Grade:** A (judge, 27 October 2026). Every expected item passes. The DC shifts are within 0.1 mV, and the 467 Hz, 567 Hz and 83 Hz products match theory within 0.1 %. The window residual is quantified, and the means are cross-checked with a least-squares fit. The judge reproduced the numbers. The remaining shifts of 0.02 mV and the 0.2 % to 0.6 % low ripple at 1 kHz are below the limits. They may come from the time step (see the P-05 judge note).

### P-07 Frequency mismatch (optional)

- **Goal:** show the output when the input frequency differs slightly from the reference.
- **Schematic:** `circuits/lia_v2_fin518.cir` (as `lia_v2.cir` with fin = 518 Hz). V4 is the input at Vampl = 2 V and 518 Hz. The references stay on `f_osc` = 517 Hz.
- **Parameters:** `.TRAN 0 3 0 20u SKIPBP`, no `.IC`, NUMDGT = 8.
- **Expected:** VX and VY beat at 1 Hz around 2.5 V. The amplitude is 1.2732 V x |H(1 Hz)| = 1.2732 V / sqrt(1 + (2 pi x 1 Hz x 0.1 s)^2) = 1.078 V. The beat is 90 deg out of phase between X and Y.
- **Status:** done, 27 October 2026.
- **Result:** beat amplitude 1.07765 V (VX) and 1.07764 V (VY), 0.041 % and 0.043 % below the ideal 1.07809 V and within 0.004 % of the calibrated model. Beat frequency 1.000 Hz within 3 ppm, X minus Y phase -89.82 deg as expected. The 1035 Hz ripple is 1.956 mV against 1.958 mV expected. The 0.035 % time-step error is visible at this precision. See [sim-results/P-07.md](sim-results/P-07.md).
- **Grade:** A (judge, 27 October 2026). Every expected item passes: the amplitude, the 1 Hz beat, the 90 deg X-Y phase, the 32.1 deg filter lag and the start transient. The analyst correctly found that at fin = 518 Hz the 2f ripple splits into 1035 Hz (1.958 mV) and 1033 Hz (0.654 mV) lines. In the 517 Hz case these merge into the 1.304 mV seen in P-01. The 0.04 % amplitude deficit matches the 20 us time-step error. The judge reproduced the fits. A 0.02 deg beat phase offset stays an open point.

---

## Manual actions needed before the planned runs

| For | Action in Capture |
|---|---|
| All runs | Keep the PSpice (Probe) window closed while agents simulate. Capture itself may stay open. |
| P-04 to P-07 | Done on 27 October 2026, 14:38. Frozen as `circuits/lia_v2*.cir`. Note that the schematic default is fin = 518 Hz and Vharm_ampl = 1 V, so a GUI run of `lia_sanity` now includes a mismatch and a harmonic. |
| Optional | Set the V6 delay to `{0.25/f_osc}`, so the Y reference follows `f_osc`. This removes the 0.18 deg error. |
