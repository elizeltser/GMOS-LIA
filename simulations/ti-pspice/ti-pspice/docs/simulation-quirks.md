# Simulation quirks log

This file collects every surprise met while running simulations in this project. The dispatcher agent adds an entry whenever a run fails, needs a workaround or behaves unexpectedly. Read it before running anything. `docs/pspice-workflow.md` explains the tools in full. This file is the short, growing list of traps.

Entry format: a short title, then **Symptom**, **Cause**, **Workaround** and **Source** (the test ID or date, and whether it was verified).

## Running PSpice

### Only one PSpice at a time
- **Symptom:** a run ends after about 1 s with status `exited` and no `.out` file.
- **Cause:** `pspice.exe` is single-instance. A new launch hands its job to any open PSpice window and exits.
- **Workaround:** `tools/run_sim.py` holds a lock and waits until no `pspice.exe` is running. The user's own Probe window also blocks runs, so ask the user to close it. Never kill PSpice by image name.
- **Source:** 26 October 2026, verified.

### Stopping a run leaves the simulation server running
- **Symptom:** after the runner and its `pspice.exe` were stopped, the output files stayed locked and one `SimSrvr.exe` kept using CPU.
- **Cause:** `pspice.exe` hands the job to a `SimSrvr.exe` COM server (parent: the DCOM service host), which does not exit with it.
- **Workaround:** to abort a run, find the `SimSrvr.exe` that is using CPU (sample its CPU time twice) and stop that one by PID. Leave idle servers and never stop by image name.
- **Side effect:** after this, the next run hung. `pspice.exe` started but used no CPU, no `SimSrvr.exe` appeared, and no `.out` was written for an hour. The runner's timeout did not catch it in that time. The cause was the PSpice Simulation Manager (`simmgr.exe`), left in a bad state. Stopping that `simmgr.exe` by PID, and the hung `pspice.exe` and runner, fixed it: a 10 ms smoke run then finished in 10 s. Check first that no Capture or user PSpice window is open.
- **Detecting a hang:** if a run has no `.out` file after a few minutes and its `pspice.exe` uses no CPU, it is hung.
- **Update (27 October 2026, P14_mc2 and P14_mc3):** the runner timeout of P14_mc2 stopped its `pspice.exe`, but `SimSrvr.exe` PID 13380 (started with that job) kept computing at about 100 % CPU. The next run, P14_mc3, started `pspice.exe` and a new `SimSrvr.exe`, both idle. It wrote no `.out` for more than 15 min, which is the hang described above. The agent could not stop the processes by PID, because the permission system denied the action. The cause and the fix are not verified. Avoid a timeout on a long `.MC` run, which leaves an orphan server. Use `--timeout 1800` (see the Monte Carlo entries).
- **Source:** P05_step2u, 27 October 2026, verified. The P14_mc2 and P14_mc3 update: 27 October 2026, verified for the process states, not for the cause.

### Node probes need brackets
- **Symptom:** `ERROR(ORPSIM-16306): Must be a two terminal device`.
- **Cause:** PSpice reads `V(NAME)` as the voltage of a device called NAME.
- **Workaround:** use `V([NAME])`. `run_sim.py` converts `V(NAME)` automatically. Hand-written `.PROBE` lines need the brackets.
- **Source:** 26 October 2026, verified.

### Home-made library through .LIB is not found
- **Symptom:** `ERROR(ORPSIM-15108): Subcircuit SPDT_PREC used by X_U1 is undefined` in a batch run.
- **Cause:** not fully known. The unsigned `tmux6136_beh.lib` loads through `.INC` but not through `.LIB`.
- **Workaround:** `run_sim.py` converts unsigned flat libraries to `.INC` and adds `.OPTIONS FILEMODELSEARCH`.
- **Source:** 26 October 2026, verified.

