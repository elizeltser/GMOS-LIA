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

### Batch 2: fault injection, full chain and front-end checks (requested 27 October 2026)

The user asked for nine further tests (P-09 to P-17). P-08 first validates the fast settings that most of them use. The new circuits are:

| Circuit | Content |
|---|---|
| `circuits/lia_v3_fast.cir` | `lia_v2.cir` with output capacitors `{cout}` (default 1 uF) and fault-injection parameters: `rser` (series resistance at the demodulator input), `dr1` (relative change of R1), `vos` (source in series with IN+ of U2 and U4), `aref`/`pref` (ripple on Vref), `kref` (0: ideal Vref, 1: Vref = V(VDC)/2 through an ideal buffer), `arail`/`prail` (ripple on the 5 V source), `rrail` (rail source resistance) and `iexc` (square excitation current drawn from the rail during the first half period, in phase with the X reference). Defaults reproduce `lia_v2.cir` apart from `cout`. |
| `circuits/chain_ss.cir` | Full chain on one 0 V to 5 V rail: sensor stand-in, INA828 (G = 11 V/V, REF = 2.5 V), Sallen-Key high-pass and low-pass with their ground returns moved to the 2.5 V reference, and the X/Y demodulator. Each INA828 input is biased to 2.5 V through 100 kOhm (D-02). The sensor model is TBD (`docs/design-context.md` section 1), so the stand-in is a floating differential source: sine `asin`, square `asq`, gated burst `aburst`, common mode `vcm`, DC differential `vdiff`, series resistance `rsens` per leg. |
| `circuits/frontend_mc.cir` | The front end of `chain_ss.cir` alone, with toleranced R and C models for a Monte Carlo AC run. |

Fast settings (used where an entry says "fast"):

| Setting | Value | Reason |
|---|---|---|
| Output capacitors | `cout` = 1 uF, so tau = 10 ms | Settling is most of the run time. The demodulator itself is unchanged. The 2f ripple grows 10 times, but the measurement is a whole-period mean. |
| Analysis | `.TRAN 0 0.15 0 5u SKIPBP` (`lia_v3_fast.cir`). `chain_ss.cir` runs without `SKIPBP`, so that the high-pass capacitors start from the bias point. | 15 tau. 5 us leaves a 0.003 % gain error at the fundamental (P-05 time-step check). |
| Initial conditions | `.IC V(VX)=2.5 V(VY)=2.5` | As the defaults. |
| Measurement window | Mean of the last 20 whole periods (38.68 ms at 517 Hz), from 111.3 ms | The settling bias of this mean is about abs(V - 2.5 V) x (tau / 38.68 ms) x exp(-11.13) = 3.8e-6 x abs(V - 2.5 V), so 4.8 uV at 2 V amplitude and below 0.5 uV at 0.2 V. Every fault test below is a difference against a baseline step of the same run, so this bias cancels further. |
| Signal level | Vampl = 0.2 V unless stated | Close to the Draft demodulator input of `docs/design-context.md` section 4 (about 166 mV), as D-09 recommends. Then 2A/pi = 127.324 mV. |
| Precision | `.OPTIONS NUMDGT=8` | Most expected effects are 0.05 mV to 2 mV. |

Setting a non-default parameter: PSpice allows one `.STEP` per run. Other non-default parameters are set by an edited copy of the circuit in the run folder or by `--extra ".PARAM ..."`. The dispatcher checks which works and records the result in `docs/simulation-quirks.md`.

### P-08 Validation of the fast settings

- **Goal:** confirm that the fast settings give the same settled VX and VY as the 1 s, 10 uF runs, so that P-09 to P-17 can use them.
- **Schematic:** `circuits/lia_v3_fast.cir`, all fault parameters at their defaults.
- **Parameters:** fast, p = 0, ost = 0, `.STEP PARAM Vampl LIST 0.2 2`. Probes V(VX), V(VY).
- **Expected:** at Vampl = 2 V the reference is P04_step5u (same 5 us step, 10 uF, 1 s): VX = 1.2268012 V and VY = 2.4969886 V ([sim-results/P-05.md](sim-results/P-05.md)). The fast run should agree within 0.02 mV in both channels. At 0.2 V, VX - 2.5 V = -127.324 mV within 0.01 mV, and VY - 2.5 V is close to -0.40 mV (the 0.18 deg Y timing error) plus a slew term that scales with A^2 and is below 0.01 mV here. The 2f ripple at VX is about 10 times the 1.3 mV of P-01 at 2 V, so about 13 mV peak. Pass: both channels within 0.02 mV of the reference at 2 V, and a measured settling bias of the window below 0.005 mV (compare the last 20 periods with the 20 periods before them, scaled by exp(-38.68 ms / tau)).
- **Status:** done, 27 October 2026.
- **Result:** at 2 V the fast VX and VY agree with the reference within 0.015 mV and 0.001 mV (corrected means). The 2 V settling bias is 4.7 uV. At 0.2 V, VX - 2.5 V = -127.3248 mV (0.001 mV from ideal). VY - 2.5 V = -0.344 mV, which is 0.053 mV above the -0.40 mV expected here. The expectation omitted the 126 ns lag and the slew term. With them, the model gives -0.340 mV (0.004 mV residual). The 2f VX ripple is 1.31 mV at 0.2 V and 13.06 mV at 2 V, so the 13 mV expectation holds only at 2 V. See [sim-results/P-08.md](sim-results/P-08.md).
- **Grade:** A (judge, 27 October 2026). Every pass criterion is met: 2 V agreement within 0.015 mV and 0.001 mV, and a 4.7 uV settling bias. The judge re-ran the script and got the same numbers. The two "fail as written" lines are errors of the entry, not of the run. The judge's VY expectation omitted the P-04 lag and slew terms, and the 13 mV ripple was the 2 V value. With the P-04 model, VY at 0.2 V agrees within 0.004 mV. The fast settings are accepted for P-09 to P-17. The 0.024 mV VY model residual at 2 V (mostly the 20 us origin of the P-04 constants) stays an open point.