### Signed TI library through .INC fails
- **Symptom:** `ERROR(ORPSIM-16583): More than one imported model containing transistors or diodes`.
- **Cause:** a signed library (one with a `.LIBsig` file, such as `opax192.lib`) was loaded with `.INC`.
- **Workaround:** keep signed libraries as `.LIB`. `run_sim.py` does this. This error has nothing to do with the number of probes.
- **Source:** 26 October 2026, verified.

### A .PARAM from --extra cannot redefine a name already in the netlist
- **Symptom:** `ERROR(ORPSIM-15089): Can not re-define aref. aref is either a system defined variable or has already been defined`. The run ends with status `error` after about 16 s and writes no `.csd`.
- **Cause:** the netlist already has a `.PARAM` line that defines `aref`. The runner appends `--extra` lines before `.END`, so the second `.PARAM aref=...` is rejected. This applies to every name on the `.PARAM` lines of `lia_v3_fast.cir`.
- **Workaround:** make an edited copy of the circuit with the wanted default in its own `.PARAM` line, and run that copy by path. For aref = 1 mV this is `circuits/lia_v3_fast_aref1m.cir` (only `aref=0` changed to `aref=1m` on the `.PARAM cout=...` line). The copy ran with status `done` in 13 s (run P08_paramtest_copy). V(REF) between 0.5 ms and 2 ms has a peak-to-peak ripple of 1.998 mV, so the amplitude is 1.0 mV. The first run (P08_paramtest) gave the error above. An `--extra` line for a name that is not in the netlist should work, but this was not verified.
- **Update (27 October 2026, Batch 2):** `.STEP PARAM` on a name that the netlist already defines works without any copy. Runs P10a0, P10b, P10c, P10d, P10e, P11p, P11m, P12 and P13 stepped aref, arail, iexc, dr1, rser and vos this way. Only fixed non-default values need a copy (for example vampl=0.2, ost=0.3 or rrail=1).
- **Source:** P08_paramtest (failed) and P08_paramtest_copy (done), 27 October 2026, verified.

### A .STEP LIST must be monotonic
- **Symptom:** `ERROR(ORPSIM-16068): Must be monotonically increasing or decreasing`. The run ends with status `error` after about 15 s to 16 s and writes no `.csd`.
- **Cause:** PSpice rejects a `.STEP PARAM x LIST ...` whose values are not in increasing or decreasing order. The entries P-11 (`LIST 0 1m -1m 10m -10m`) and P-13 (`LIST 0 25u -25u`) do this.
- **Workaround:** give the same values in sorted order, for example `LIST -10m -1m 0 1m 10m` and `LIST -25u 0 25u`. The sorted run gives the same step set. The step order in the `.csd` then changes, so match each section by `section.step_value`, not by its index. Run P11p (`LIST -10m -1m 0 1m 10m`) and P13 (`LIST -25u 0 25u`) finished with status `done` on this workaround.
- **Source:** P11p_mismatch, P11m_mismatch and P13_vos (first attempt, failed in 15 s to 16 s), and their sorted reruns (done), 27 October 2026, verified.

### Orphaned simulation server after an agent is stopped
- **Symptom:** a run seemed stuck. A new run (P14_mc3) held `sim-runs/.pspice.lock` and waited, one `SimSrvr.exe` used a full CPU core for 30 min without writing any file, and the `.out` of an earlier run kept growing with no runner attached.
- **Cause:** stopping a dispatcher agent ends its runner and `pspice.exe`, but not the `SimSrvr.exe` that does the work (see "Stopping a run leaves the simulation server running"). The diverging Monte Carlo attempt P14_mc_opt left a server that never finished. The server of P14_mc2 carried on and finished its job (500 passes, 1638 s), with no runner to close it.
- **Workaround:** sample the CPU time of each `SimSrvr.exe` twice. Match each busy one to a run by its start time and by the run folder whose files are still changing. Stop by PID only the servers whose run is dead. Let a server finish if its `.out` is still growing. Delete the lock file only when its PID (the file content) no longer exists. A 500-pass `.MC` AC run of `frontend_mc.cir` takes about 27 min, longer than the runner's default timeout, so pass a larger `--timeout`.
- **Source:** P-14, 27 October 2026, verified (judge).