### P-09 Full chain on a single 5 V rail

- **Goal:** run the sensor stand-in through the INA828, both filters and the demodulator on one 0 V to 5 V rail. Check the INA828 input and output against its supply limits and check that its inputs sit at 2.5 V.
- **Schematic:** `circuits/chain_ss.cir`, asin = 15 mV (the C-06 level, Draft in `docs/design-context.md` section 4), rsens = 1 mOhm, vcm = 2.5 V.
- **Parameters:** run P09a: fast, `.TRAN 0 0.15 0 5u` (bias point on), `.STEP PARAM p LIST 0 90`. Probes V(INP), V(INN), V(VDIFF), V(HPF), V(VSAMPLE), V(VX), V(VY). Run P09b: `.DC LIN PARAM vcm 0 5 0.02` with vdiff = 10 mV and asin = 0, probes V(VDIFF), V(HPF), V(INP). P09b finds the common-mode range of the INA828 model on this supply.
- **Expected:** the ideal front-end transfer function of `ti-pspice-PSpiceFiles/differential-amplifier/README.md` section 3 gives |H(517 Hz)| = 11.079 V/V and a phase of +1.63 deg. Its phase slope is -0.442 deg/Hz. P09a:
  - DC level of INP and INN: 2.5 V within 1 mV (the INA828 bias current times 100 kOhm). VDIFF, HPF and VSAMPLE DC levels: 2.5 V within 5 mV (op amp and INA828 offsets). VSAMPLE amplitude 15 mV x 11.079 = 166.19 mV within 0.5 %.
  - The INA828 output swing is +/-166 mV around 2.5 V, far inside the rails. The INA828 input common mode is 2.5 V, which leaves about 0.5 V to the limits quoted in D-02 (about 2 V from each rail, to be confirmed by P09b and the reviewer).
  - At p = 0: VX - 2.5 V = -(2/pi) x 166.19 mV x cos(1.63 deg) = -105.76 mV, and VY - 2.5 V = +3.01 mV minus the Y timing term (0.18 deg x 105.8 mV = 0.33 mV). At p = 90 deg: VX - 2.5 V close to +3.0 mV and VY - 2.5 V close to +105.76 mV. R = 105.80 mV at both phases. Pass limits: R within 0.5 % of 105.80 mV, and the measured front-end phase within 0.5 deg of +1.63 deg after the Y timing correction. The INA828 and op amp bandwidths are not in the ideal model. The analyst reports their extra phase.
  - P09b: VDIFF stays at 2.5 V + 110 mV (11 x 10 mV) within 1 mV over a common-mode window. The analyst reports the vcm range where it holds within 1 mV and compares it with D-02. If the model does not limit the common mode at all, the analyst says so, because then the simulation cannot show the D-02 risk.
- **Status:** done, 27 October 2026.
- **Result:** front-end gain 11.073 V/V (-0.055 % against 11.079 V/V) and phase +1.50 deg (-0.13 deg against +1.63 deg). R = 105.73 mV at p = 0 deg and 105.74 mV at p = 90 deg, -0.06 % against 105.80 mV, pass. The last-window settling bias is 0.45 uV, so the run is settled. The dispatcher's 2.402 V is a whole-run mean. The VDIFF value stays within 1 mV of 2.61 V for vcm from 2.02 V to 2.98 V, with clamp edges at 2.00 V and 3.00 V (consistent with D-02, datasheet not verified). See [sim-results/P-09.md](sim-results/P-09.md).
- **Grade:** A (judge, 27 October 2026). Every stated criterion passes: input bias 2.5 V, stage offsets below 0.25 mV, amplitude -0.055 %, R -0.06 % and phase -0.13 deg (limit 0.5 deg). The judge re-ran the script and confirmed that the dispatcher's 2.402 V was a whole-run mean, not a settling problem. The INA828 model clamps the input common mode at 2 V from each rail. On 5 V this leaves 2.0 V to 3.0 V, so the 2.5 V bias has 0.5 V of margin on each side, and the D-02 risk is visible in simulation. The 0.055 % gain and 0.13 deg phase deficit against the ideal filters are localised by stage, but their cause is not identified (not verified against the amplifier bandwidths). This stays an open point.