## Accuracy

## Accuracy

### No maximum time step gives wrong results
- **Symptom:** LIA outputs 5.6 % below theory. An oscillator ran 6 % slow.
- **Cause:** `.TRAN` without a fourth field lets PSpice take steps of up to 244 us, about one eighth of a period.
- **Workaround:** always give a maximum step, for example `.TRAN 0 1 0 5u SKIPBP`. Even with a step, the error is about (n x 2 pi f x h)^2 / 12 for a signal at harmonic n of f. At 517 Hz the VX gain error is 0.036 % with 20 us, 0.003 % with 5 us and 0.0005 % with 2 us. At the 7th harmonic, 20 us gives 2.0 % and 2 us gives 0.04 %. C-03 saw no difference between 20, 5 and 2 us only because the output had four digits. Use 2u for harmonics or for errors below 0.01 mV.
- **Source:** C-03, and the P-05 time-step check (P04_step5u, P04_step2u, P05_step5u, P05_step2u), 27 October 2026, verified.

### Text output has only four digits
- **Symptom:** values near 2.5 V come out rounded to 1 mV, and the ripple is invisible.
- **Workaround:** add `--extra ".OPTIONS NUMDGT=8"`.
- **Source:** C-03, verified.

### Slow settling of the LIA outputs
- **Symptom:** VX and VY need about 1 s to settle when a run starts at 0 V.
- **Cause:** the RC output filter has tau = 0.1 s, and `SKIPBP` starts the capacitors at 0 V.
- **Workaround:** run 1 s (10 tau) with `--extra ".IC V(VX)=2.5 V(VY)=2.5"`. Verified in P-01: `.IC` is honoured together with `SKIPBP`. In run P01_B_1s_ic, V(VX) and V(VY) start at 2.5000 V at t = 0. The bracket form `V([VX])` was not needed. Run P01_A_2s_from0 (no `.IC`) starts at 0 V and reaches 1.22717 V (VX) and 2.49467 V (VY) at 1.0 s. At 2.0 s it reads 1.22723 V and 2.49478 V. The 1 s run P01_B_1s_ic reads 1.22728 V and 2.49477 V at 1.0 s. The two runs agree within 0.1 mV.
- **Source:** P-01 (27 October 2026), verified for the `.IC` form and for the 1 s settling. The 0.1 s tau behaviour was not fitted.

### Point mean of PSpice output is biased by the adaptive step
- **Symptom:** the arithmetic mean of the saved points differs from the time-weighted mean. In P08_fast at Vampl = 2 V, V(VY) gives 2.5040525 V as a point mean and 2.4969897 V as a time-weighted mean. The point-mean error for V(VY) is 7.1 mV, and for V(VX) it is 0.013 mV.
- **Cause:** PSpice saves points at its internal steps. These are 2.8e-11 s to 5 us apart. The points cluster near the switching edges, so a point mean over-weights the edges.
- **Workaround:** average over time with the trapezoid rule (`numpy.trapezoid` on the time vector, divided by the window length) for any window mean, and do not use the point mean. Check the 1f residual of the window too.
- **Source:** P08_fast (27 October 2026), verified by comparing the point mean and the trapezoid mean of the same window.

### PULSE width is counted after the rise time
- **Symptom:** in P-11 the demodulated output moved by -0.153 mV per V of input offset with matched resistors, where an ideal +1/-1 demodulator gives none.
- **Cause:** a PSpice `PULSE` source is high for TR + PW, not PW. The references V_V2 and V_V6 use PW = 0.5/f_osc with TR = TF = 100 ns, so the -1 state lasts T/2 + 100 ns. This converts an input offset into a DC error of -2 x 100 ns / T = -0.103 mV/V at 517 Hz. Unequal switch delays in the behavioural switch model (41 ns and 87.5 ns) add -0.048 mV/V.
- **Workaround:** use PW = {0.5/f_osc - t_slope} for a 50 % duty. This is a schematic change for the LIA page (user only). Circuits copied from it keep the offset term. It cancels in differences at fixed ost.
- **Source:** P-11 diagnostic runs P11diag_ideal_opamp, P11diag_ron01, P11diag_noqinj, 27 October 2026. The duty term is verified against theory. The schematic fix was not run.

## Netlist and log messages

### VTH is not a parameter of SPDT_PREC
- **Symptom:** `WARNING(ORPSIM-15256): <X_U1.VTH> not a subcircuit param` and the same for X_U3.
- **Cause:** the switch symbol passes `VTH=1.4`, but the model has fixed thresholds of 1.0 V and 1.8 V.
- **Workaround:** none needed. The warning is harmless.
- **Source:** every LIA run, verified.

### Default pulse edges reported although t_slope is set
- **Symptom:** `WARNING(ORPSIM-15459): In device V_V2, default values (TR=1.00e-09, TF=1.00e-09) are used for zero TR and TF`, and the same for V_V6, while the netlist uses `{t_slope}` = 100 ns.
- **Cause:** not known. The warning appears in both P-01 logs, but the measured edge follows the 100 ns setting (see below).
- **Workaround:** none needed for V_V2. In P-01 runs A and B, V(N00261) rises from 10 % (0.5 V) to 90 % (4.5 V) in 80 ns. A linear 100 ns edge over 0 to 5 V gives exactly 80 ns. A 1 ns edge would give 0.8 ns. The saved points near the edge are 1 to 20 ns apart, so the two cases are clearly separated. V_V6 (the Y reference) was not measured, so the warning is only resolved for V_V2.
- **Update (P08_fast, 27 October 2026):** the same warning also appears for the current source `I_IEXC` in `lia_v3_fast.cir`, with the same TR and TF defaults of 1 ns. Its amplitude is `{iexc}` = 0 in the default runs, so it has no effect. The netlist gives the edges as `{t_slope}`, as for V_V2. The edge time of I_IEXC was not measured (not verified).
- **Source:** C-07 log and P-01 (27 October 2026). Verified for V_V2 (N00261). Verified for V_V6 (N01577) in P01_D_edges (28 October 2026): 10 % to 90 % takes 80.00 ns at both the rising and the falling edge.

### Large output files from GUI runs
- **Symptom:** the 41-step GUI sweep C-07 wrote a 2.95 GB `.dat` and took 8672 s (211 s per 2 s step).
- **Cause:** the profile saves all voltages, currents and noise (`.PROBE64 W(alias(*)) NOISE(alias(*))`).
- **Workaround:** batch runs probe only the signals the analysis needs.
- **Source:** C-07, verified.

### Job-time warning for ITL4 with speed levels
- **Symptom:** `WARNING(ORPSIM-16534): Using high values of ITL4 for Speed Level > 0 may increase total simulation job time.`
- **Cause:** not checked. The warning is advisory and comes from the PSpice solver settings.
- **Workaround:** none needed for results. The run P01_D_edges (6 ms to 10 ms, 10 ns maximum step) took 273 s and produced a 52 MB `.csd` file.
- **Source:** P01_D_edges (28 October 2026), verified as harmless (results plausible, no ERROR lines).

### Switch change is too small to measure on some edges
- **Symptom:** in P01_D_edges the X demodulator (VX_DEMOD) moves only 9 mV to 17 mV at the X switch changes, so its 90 % time (about 750 ns) and slew (0.01 V/us) are not meaningful.
- **Cause:** the step of a switch output is the difference between the held level (2.5 V) and the input N00890. At these X edges the input is about 2.5 V, so the step is almost zero. This is physics of the phase, not a simulator fault. The Y edges have a 4 V step.
- **Workaround:** measure the demodulator step only where the input differs from 2.5 V by more than about 1 V. Otherwise report the step as not measurable. Check the step size before quoting a time or slew.
- **Source:** P-01 edge measurement, 28 October 2026, verified from the CSDF values.