### P-10 Coherent pickup on the reference and the rail

- **Goal:** measure the DC error from a ripple at f_osc on Vref, on the 5 V rail, and from an excitation current that loads the rail (D-04).
- **Schematic:** `circuits/lia_v3_fast.cir`, Vampl = 0.2 V, ost = 0, p = 0.
- **Parameters:** fast. Each run steps its own baseline. Probes V(VX), V(VY), V(REF), V(VDC).

  | Run | Fixed settings | `.STEP` |
  |---|---|---|
  | P10a0, P10a90 | kref = 0, pref = 0 or 90 | `PARAM aref LIST 0 1m` |
  | P10b | kref = 0, prail = 0 | `PARAM arail LIST 0 1m` |
  | P10c | kref = 1, prail = 0 | `PARAM arail LIST 0 1m` |
  | P10d | kref = 0, rrail = 1 Ohm | `PARAM iexc LIST 0 10m` |
  | P10e | kref = 1, rrail = 1 Ohm | `PARAM iexc LIST 0 10m` |

  The rail resistance (1 Ohm) and excitation current (10 mA) are test values. The real ones are TBD (`docs/design-context.md` section 1).
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
- **Result:** all 15 checks pass. The reference responses are +0.6366 mV (aref, pref = 0) and -0.6363 mV (pref = 90 deg), and +0.3183 mV with kref = 1. The 10 mA rail step gives -2.5001 mV in the readout of VX. The absolute VY shift is -2.5058 mV, which the Y reference delay of 482.6 us explains. A 1 mV rail ripple couples at 2.6e-4 V/V (-72 dB) into VY and 8.9e-6 V/V (-101 dB) into VX. See [sim-results/P-10.md](sim-results/P-10.md).
- **Grade:** A (judge, 27 October 2026). All 15 checks pass, relative to the mean of V(REF) as defined. The judge re-ran the script. A 1 mV Vref ripple at f_osc gives 0.637 mV of DC error, the full (2/pi) weight. Rail ripple with an ideal reference couples below 0.0003 mV. A reference derived from the rail carries half of it. The entry's P10e VY expectation (0 relative, -2.500 mV absolute) ignored the 482.6 us Y delay. The analyst derived the correct -0.005 mV and -2.505 mV, which match. The entry mixed two limits (0.01 mV and below 0.005 mV). Both hold.



### P-11 Resistor mismatch with input offset

- **Goal:** measure the DC and scale error from a mismatch of R1 against R2 in the X channel (D-05).
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
- **Result:** all eight VX deltas pass (largest difference 0.0004 mV at dr1 = +1 %), and delta VY stays below 0.0002 mV. The VX offset term of -0.153 mV/V at dr1 = 0 is a timing effect of the test bench and the switch model (100 ns reference duty offset and 46 ns switch delay asymmetry). It is not the op amp or the switch on-resistance. It changes the deltas by at most 0.0008 mV. See [sim-results/P-11.md](sim-results/P-11.md).
- **Grade:** A (judge, 27 October 2026). All 16 deltas pass within 0.0005 mV of (delta/2)(ost + 2A/pi). The judge re-ran the script. The analyst explained the extra -0.153 mV per V of ost at dr1 = 0 with diagnostic runs: -0.103 mV/V from the reference duty (the PULSE width is counted after the 100 ns rise, so the -1 state lasts T/2 + 100 ns, which the judge checked: -2 x 100 ns / T = -0.103 mV/V) and -0.048 mV/V from unequal switch delays (41 ns and 87.5 ns) in the behavioural switch model. It does not affect the mismatch deltas. It also explains most of the P-03 offset slope (-0.148 mV/V).

### P-12 Driver output impedance at the demodulator input

- **Goal:** measure the gain and phase error when the demodulator input node is driven through a series resistance (D-06).
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
- **Result:** VX deltas and gain errors match theory. VY at 1 kOhm is -0.458 mV, against -0.482 mV in the entry, because the entry omits the Y edge delay. With the 235 ns delay of P-01 the theory gives -0.456 mV. Node steps are eps (Vin - Vref) at the Y edges only. See [sim-results/P-12.md](sim-results/P-12.md).
- **Grade:** A (judge, 27 October 2026). Every X delta and gain error matches the exact theory within 0.002 mV (-0.0998 %, -0.985 %, -8.71 %). The judge re-ran the script and got the same numbers. The VY value at 1 kOhm fails the entry as written (-0.458 mV against -0.482 mV), but the entry omitted the Y timing error. With the 235 ns Y delay the exact theory gives -0.456 mV. The "2 eps" node step in the entry was wrong: the node gain is 1/(1 + 2 eps) when both channels are in the -1 state, but a visible step occurs only at the Y edges, because the X edges fall at zero input. The analyst found both entry errors. Note for the reviewer: 10 Ohm already reaches the 0.1 % Draft major threshold.