### Step value only as text
- **Symptom:** a `.STEP` run's CSDF sections have no numeric step key.
- **Cause:** PSpice writes the step only as text, for example `SUBTITLE='Step param f =  300'`.
- **Workaround:** use `section.step_value` from `tools/csdf.py`.
- **Source:** 26 October 2026, verified.

## Batch 2 circuits (P-09 to P-17)

### Overload burst fails to converge with a 5 us maximum step
- **Symptom:** `ERROR(ORPSIM-15138): Convergence problem in Transient Analysis at Time = .101` (run P16_overload, step aburst = 0.5). The run stops with status `error` at t = 0.101 s, while the burst is active. The time step falls to 2.5e-19 s against a 1e-18 s minimum. The step aburst = 0 reference runs to the end.
- **Cause:** the INA828 and the op amps clip at both rails during the burst. Newton does not converge at the 5 us grid during the clipped interval.
- **Workaround:** a 2 us maximum step (`.TRAN 0 0.3 0 2u`) converges and completes both steps (run P16_2u, status `done`, 176005 and 177368 points). Two other options did not help. `.OPTIONS METHOD=GEAR` (run P16_gear) failed at t = 0.103 s. The bias point and the first 96 ms were fine in every run.
- **Source:** P16_overload (failed), P16_gear (failed) and P16_2u (done), 27 October 2026, verified.

### Monte Carlo bias point fails without the solver options
- **Symptom:** `ERROR -- Convergence problem in bias point calculation` at the first run, with the node voltages far from the operating point (VDC near 3.85 V instead of 5 V). Runs P14_mc and P14_nominal_diag (the same circuit with the `.MC` line removed) both fail in 37 s to 43 s, so the Monte Carlo setup is not the cause.
- **Cause:** `circuits/frontend_mc.cir` had neither `.OPTIONS ADVCONV` nor `.INC "../options.inc"`. `chain_ss.cir` has both and its bias point converges (P09a).
- **Workaround:** the file now has `.INC "../options.inc"` (after the opax192 `.LIB`) and `.OPTIONS ADVCONV` (before `.AC`). With both, the nominal bias point converges and the Monte Carlo starts. `ADVCONV` alone did not fix it (run P14_mc_adv, failed).
- **Source:** P14_mc, P14_mc_adv, P14_nominal_diag (failed) and P14_mc_opt (the nominal run converges, then aborts at MC pass 2), 27 October 2026, verified.

### Monte Carlo sample diverges and aborts the whole run
- **Symptom:** `ERROR -- Convergence problem in bias point calculation` in the pseudo-transient of MC pass 2 (and in later passes). Node voltages of the failed sample reach about -2.6e9 V (HPF and N07629), and VDIFF reaches 940e6 V. The run ends with status `error` after 44 s and the `.csd` is 0 bytes, so no sample is saved.
- **Cause:** the old model wrote the tolerance as `.PARAM tolr=1%` with `DEV={tolr}`. PSpice most likely read `1%` as 1, so the deviation was an absolute 1 on R = 1 (100 %), and some samples got near-zero or negative resistors. This is likely, not verified, because the old form was not re-run. PSpice stops at the first failing sample and does not skip it.
- **Workaround:** write the tolerance literally in the models, `.MODEL RTOL RES(R=1 DEV=1%)` and `.MODEL CTOL CAP(C=1 DEV=5%)`. This is the current form of `circuits/frontend_mc.cir`. Run P14_mc2 with it ran 327 passes (of 500) with no convergence error. Its spread matched numpy: phase std 3.47 deg (numpy 3.36 deg) and gain std 3.55 % (numpy 3.59 %). The run was stopped by the runner timeout, so the full 500 passes are not yet verified.
- **Source:** P14_mc_opt (divergence, 27 October 2026, verified that the run stops and writes no data). P14_mc2 (27 October 2026, verified for 327 passes, no divergence). The cause of the divergence is likely, not verified.