### P-13 Op amp offset

- **Goal:** confirm that an offset at the non-inverting input of the demodulator op amp appears doubled at the output.
- **Schematic:** `circuits/lia_v3_fast.cir`, Vampl = 0.2 V, ost = 0, p = 0. The source `vos` is in series with IN+ of both U2 and U4.
- **Parameters:** fast, `.STEP PARAM vos LIST -25u 0 25u` (sorted, because the order `0 25u -25u` was rejected, see the `.STEP LIST` quirk in `docs/simulation-quirks.md`). Probes V(VX), V(VY).
- **Expected:** the output is (1 + R1/R2)(V+ + vos) - (R1/R2) Vin in both states, so the offset adds 2 vos. Delta VX = delta VY = +50 uV at vos = 25 uV and -50 uV at -25 uV. Pass: within 2 uV. The analyst also reports the offset already present at vos = 0 (the model's own offset), from the residual against theory.
- **Status:** done, 27 October 2026.
- **Result:** the shift is -2 vos in both channels, so the magnitude matches 2 vos within 0.16 uV (limit 2 uV). The entry's +2 vos sign does not match the netlist orientation. Model offset at vos = 0: -0.89 uV in VX and -3.95 uV in VY against the P-08 model. See [sim-results/P-13.md](sim-results/P-13.md).
- **Grade:** A (judge, 27 October 2026). The magnitude is 2 |vos| within 0.16 uV in both channels. The sign is reversed against the entry because the test source V_VOSX N00695 N00695P {vos} puts IN+ at the switch output minus vos. This is an error of the judge's fixture orientation, not of the circuit. The physics (gain 2 from IN+ to the output in both states) is confirmed. The judge re-ran the script. The model's own offset is below 2 uV input-referred in both channels.

### P-14 Filter tolerance Monte Carlo

- **Goal:** find the spread of the front-end phase and gain at f_osc for given component tolerances, and compare the error of reading X alone with the error of reading R (D-08).
- **Schematic:** `circuits/frontend_mc.cir`. Resistors 1 % and capacitors 5 %, uniform. These are test values. The tolerances are TBD in `docs/design-context.md` section 6.
- **Parameters:** `.AC LIN 1 517 517`, `.MC 500 AC VP([VSAMPLE]) YMAX OUTPUT ALL SEED=17`, `.OPTIONS NUMDGT=8`, run P14_mc2 (1638 s). The run gives 499 random samples (Pass 2 to Pass 500) plus the nominal section. Both CSDF columns hold the complex V(VSAMPLE), so VP and VM are derived from it (deg and V/V).
- **Expected:** a numpy Monte Carlo of the ideal transfer function (200 000 samples, same tolerances, RG included) gives:

  | Quantity | Mean | Std | 2.5 % to 97.5 % |
  |---|---|---|---|
  | Phase shift from nominal | +0.10 deg | 3.36 deg | -6.40 deg to +6.67 deg |
  | Gain error, R | -0.13 % | 3.59 % | -6.86 % to +6.77 % |
  | Gain error, X alone (phase not corrected) | -0.30 % | 3.60 % | -6.97 % to +6.69 % |
  | Extra error of X over R | -0.17 % | 0.23 % | -0.82 % to 0 % |

  The nominal run should give |H| = 11.079 V/V and +1.63 deg (P-09). With 500 runs the sampled standard deviation has a relative uncertainty of about 3 %, so the PSpice phase std should fall in 3.1 deg to 3.6 deg. The analyst stores the numpy script in `docs/sim-results/scripts/P-14_mc.py`. Pass: phase std and gain std within those bands. The analyst states that the gain spread affects X and R equally, and that computing R removes only the extra X error.
- **Status:** done, 27 October 2026.
- **Result:** 499 samples. Phase std 3.443 deg (band 3.1 to 3.6 deg, pass). Gain std 3.617 % (R) and 3.635 % (X), both in the 3.48 % to 3.70 % band, pass. Nominal 11.0732 V/V and +1.518 deg, 0.055 % and 0.11 deg below the ideal values, the same offset as P-09. With the entry's definition (phase calibrated at nominal) the extra X rows agree within 2 standard errors: PSpice -0.180 % (mean), 0.246 % (std), -0.884 % (2.5 %) against entry -0.17 %, 0.23 %, -0.82 %, and numpy reproduces the entry. A total-phase reading (not calibrated) gives about 0.04 % more negative values. See [sim-results/P-14.md](sim-results/P-14.md).
- **Grade:** A (judge, 27 October 2026, after one revision from B). Phase std 3.44 deg and gain std 3.62 % are inside their bands. With the entry's definition (phase calibrated at the nominal circuit), the extra X error of -0.180 % mean, 0.246 % std and -0.88 % at 2.5 % matches the reference within 2 standard errors. The judge recomputed these from the CSDF. The first version used the uncalibrated total phase and wrongly called the entry inconsistent. That reading is kept as a secondary row. The run has 499 random samples plus the nominal. The nominal offset (-0.055 %, -0.11 deg) is the same as in P-09 and stays open. For the reviewer: about 76 % of samples are beyond the Draft 1 deg phase limit.

### P-15 Noise floor of the front end

- **Goal:** find the output noise density of the front end at f_osc and the smallest sensor amplitude the lock-in resolves.
- **Schematic:** `circuits/chain_ss.cir` with acmag = 1 (AC differential input of 1 V on V_SIN) and asin = 0.
- **Parameters:** `circuits/chain_ss_P15.cir` with acmag = 1 V and asin = 0. The run has cout = 1 uF, so its RC is tau = 10 ms, not 0.1 s. Runs P15a_noise517c (`.AC LIN 1 517 517`) and P15b_noise_dec (`.AC DEC 50 10 100k`, 201 points), each with `.NOISE V([VSAMPLE]) V_SIN 1` (the print interval 1 is needed for the tables), `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5` and probe `V([VSAMPLE])`. The noise tables are in the `.out` files, not in the `.csd`.
- **Expected:** the demodulator multiplies by a +/-1 square wave, which folds the noise at each odd harmonic n f_osc to DC with weight (4 / (n pi))^2 / 2. The band-pass makes the harmonic terms small (|H(3 f_osc)| = 1.39 V/V against 11.08 V/V), so the DC density at VX is about 0.90 x e_out(517 Hz). The analyst computes the exact factor from the AC sweep. The output RC has an equivalent noise bandwidth 1 / (4 tau) = 2.5 Hz for tau = 0.1 s (`docs/design-context.md` section 5). For SNR = 1 the smallest input amplitude is A_min = (pi / 2) x 0.90 x e_out x sqrt(2.5 Hz) / 11.08 V/V, which is about 0.20 x e_out (A_min in V for e_out in V/sqrt(Hz)). The datasheet noise of the INA828 and OPAx192 is not recorded in the project. The analyst compares the .NOISE contributions with the datasheet values and cites them. The demodulator and its 10 kOhm resistors cannot be included in `.NOISE`, because the switches change state. The analyst estimates their noise from datasheet values and states that the estimate is not simulated.
- **Status:** done, 27 October 2026.
- **Result:** fold-down factor 0.9014 (index 0.90). A_min for SNR = 1 is 28.4 nV at 2.5 Hz and 89.8 nV at 25 Hz (front end only). Input-referred noise 12.68 nV/sqrt(Hz). R_R16 gives 8.28 nV/sqrt(Hz), 0.91 of its 4kTR, not exactly 1:1. INA828 datasheet and demodulator values not verified. See [sim-results/P-15.md](sim-results/P-15.md).
- **Grade:** A (judge, 27 October 2026). The exact fold-down factor (0.901) and A_min = 28.4 nV for tau = 0.1 s agree with the entry's formula within 0.25 %. The judge re-ran the script. The judge checked the datasheet values on the TI product pages: INA828 7 nV/sqrt(Hz) and OPA192 5.5 nV/sqrt(Hz). The analyst had recalled 4.5 nV/sqrt(Hz), which a judge note in the summary corrects. The effect on A_min is below 1 %. Main finding: the 5 kOhm gain resistor gives 42.6 % of the output noise power, so a higher in-amp gain lowers the floor. The demodulator noise is an estimate, not simulated.

### P-16 Overload recovery

- **Goal:** measure how long the chain takes to return to within 1 mV after an input burst that drives the INA828 beyond the rails.
- **Schematic:** `circuits/chain_ss.cir`, asin = 15 mV, burst at f_osc of 10 periods (19.34 ms) starting at 50 periods (96.71 ms).
- **Parameters:** fast, `.TRAN 0 0.3 0 2u` (run P16_2u; the 5 us runs P16_overload and P16_gear failed to converge, see `docs/simulation-quirks.md`), `.STEP PARAM aburst LIST 0 0.5`, asin = 15 mV, cout = 1 uF (tau = 10 ms in the run, not 0.1 s), `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`. With 0.5 V differential the INA828 would need +/-5.5 V around 2.5 V, so it clips at both rails. Probes V(VDIFF), V(HPF), V(VSAMPLE), V(VX), V(VY).
- **Expected:** the aburst = 0 step is the reference waveform. Recovery is measured from the end of the burst (116.05 ms) as the time after which the difference from the reference stays below 1 mV.
  - VSAMPLE: each Sallen-Key stage has a Q of about 1, so its envelope decays with a time constant of about Q / (pi f0) = 0.6 ms. From a 2.5 V overload to 1 mV takes about 0.6 ms x ln(2500) = 4.7 ms per stage. A recovery time below 10 ms is expected. A longer time means saturation memory (a coupling capacitor charged during clipping), which the analyst identifies from V(HPF) and V(VDIFF).
  - VX and VY: once VSAMPLE has recovered at time t_VS, the outputs decay as exp(-t / tau). With dV the difference from the reference at t_VS, the recovery time is t_VS + tau x ln(dV / 1 mV). The analyst checks that the measured time matches this within 10 %, and scales the result to tau = 0.1 s (10 times the RC part).
- **Status:** done, 27 October 2026.
- **Result:** VSAMPLE recovers 6.21 ms after the burst (limit 10 ms). VX and VY agree with t_VS + tau ln(dV/1 mV) within 0.05 %, with tau = 10 ms as run. No saturation memory beyond the ms-scale filter time constants. The value scaled to tau = 0.1 s (662 ms) is not simulated. See [sim-results/P-16.md](sim-results/P-16.md).
- **Grade:** A (judge, 27 October 2026). VSAMPLE recovers in 6.2 ms (expected below 10 ms). VX and VY match t_VS + tau ln(dV/1 mV) within 0.05 %, and no saturation memory is found. The judge re-ran the script. The run used tau = 10 ms. The 0.66 s recovery for tau = 0.1 s is an arithmetic scaling, not a simulation, and the analyst says so. The recovery requirement and the overload level are TBD.

### P-17 Square-wave excitation through the band-pass

- **Goal:** check the calibration when the sensor signal is a square wave, whose harmonics pass the band-pass with a different gain and phase.
- **Schematic:** `circuits/chain_ss.cir`, asin = 0, asq = 15 mV (a square of +/-15 mV differential, high in the first half period).
- **Parameters:** fast, `.TRAN 0 0.15 0 2u` (2 us, because harmonics up to the 7th matter, see `docs/simulation-quirks.md`). A second run with asin = 15 mV and asq = 0 at the same step gives the sine calibration. Probes V(VSAMPLE), V(VX), V(VY).
- **Expected:** a square of amplitude A has harmonics (4A / (n pi)) sin(n w t), and the square reference weighs harmonic n by 2 / (n pi). With H(f) the ideal front end, VX - 2.5 V = -(8 A / pi^2) x sum over odd n of |H(n f)| cos(phi_n) / n^2, and VY - 2.5 V = (8 A / pi^2) x sum of s_n |H(n f)| sin(phi_n) / n^2 with s_n = +1 for n = 1, 5, 9 and -1 for n = 3, 7, 11. Numerically (n up to 399): VX - 2.5 V = -132.94 mV, VY - 2.5 V = +5.00 mV and R = 133.03 mV. The fundamental alone gives -134.65 mV. The harmonics therefore lower X by 1.27 %, mostly through n = 3 (|H| = 1.39 V/V, phase -138.5 deg). A calibration that treats the square as its fundamental is off by -1.27 %, which is above the 0.1 % major error threshold (Draft, `docs/design-context.md` section 7). The predicted ratio of the square response to the sine response is (4/pi) x 0.98725 = 1.2570. The Y timing error and the INA828 and op amp bandwidths shift these values slightly. Pass: VX within 0.5 % of -132.94 mV, and the measured ratio within 0.2 % of 1.2570.
- **Status:** done, 27 October 2026.
- **Result:** square/sine VX ratio 1.25700 against 1.2570 (ideal 1.25701), pass. Square VX = -132.872 mV, +0.049 % against -132.94 mV, pass. X shift -1.276 % from the fundamental, above the 0.1 % major threshold. Square VY = +4.326 mV against the entry's +5.00 mV, because the 482.6 us Y timing gives -0.43 mV (ideal 4.570 mV). See [sim-results/P-17.md](sim-results/P-17.md).
- **Grade:** A (judge, 27 October 2026). The square/sine ratio matches 1.2570 to 0.001 %, and square VX is within 0.05 % of the prediction. A calibration that treats the square as its fundamental is therefore 1.28 % off, which is above the Draft 0.1 % major threshold. The judge re-ran the script. The entry's VY of +5.00 mV assumed a Y reference at exactly T/4. With the 482.6 us delay the ideal is +4.57 mV. The remaining -0.24 mV is mostly the -0.13 deg front-end phase deficit found in P-09. A +0.058 mV VY excess above n = 7 stays an open point.

### Batch 3: tests proposed by the batch-2 design review

Entries P-18 to P-22 are the tests R-01 to R-05 of [design-review/2026-10-27_batch2.md](design-review/2026-10-27_batch2.md), taken over by the judge on 27 October 2026 with the reviewer's expected values. Circuit names were renamed from R-0n to the P numbers. P-21 also depends on the switch decision of D-01 and uses assumed TMUX1136 parameters (CS = 10 pF is not from the datasheet).

### P-18 Sensor source impedance, gain loading and noise

- **Goal:** measure the gain and the input-referred noise of the chain when the sensor has a series resistance, with the 100 kOhm bias resistors in place (D-11).
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
- **Status:** planned.

### P-19 Reference tracking with a shared reference node

- **Goal:** show that a ripple at f_osc on one shared reference node (INA828 REF, filter returns, demodulator reference) produces no DC error, and measure the tracking error that is left (D-04).
- **Schematic:** `circuits/chain_ss_P19.cir`, a copy of `chain_ss.cir` in which `V_VREF VREF 0 {vref}` is replaced by `V_VREF0 VREF0 0 {vref}` and `V_RIP VREF VREF0 SIN(0 {aref} {f_osc} 0 0 {pref}) AC 1`, and the parameters `aref=0 pref=0` are added to the `.PARAM` line. acmag = 0, asin = 15 mV (Draft level).
- **Parameters:**
  - Run P19a (linear): `.AC LIN 1 517 517`, probes `V([VSAMPLE])`, `V([VREF])`, `V([VDIFF])`, `V([HPF])`. `V_SIN` AC magnitude 0 (`acmag` = 0).
  - Run P19b (confirmation): fast, `.TRAN 0 0.15 0 5u`, `.STEP PARAM aref LIST 0 1m` with pref = 0, then a second run with pref = 90 deg. Probes `V([VX])`, `V([VY])`, `V([VREF])`, `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`. Readout = VX and VY minus the mean of V(VREF) over the last 20 periods (as P-10).
- **Expected:**
  - Derivation. The in-amp, both filters and the demodulator are referenced to one node, so the demodulator input is Vref + s and the output is Vref +/- s. A ripple a on Vref leaves no DC term. The nodal solution with ideal op amps gives V(VSAMPLE) - V(VREF) = Vd x 11.0793 /1.6300 deg whatever the reference resistance (`docs/design-review/scripts/batch2_calc6.py`). The finite loop gain of the followers (Aol at 517 Hz is 10 MHz / 517 Hz = 19 300) and the INA828 bandwidth (640 kHz at G = 10, a lag of 0.046 deg = 8.1e-4 rad) leave a tracking error of the order of 1e-3.
  - P19a: V(VSAMPLE) - V(VREF) for a 1 V AC ripple is below 2e-3 in magnitude. (For comparison, an isolated demodulator reference would give 1.) Pass: below 2e-3.
  - P19b: delta VX (pref = 0) and delta VY (pref = 90 deg) relative to mean Vref are below 0.005 mV for a 1 mV ripple. The separate-reference result of P-10 is 0.6366 mV, so the improvement factor is at least 127. Pass: both below 0.005 mV, and the ratio to 0.6366 mV is reported.
  - If P19a gives more than 2e-3, the analyst identifies the stage (V(VDIFF) - V(VREF), V(HPF) - V(VREF), V(VSAMPLE) - V(VREF)).
- **Status:** planned.

### P-20 Origin of the -0.055 % and -0.13 deg front-end deficit

- **Goal:** separate the follower models from input capacitance as the cause of the P-09 deficit.
- **Schematic:** `circuits/frontend_mc_nominal.cir` (or `frontend_mc.cir` without `.MC`). Variants as edited copies:
  - P20a: `X_U2` and `X_U3` replaced by ideal buffers `E_U2 HPF 0 N07629 0 1` and `E_U3 VSAMPLE 0 N08020 0 1`. The INA828 stays.
  - P20b: as P20a plus a 6.4 pF capacitor from N07629 to VREF and a 6.4 pF capacitor from N08020 to VREF.
  - P20c: ideal buffers and an ideal in-amp `E_INA VDIFF VREF INP CM 11`. This is the wiring check.
- **Parameters:** `.AC LIN 1 517 517`, `.OPTIONS NUMDGT=8`, probe `VM([VSAMPLE])`, `VP([VSAMPLE])`. Three runs of a few seconds.
- **Expected:** P20c reproduces the analytic values 11.0793 V/V and +1.6300 deg within 0.001 %. P20a gives 11.0794 V/V and +1.570 deg (the INA828 gain of 11.000074 V/V and phase of -0.060 deg from P-09). P20b changes P20a by -0.058 % and -0.034 deg (`docs/design-review/scripts/batch2_calc4.py`), so 11.0730 V/V and +1.536 deg. The measured P-14 nominal is 11.0732 V/V and +1.518 deg.
  - If P20a is already at 11.0732 V/V and +1.52 deg, the OPA192 model causes the deficit. If P20a is at 11.0794 V/V and +1.57 deg and P20b is within 0.02 deg of P-14, the follower input capacitance is the cause.
  Pass: P20c within 0.001 %. The result for P20a and P20b is reported, not judged.
- **Status:** planned.

### P-21 Switch with 5 V part parameters and reference impedance

- **Goal:** rerun the demodulator with the TMUX1136 data of D-01 and measure the effect of charge injection into a reference with finite resistance (D-01, D-09, finding F-A).
- **Schematic:** `circuits/lia_v3_fast_P21.cir`, a copy of `lia_v3_fast.cir` with Vampl = 0.2 V, ost = 0, p = 0, kref = 0, and these edits. The instance lines of `X_U1` and `X_U3` use `RON=2 CS=10P CD=20P QINJ=6P TAU=5N ILK=3P`. `E_REF REF 0 VALUE ...` becomes `E_REF REFB 0 VALUE ...` with a new `R_RREFS REFB REF {rrefs}` and the parameter `rrefs=1m`. CS = 10 pF is an assumption, because the datasheet source-off capacitance was not read. A second copy `lia_v3_fast_P21b.cir` keeps the original switch parameters (QINJ = 0.4P) as the baseline.
- **Parameters:** fast, `.TRAN 0 0.15 0 5u SKIPBP`, `.STEP PARAM rrefs LIST 1m 10 1k 5k`, `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`, probes `V(VX)`, `V(VY)`, `V(REF)`.
- **Expected:** the baseline step (rrefs = 1 mOhm) gives VX - 2.5 V = -127.325 mV and VY - 2.5 V = -0.344 mV (P-08), within 0.01 mV. The DC shift with rrefs is at most Q x 2 f_osc x rrefs (a bound, the sign and exact size depend on the edge order in the model):

  | rrefs | Bound, 6 pC | Bound, 0.4 pC |
  |---|---|---|
  | 10 Ohm | 0.06 uV | 0.004 uV |
  | 1 kOhm | 6.2 uV | 0.41 uV |
  | 5 kOhm | 31 uV | 2.1 uV |

  Pass: the VX and VY shifts relative to the rrefs = 1 mOhm step stay within the bound (+10 %) or 0.002 mV, whichever is larger. The analyst reports the measured value over the bound. The spike at node N00695 is not resolved with the 5 us step and is reported as not measurable. A finding of more than the bound means the charge model of SPDT_PREC differs from the assumption.
- **Status:** planned.

### P-22 DC step at the sensor input

- **Goal:** measure the chain response and recovery to a sudden DC change at the sensor input (baseline shift, switch-on), including the input clipping of the in-amp.
- **Schematic:** `circuits/chain_ss_P22.cir`, a copy of `chain_ss.cir` in which `R_SP SP3 INP {rsens}` is replaced by `V_STEP SP3 SPS PULSE(0 {dvstep} {tstep} 1u 1u 1 2)` and `R_SP SPS INP {rsens}`, with `dvstep=0 tstep=20m` added. asin = 15 mV, cout = 1 uF (tau = 10 ms in the run).
- **Parameters:** `.TRAN 0 0.3 0 2u` (2 us as P-16, because 5 us fails when the in-amp clips), `.STEP PARAM dvstep LIST 0 50m 100m 300m`, `.OPTIONS NUMDGT=8`, `.IC V(VX)=2.5 V(VY)=2.5`, probes `V(VDIFF)`, `V(VSAMPLE)`, `V(VX)`, `V(VY)`.
- **Expected:** the step response of the ideal chain (INA828 gain 11, high-pass and low-pass of the netlist) has a peak of 3.14 V per volt of input step at 0.47 ms, and the output returns to within 1 mV after 5.1 ms (50 mV), 5.2 ms (100 mV). `docs/design-review/scripts/batch2_calc3.py` gives these values.

  | dvstep | VDIFF step (11 x dvstep) | Peak abs(VSAMPLE - 2.5 V) | Time until within 1 mV |
  |---|---|---|---|
  | 50 mV | 0.55 V | 0.157 V | 5.1 ms |
  | 100 mV | 1.1 V | 0.314 V | 5.2 ms |
  | 300 mV | 3.3 V, so VDIFF would reach 5.8 V | about 0.67 V (VDIFF clipped near 4.85 V, 2.35 V step x 0.285) | about 5.6 ms |

  The mean of VX and VY returns to the dvstep = 0 value within 0.01 mV from 240 ms after the step (24 tau). A DC input is rejected by the demodulator mean (0.5 v + 0.5 (2 Vref - v) = Vref). During the transient the VX ripple at f_osc is about 39 mV per volt of VSAMPLE excursion (tau = 10 ms), so 12 mV at the 0.314 V peak. Pass: the VSAMPLE peak within 15 % of the table (the 300 mV row within 30 %), recovery time within 1 ms of the table, and the final VX and VY within 0.01 mV. The analyst reports if the INA828 model clips the step at a value other than 4.85 V.
- **Status:** planned.

---

## Manual actions needed before the planned runs

| For | Action in Capture |
|---|---|
| All runs | Keep the PSpice (Probe) window closed while agents simulate. Capture itself may stay open. |
| P-04 to P-07 | Done on 27 October 2026, 14:38. Frozen as `circuits/lia_v2*.cir`. Note that the schematic default is fin = 518 Hz and Vharm_ampl = 1 V, so a GUI run of `lia_sanity` now includes a mismatch and a harmonic. |
| Optional | Set the V6 delay to `{0.25/f_osc}`, so the Y reference follows `f_osc`. This removes the 0.18 deg error. |