### Monte Carlo CSDF has one AC section per pass
- **Symptom:** `csdf.py --list` shows one section per pass, titled `Monte Carlo NOMINAL` and then `Monte Carlo Pass    2`, `Pass    3` and so on. Each section has one frequency point. `VP(VSAMPLE)` and `VM(VSAMPLE)` both appear only as `V(VSAMPLE)`, twice, with identical values.
- **Cause:** PSpice writes AC results as complex values (`COMPLEXVALUES='YES'`, real/imag pairs). It labels each column by the node and drops the VP and VM prefix, so the two requested probes are the same complex value.
- **Workaround:** read the complex value from the first column of the section and take `abs` for the magnitude and `angle` for the phase. Use the section whose subtitle contains `NOMINAL` as the reference. The `.csd` has no numeric step key (see "Step value only as text"). A timed-out run leaves a truncated last section with no names, so skip it. The analysis script for this is in the scratchpad, not in the project.
- **Source:** P14_mc2 partial `.csd` (327 sections, read with `tools/csdf.py`), 27 October 2026, verified. The count of 500 passes plus the nominal was not verified, because the file was cut off.

### Monte Carlo runs take about 1.9 s per pass
- **Symptom:** run P14_mc2 ended with status `timeout` after 601 s. The `.out` had no `Total job time` and reached `MONTE CARLO PASS 322`. The `pspice.exe` exit code was 0 because the runner stopped it.
- **Cause:** each AC pass takes about 1.9 s, so 500 passes need about 950 s. The runner default `--timeout` is 600 s.
- **Workaround:** pass `--timeout 1800` for `.MC 500`.
- **Source:** P14_mc2, 27 October 2026, verified from the pass count and the timestamps.

### A locked .out stops the runner before the run starts
- **Symptom:** `PermissionError: [WinError 32] ... P14_mc.out` from `tools/run_sim.py` at `os.remove`, and no run.
- **Cause:** the `.out` of an earlier run in the same folder was still held open by a PSpice process after the error exit. No `pspice.exe` was listed. `simmgr.exe` was the only PSpice process found. The holder was not identified (not verified).
- **Workaround:** use a new run name (for example `P14_mc_adv` after `P14_mc`), so the runner uses a new folder. Do not kill processes. The P14 retry under the same name failed twice with this error.
- **Source:** P14_mc (retries), 27 October 2026, verified for the error. The holder is not verified.

### Noise probes are not node names
- **Symptom:** with `.PROBE/CSDF V([VSAMPLE]) V([ONOISE]) V([INOISE])`: `ERROR(ORPSIM-15140): Node ONOISE is undefined` and `ERROR(ORPSIM-15142): Node ONOISE is floating`. With the bare names `ONOISE INOISE`: `ERROR(ORPSIM-16296): Invalid Expression: Specify either current(I) or voltage(V).` Neither form writes a `.csd`.
- **Cause:** the noise outputs are not nodes, and `.PROBE/CSDF` does not take them as bare names in this form.
- **Workaround:** probe only the node voltages (for example `V([VSAMPLE])`), and read the noise from the `.out`. Add a print interval to `.NOISE` (`.NOISE V([VSAMPLE]) V_SIN 1`). Then the `.out` gets a noise table per frequency (device squared noise, `TOTAL OUTPUT NOISE VOLTAGE`, `TRANSFER FUNCTION VALUE` and `Top Contributors To Output Noise`). Without the interval, the tables are not printed. The `.csd` has no noise section.
- **Source:** P15a_noise517 (failed), P15a_noise517b (failed) and P15a_noise517c (done, 23 s), P15b_noise_dec (done, 25 s, 201 tables), 27 October 2026, verified.
