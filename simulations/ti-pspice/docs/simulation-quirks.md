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

### PWL time values cannot be expressions
- **Symptom:** `ERROR(ORPSIM-16352): Time value must not be an expression`, status `error` after about 17 s, no `.csd`.
- **Cause:** a `PWL` source with a time point written as `{max(t15,1n)}` or `{t5+tramp}`. PSpice accepts expressions in PWL values but not in PWL times.
- **Workaround:** use `PULSE` for a single ramp: `PULSE({v*u} {v} {t_on} {tramp} 1 10 20)` ramps from v*u to v at t_on and stays there. `circuits/afe_eval.cir` does this for the bench inputs. A fixed-time PWL from a script (`circuits/gen_exc_stair.py`) works.
- **Source:** smoke_afe_op, 7 November 2026, verified.

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

## Batch 4 circuits (P-23 to P-34, LIA-AFE-Eval)

### Rail diodes of afe_eval.cir use the ESD stand-in model
- **Symptom:** the header of `circuits/afe_eval.cir` says the rail diodes are a B5819W model with IS, N and RS fitted to about 0.3 V at 10 mA. The netlist lines `D_D5`, `D_D10`, `D_D4` and `D_D9` use `DSCHOTTKY`, the ESD stand-in model with IS = 5 uA and N = 1.05. This model gives V_F = 0.177 V at 3.37 mA (P23a, V_F from the node voltages) and 0.206 V at 10 mA (hand value, n Vt ln(I/IS)). The +5VA rail is 0.12 V higher than with a 0.3 V diode.
- **Cause:** the same `.MODEL DSCHOTTKY` line serves the TMUX6136 ESD stand-ins and the rail diodes. The header does not match the netlist.
- **Workaround:** none in the circuit (not edited by the dispatcher). Rail results are valid only for this model. The owner should add a B5819W model and rerun P-23. Until then, +5VA and the heater headroom (P5VP) are not verified against the real diode.
- **Source:** P23a_op and P23b_heat, 7 November 2026, verified from the netlist echo in the `.out` and the arithmetic. The B5819W curve was not read (not verified).

### Bias sweep with .DC PARAM is slow
- **Symptom:** P23c, a `.DC LIN PARAM v5` sweep of 21 points, took 552 s. The single `.OP` of P23a took 28 s, and the two-step heater run P23b took 75 s. The 600 s runner timeout is close.
- **Cause:** not known. Each sweep point repeats the bias solution with the pseudo-transient start.
- **Workaround:** pass `--timeout 1200` for `.DC` sweeps of this circuit.
- **Source:** P23c_sweep, 7 November 2026, verified (status done, 552 s). P33a (47 points of `.DC PARAM vh_a`, three runs) took 1540 s to 1609 s, about 33 s per point, and P33c (59 points of `.DC PARAM vdrc_a`) took 731 s, 7 November 2026, verified (status done).

### .OP with .STEP prints several blocks per step
- **Symptom:** the `.out` of an `.OP` run with `.STEP` contains a "SMALL SIGNAL BIAS SOLUTION" table, then an "OPERATING POINT INFORMATION" block and a "JOB STATISTICS SUMMARY" for each step. A naive search for node voltages finds the device blocks as well.
- **Cause:** PSpice prints the device operating point with each step.
- **Workaround:** parse only the block that starts at "SMALL SIGNAL BIAS SOLUTION" and stops at "OPERATING POINT INFORMATION" (see `docs/sim-results/scripts/P-23_bias.py`).
- **Source:** P23a_op and P23b_heat, 7 November 2026, verified.

### A .DC PARAM sweep moves one bench rail only
- **Symptom:** P23c sweeps `v5` (the +5 V bench input) with `v5n` held at 5.3 V, so the -5 V rail is not swept.
- **Cause:** one `.DC` sweep variable per run, and the bench inputs are two parameters.
- **Workaround:** for a symmetric sweep, a copy of the circuit with `v5n = v5` set in one `.PARAM` line, or a second run with `v5n` swept.
- **Source:** P23c_sweep, 7 November 2026, verified from the sweep table.

### ABSTOL = 1p in a .DC sweep printed no result
- **Symptom:** P23c_abstol (`.DC LIN PARAM v5 4.6 5.6 0.05` with `--extra ".OPTIONS ABSTOL=1p"`, runner timeout 1200 s) never printed a bias solution. Its `.out` stopped growing at 1.04 MB about 5 min after the start, and its `.csd` stayed empty. By 19:46 its `pspice.exe` was gone, and three `SimSrvr.exe` servers stayed idle (CPU time flat over 30 s). They were not stopped, because another agent's run held the lock.
- **Cause:** not known. The same sweep with ABSTOL = 1n completed 21 points in 552 s. The pattern matches the orphaned-server hang already in this log.
- **Workaround:** use ABSTOL = 1p only for single bias points. A single `.OP` at the default state (P23c_op_abstol1p) finished in 46 s, and X_OUT agreed with ABSTOL = 1n to 0.4 uV.
- **Source:** P23c_abstol, 7 November 2026. The stall is verified from the file sizes and the process list. Its cause is not verified. The single-point comparison is verified.

### .OP stops before the slow nodes settle (loose pseudo-transient tolerances)
- **Symptom:** the bias point of afe_eval.cir does not satisfy KCL at node NC13 (C13 is open at DC) or the internal MID nodes of the OPAx196 models. The residue at NC13 is 45 pA (vda = 0) and -267 pA (vda = 10 mV). At the MID node of U1B the residue is +1.2 mV from (V+ + V-)/2, and the other op amps show the same order. The zero-signal X_OUT then depends on the path of the run: -0.030 mV or -0.353 mV at vda = 0 or 10 mV, in the same `.OP` analysis.
- **Cause:** the `.OP` is a pseudo-transient (`.OPTIONS ADVCONV`). `options.inc` sets PTRANABSTOL = 1e-5 and PTRANVNTOL = 1e-4, which are loose for these nodes. The pseudo-transient stops before the slow nodes settle. The OPAx196 model has an internal MID node with tau of about 0.5 s (R48 and R50 of 1 MOhm with C_C14 of 1 uF). ABSTOL does not control this stop, so ABSTOL = 1 pA gives the same residue. The residue depends on the ramp path: the vda term of the pixel stand-in is large while GATE ramps, and the heater ramp loads the rails. The path explanation is inferred, not verified.
- **Workaround:** none found. Tightening the pseudo-transient tolerances to `.OPTIONS PTRANVNTOL=1u PTRANABSTOL=1p` made the `.OP` of `afe_eval.cir` run for more than 20 min (run P23e_op_tight, `SimSrvr.exe` about 2700 s CPU) without a bias point. The main session stopped it, so this is not a usable workaround. For a settled DC value use a long `.TRAN` (not yet run, the simulator was needed for P-27) or the analytic value. The P-23 summary states the analytic value.
- **Source:** P23a_op, P23d_op_step, P23b_heat, P23c_op_abstol1n and P23c_op_abstol1p, 7 November 2026. The residues and the MID offsets are verified from the bias tables and the OPAx196.LIB values (I_B = 5.25 pA, I_OS = 2.75 pA, R_DIFF = 100 MOhm). The cause is not verified.

### Removing X_U2 leaves the RG resistor floating
- **Symptom:** P24b_ideal (the ideal-block copy of afe_eval.cir) stopped with status error after 18 s. The .out has `ERROR(ORPSIM-15141): Less than 2 connections at node RGP`, the same for RGN, and `ERROR(ORPSIM-15142): Node RGP is floating` (and RGN).
- **Cause:** R_R10 (RG = 5.62 kOhm) connects only RGP and RGN, which are pins of X_U2 only. Replacing X_U2 by an E source removes those pins, so the resistor is left alone on two nodes.
- **Workaround:** the line R_R10 is commented out in circuits/afe_eval_P24b.cir. The E_U2 source has the gain 1 + 50 kOhm / 5.62 kOhm written out, so the RG value stays in the file. The P24b entry in the index does not mention this step, so the owner should note it there.
- **Source:** P24b_ideal, 7 November 2026, verified (second run status done, 19 s, no ERROR line).

### Grid frequencies of .AC DEC 200 do not contain the nominal test frequencies
- **Symptom:** the P-24 entry quotes values at 518 Hz, 1036 Hz, 1554 Hz and so on, but a `.AC DEC 200 50 20k` run has 522 points with a 1.16 % step, so the nearest points are 517.571 Hz, 1032.69 Hz and 1545.15 Hz. At 518 Hz the phase slope is -0.44 deg per Hz, so an offset of 0.43 Hz changes the phase by 0.19 deg.
- **Cause:** the decade grid is logarithmic and does not include the design frequencies.
- **Workaround:** compare run and reference on the same grid point (the analysis script P-24_ac.py does this). For exact points, a `.AC LIN` run with the frequency set on the grid, or a separate run, is needed.
- **Source:** P24a_vendor and P24b_ideal, 7 November 2026, verified from the frequency column of the .csd.

### Grid finite-difference phase slope differs from the analytic slope by 0.07 %
- **Symptom:** the phase slope at 518 Hz from the grid, (phi(f2) - phi(f1)) / (f2 - f1), is -0.44273 deg/Hz for the ideal run, but the analytic derivative is -0.4424 deg/Hz.
- **Cause:** finite difference over two grid points of width 11.9 Hz. The phase curvature makes the secant differ from the tangent.
- **Workaround:** compare the run with the ideal curve on the same grid, which gives 0.00 %. Quote the analytic value only as a reference.
- **Source:** P24b_ideal, 7 November 2026, verified (P-24_ac.py).

### A background run stops without an .out and leaves a foreign lock
- **Symptom:** P26a_ac2 ended with no `.out` after its background shell exited with code 127. Its folder had only the `.cir`. A later P26a attempt waited on `sim-runs/.pspice.lock`, which then belonged to another agent's P23c run (PID 19144). The first attempt, P26a_ac, was also partial.
- **Cause:** not verified. The background shell was stopped before the run wrote its `.out`. The runner does not write a status when it is killed.
- **Workaround:** check the folder for a `.out` with `Total job time` before rerunning. Use a new run name for a partial folder (P26a_ac3 finished in 34 s). Do not stop the other agent's process. Run long jobs with `nohup` and an output file, not with the shell's background mode.
- **Source:** P26a_ac, P26a_ac2 and P26a_ac3, 7 November 2026, verified for the folder states and the lock holder.

### A 2 us maximum step resolves the staircase edges of P26b
- **Symptom:** the fit residual of V(EXC_DAC) is 1.45 mV rms against a 300 mV fundamental. Fitting only the first ten harmonics leaves 2.49 mV rms. The residual is the ZOH images at 129 f0, 255 f0 and above, which the fit basis did not include. The gate residual is 0.31 uV rms.
- **Cause:** not an edge problem. The solver puts time points on the 100 ns edges: the median solver step in the window is 128 ns, and every one of the first 4000 edges has a time point within 5 ns. An analytic 12-bit staircase with 100 ns edges gives the same fit (299.9213 mV, -1.4155 deg, -42.08 dBc).
- **Workaround:** none needed for the 2 us run. Include the ZOH images (k 128 +/- 1, times f0) in the fit basis. The edge density check is in `docs/sim-results/scripts/P-26_stair.py`.
- **Source:** P26b_stair (2 us, 424 s, status done), 7 November 2026, verified by the edge check and by the analytic staircase.

### Zero-crossing ringing period is biased by the decay
- **Symptom:** the median half period of the zero crossings of a step residual gives 2.66 kHz, against 3.61 kHz from a damped-sinusoid fit of the same data.
- **Cause:** the decaying offset and the early, non-sinusoidal part of the response move the crossings. The estimate is not a frequency of the mode.
- **Workaround:** fit an exponentially damped cosine with an offset (`scipy.optimize.curve_fit`) over the ringing window, as in `docs/sim-results/scripts/P-26_step.py`.
- **Source:** P26c_step (cgate 50 pF and 1 nF), 7 November 2026, verified against the fit.

### The simulated MFB image is 4 dB above the ideal closed form
- **Symptom:** the simulated attenuation of the MFB at 65.786 kHz is -40.910 dB (50 pF) and -40.808 dB (1 nF). The ideal closed form gives -44.945 dB. The simulated gain is 4.06 dB above the closed form at 66 kHz, and the excess grows to +7.4 dB at 100 kHz and about +34 dB at 1 MHz.
- **Cause:** not finite GBW alone. A single-pole op amp with GBW 1.1 MHz gives -45.02 dB, which is slightly lower than the ideal value. An output resistance Ro in series with the op-amp output raises the image attenuation: with GBW 1.1 MHz, Ro of 200, 300 and 500 Ohm give -43.31, -42.57 and -41.27 dB. No single Ro fits 100 kHz to 1 MHz. The most likely source is feedthrough from NC7 through R5. GBW and Ro are not verified against the OPAx196 model.
- **Workaround:** use the simulated attenuation for the image of the excitation. Quote the closed form only as an ideal value. The nodal model in `docs/sim-results/scripts/P-26_ac.py` tests the op-amp parameters.
- **Source:** P26a_ac3, 7 November 2026, verified against the grid values (66069 Hz: 7.47e-5 V/V simulated, 4.68e-5 V/V closed form) and by the nodal model.

### Break-before-make delay and slew at the sine peak give a demodulator error at p = 0 and p = 90
- **Symptom:** the offset-corrected Y_OUT at p = 0 is -0.0078, -0.0317, -0.2367, -0.5866, -1.0829, -1.7033 and -2.4630 mV at 0.1, 0.4, 1, 1.5, 2, 2.5 and 3 V (P28a). The offset-corrected X_OUT at p = 90 is -0.0318 mV at 0.4 V and -1.085 mV at 2 V (P28d). The D1 and X_DEM show spikes at the switch edges: the D1 overshoot peaks 45 ns to 58 ns after each REF_X edge, and the break excursion of D1 is about ±9 mV.
- **Cause:** the errors are a reference timing error with a slew limit, at the same size for X and Y. They enter where the reference edge falls on the sine peak. A three-term model fits 1 V to 3 V within 7.7 uV: MAG = 4 f0 delta A + 4 f0 A^2 / SR - c, with delta = 38.1 ns (the break-before-make lag, which fits 37.6 and 38.3 ns at 0.1 V and 0.4 V), SR = 8.00 V/us (the rising rate of the output, the only rate that enters, because both reference edges of each period step the output upwards), and c = 0.109 mV (a recovery term from the X_DEM overshoot of 0.17 V to 0.27 V, about 0.3 us to 0.8 us after each edge. It is not constant: it scales with the step below 1 V and saturates near 0.11 mV above, P-28 third grading). The three constants are correlated: a least-squares fit over 1 V to 3 V gives delta = 17.1 ns, SR = 7.69 V/us and c = 0.070 mV. At 0.1 V and 0.4 V the model overpredicts the error by 106 uV and 68 uV, so the recovery term is not amplitude-independent at low amplitude. The empirical slew-only fit over 1.5 V to 3 V (7.60 V/us) absorbs the delay and recovery terms. The sign follows from a lag: (2/pi) A cos(p + omega delta) gives negative errors at p = 0 (Y) and p = 90 (X). X_DEM moves less than 1 mV on average until D1 passes 50 % (at 40.2 ns after the edge), then it slews at 8.2 V/us at 2 V (secant, 8.14 V/us to 8.24 V/us). Ruled out by argument, not simulated: the QINJ charge (the +Q and -Q edges of each period cancel to about 0.1 uV on the mean) and RON with CS and CD (a 2 ns linear filter, no effect on the mean). The break excursion of about ±9 mV on D1 matches the injected switch charge on the floating node (0.4 pC x 0.3 / 12 pF = 10 mV). The post-closure overshoot of D1 is a separate excursion (its cause is not checked here). The datasheet values of SBOS869 are 7.5 V/us rising and 5.5 V/us falling at +/-18 V (page 8), and 6.5 V/us rising and 5.5 V/us falling at +/-2.25 V (page 10). The model value at the +/-5 V supply is not read here.
- **Workaround:** use the offset-corrected values of P-28 for the error budget. Do not use the peaks of D1 or X_DEM as the amplitude. To separate the terms, run the same sweep with the reference edges moved off the peak (for example p = 45 deg) and with the break-before-make delay removed from the switch model.
- **Source:** P28a_lin, P28d_quad and P28c_zero, 7 November 2026, verified against `docs/sim-results/scripts/P-28_linearity.py` (three-term edge model, edge statistics and sample offsets). The datasheet values were read from the local copy of SBOS869 (pages 7, 8, 10 and 24, path in `docs/sim-results/P-28.md`), not verified against the model file. The QINJ and RON arguments are not simulated.

### Settling check against the window before the reference is not a settling test
- **Symptom:** the entry's settling check (mean over 20 periods from 60 ms against the 20 periods before) gives +363 uV at ain = 1 V and +1.09 mV at 3 V in P28a, which is not a settled-window difference.
- **Cause:** the reference window starts at 21.39 ms, 7.1 time constants (tau = 3 ms) after the start, and still holds the start-up transient of the post-filter. The analytic mean deficit of that window is 5.68e-4 of the final value, which gives 361.6 uV at 1 V (measured 363 uV, 0.5 % apart) and 1.085 mV at 3 V (measured 1.090 mV). The window at 60 ms is settled to below 0.03 uV at 1 V (residual (1 + t/tau) exp(-t/tau) with t/tau = 20).
- **Workaround:** keep the 60 ms window and check it with the analytic residual, or compare with a window that starts after 60 ms. Do not use the 20-period reference window as a settling tolerance for a 3 ms pole.
- **Source:** P28a_lin and P28b_lin5v, 7 November 2026, verified against the analytic formula in `docs/sim-results/scripts/P-28_linearity.py`.

### A background chain started with nohup returns at once
- **Symptom:** a shell script that ran four simulations in sequence was started with `nohup ... &` inside the Bash tool, with its output to a log file. The tool reported the background command as completed with exit code 0 within a few seconds, while the first PSpice run was still running. The notification did not report the end of the chain.
- **Cause:** the `&` detaches the script from the tool's tracked process, so the tool sees the launcher exit at once.
- **Workaround:** start the chain with the tool's own `run_in_background`, or wait for a sentinel line in the log (for example `CHAIN_DONE`) with a sleep loop that runs in the background. Do not rely on the first completion notification.
- **Source:** P28 chain (P28a_lin to P28d_quad), 7 November 2026, verified from the log file and the process list.

### Two diode models give ORPSIM-16583 (trace limit of 4)
- **Symptom:** `ERROR(ORPSIM-16583): More than one imported model containing transistors or diodes is detected. To simulate this circuit, a minimum of 1 and a maximum of 4 traces are required.` The run ends with status `done` after 13 s, the `.out` is written and the runner exits with code 1. It appeared for `circuits/afe_eval_P31.cir` with two diode models (DSCHOTTKY for the rail diodes and DESD for the ESD stand-ins), with 4 probes or 8 probes or 28 probes.
- **Cause:** the circuit had two diode models. The same circuit with only DSCHOTTKY (the ESD stand-ins changed to DSCHOTTKY) runs with 23 probes. P-27 (`circuits/afe_eval_fast.cir`, one diode model) ran with 8 probes. The trace limit appears to count the probes when more than one diode model is present. This is inferred from the runs, not verified against the PSpice documentation.
- **Workaround:** keep one diode model in the circuit. P-31 uses DSCHOTTKY for the stand-ins, as the entry states. Diode currents can be probed with `I(D_xxx)` in this setup, but in the failing runs it was not separated from the model-count problem, so the stand-in current is read as the voltage across a 1 Ohm series resistor instead.
- **Source:** P31_powerup (failed, two diode models), P31_test_v (done, 4 probes, DESD), P31_bisect12, P31_bisect8, P31_bisect_nostep, P31_bisect_norail, P31_bisect4 and P31_bisect6 (failed or done as stated), P31_bisect_p27circ (done, one diode model, 8 probes), P31_bisect_one (done, DSCHOTTKY only, 23 probes), 8 November 2026. The cause is inferred, not verified.

### A probe line longer than 245 characters is rejected
- **Symptom:** `ERROR(ORPSIM-16366): Line too long. Limit is 245 characters.` after 19 s, with no data. The `.PROBE/CSDF` line that `tools/run_sim.py` writes was 254 characters for 22 probes with the names `V([K_EBP])` and so on.
- **Cause:** PSpice limits a netlist line to 245 characters. The runner writes all probes on one `.PROBE/CSDF` line.
- **Workaround:** shorten the node names (for example `KEBP` instead of `K_EBP`), or probe fewer nodes. The P-31 run uses the shortened names.
- **Source:** P31_powerup (failed), 8 November 2026, verified from the netlist line length.

### A diode model with IS = 5 uA leaks 5 uA in reverse
- **Symptom:** the DSCHOTTKY model (IS = 5 uA) placed reverse biased between a rail and a signal gives a current of about -5 uA, not a leakage near zero. An ESD stand-in test with a 1 nA limit fails by construction.
- **Cause:** the reverse saturation current of the diode is IS. The DSCHOTTKY model is the rail-diode stand-in of afe_eval.cir (B5819W), not a leakage model. A separate model with IS = 1 fA was tried in P31_test_v, but it gave the two-model error above.
- **Workaround:** none in the circuit with one diode model. The stand-in current in P-31 includes the reverse saturation current, which the summary states. The ESD leakage of a real TMUX6136 is not modelled.
- **Source:** P31 design, 8 November 2026, from the model parameters. Verified in P31_powerup: the mean over the last 20 periods is -5.00 uA in every stand-in.

### The INA828 model adds 10 pF to each input node
- **Symptom:** the drain of the vendor-model chain lags 0.68 deg more than R_D with the 60 pF of the node (phase of the chain at 518 Hz 167.11 deg, against 167.87 deg expected), and its amplitude is 0.08 % lower. The blind drain DRN_B shows 0.107 % of DRN_A at +85.6 deg, although its pixel is off.
- **Cause:** `INA828.LIB` (in the PSpice TI library folder, loaded by `nom_pspti.lib`) connects 10 pF from each input pin to MID (C_CMN, C_CMP) and 1 pF between the input pins (C_DIFF). The node therefore has 60 + 10 + 1 = 71 pF to ground. The 1 pF couples DRN_A into DRN_B, which has only this feedthrough.
- **Workaround:** use the 71 pF node in the expected values of drain-stage entries that use the vendor INA828, or remove the INA828 capacitances in a copy for the ideal case. Expected values written from the schematic values alone miss this.
- **Source:** P-27 (P27_phase, 7 November 2026). The stage phases and amplitudes match the 71 pF prediction within 0.006 deg and 0.01 %. Verified from the model netlist and the run data. A run with the capacitances removed was not made (not verified by a separate run).

### A noise-equivalent resistor of 2kT/(qI) is 6.894 kOhm and loads the node
- **Symptom:** the entry for P-30 gave a value of 6.894 MOhm for the pixel shot-noise resistor. At that value the drain DC would be 0.157 V / 6.9 MOhm = 23 nA, which is 1000 times too small, and the arithmetic of the netlist expression `2*0.025852/7.5u` gives 6894 Ohm. At 6894 Ohm the resistor draws 23 uA from each drain, three times the 7.5 uA pixel current, and reduces the drain AC impedance by about 98 %.
- **Cause:** 2kT/(qI) with kT/q = 0.025852 V and I = 7.5 uA is 6.894 kOhm. The resistor has the right noise current (4kT/R = 2qI), but the same conductance loads the node DC and AC.
- **Workaround:** keep the resistor for its noise and cancel its conductance with a noiseless behavioural source, `G_CSA PIX_D1 0 VALUE {-V(PIX_D1)/(2*0.025852/7.5u)}` (and the same for PIX_D4). The bias table of the run must still show DRN_A and DRN_B near 0.1575 V. Verified in P30a2: DRN_A 0.15745 V, DRN_B 0.15747 V, and the shot noise per side at the drain is 510.18 nV/sqrt(Hz) against 510.2 nV/sqrt(Hz) expected.
- **Source:** P30a2_noise518 and P30b2_noise_dec (`circuits/afe_eval_P30.cir`), 7 November 2026, verified by the bias table and the top-contributor table. The uncompensated run P30a_noise518 is superseded and its results are not used.

### The .NOISE "Top Contributors" block lists only five devices
- **Symptom:** the "Top Contributors To Output Noise" block at the end of a .NOISE table lists five devices. Reading only that block gives 98 % of the output power, and the rest looks unexplained.
- **Cause:** the block shows the five largest items. The full DIODE, RESISTOR and VOLTAGE CONTROLLED SWITCH tables come earlier in the same frequency block.
- **Workaround:** parse the full tables between the line "NOISE ANALYSIS" and "Top Contributors". `docs/sim-results/scripts/P-30_noise.py` does this (1641 items for the P-30 circuit). The sum of the items matches the TOTAL OUTPUT NOISE VOLTAGE within 0.004 %.
- **Source:** P30a2_noise518, 7 November 2026, verified by the item sum.

### Frequency grid of the CSDF and the .NOISE table differ in the last digit
- **Symptom:** the frequencies of the .csd (for example 10.47128548 Hz) and of the .out (10.47 Hz) differ in the fourth significant digit, so a check with the default numpy tolerance fails.
- **Cause:** the .out prints frequencies with four significant digits.
- **Workaround:** compare the grids with rtol = 1e-3 and use the .csd values for interpolation. The P-30 script does this.
- **Source:** P30b2_noise_dec, 7 November 2026, verified.

### A .MC run counts the nominal as run 1
- **Symptom:** `.MC 200 AC ...` (P29_mc) gives 200 CSDF sections. The `.out` labels section 1 as MONTE CARLO NOMINAL and the other sections as MONTE CARLO PASS 2 to PASS 200. So 199 random samples follow the nominal. The same count is in P-14 (`.MC 500` gave 499 samples).
- **Cause:** normal PSpice counting. The `.MC` count includes the nominal run, so `.MC N` gives N runs in total and N - 1 random samples. This is not a fault of the run.
- **Workaround:** take section 0 as the nominal and sections 1 to N - 1 as the samples. Report the sample count as N - 1, and state the number of runs as N.
- **Source:** P29_mc, 7 November 2026, verified from the `.out` labels (the NOMINAL label and the PASS 2 to PASS 200 labels).

### Nominal AC run of a symmetric drain stage still shows the INA828 common-mode leakage
- **Symptom:** with both drains equal (V_B - V_A = 0 exactly, P29_nom), BPF_OUT is 45.56 uV at -155.53 deg for a 0.997 V common-mode drive. The nominal output is not zero.
- **Cause:** the vendor INA828 model has a finite common-mode rejection. Referred to the differential (divided by 39.578 V/V) the leakage is about 1.15 uV, which is a CMRR of 118.75 dB.
- **Workaround:** subtract the nominal BPF_OUT in every pass before any conversion of BPF_OUT to the differential drain signal. The nominal run cannot be used as a differential reference. P-29_mc.py does this.
- **Source:** P29_nom and P29_mc, 7 November 2026, verified from the nominal CSDF and the BPF cross-check per pass.

### SKIPBP with .IC starts the state nodes at the settled values, but the output starts at zero
- **Symptom:** a `.TRAN 0 1 0 5u SKIPBP` run of `afe_demod.cir` with `.IC V(X_OUT)=0.25465 V(NC13)=0.25465 V(U26BP)=0.25465 V(Y_OUT)=0 V(NC14)=0 V(U27BP)=0` gives X_OUT = 1.64 mV at t = 0 (not 0.2547 V). It reaches 0.25466 V within 1 ms. From 1 ms to 1 s the spread of X_OUT is 32 uV, and the mean over the last 0.5 s is 0.2546849 V (+38 uV against (2/pi) x 0.4 V).
- **Cause:** the .IC values are applied to the capacitor nodes (NC13, U26BP, NC14, U27BP) and the output of the follower follows its input within the first millisecond. X_OUT itself is not an initial state, so the first samples are not the settled value. The 0.25466 V level is the state the post-filter pair starts from, so the 1 s run needs no settling of the 0.3 s pole to reach the settled level.
- **Workaround:** use the window from 0.5 s (or from 1 ms) for the analysis, and fit a transient term (A + B t) exp(-t/RC) with RC = 0.3 s over the window. Do not use the first samples of X_OUT.
- **Source:** P34_ref, 8 November 2026, verified from the CSDF (293225 points, status done after 266 s runner wall time, 258.8 s total job time in the `.out`, no ERROR line).

### Sallen-Key feedthrough puts 2f0 sidebands of about 0.4 uV into X_OUT at 500 Hz and 550 Hz
- **Symptom:** after subtracting the reference, the residual of the fit is 10.4 uV rms for fi = 500 Hz and for fi = 550 Hz, against 99 nV for 50 Hz and 88 nV for 1036 Hz. The largest lines are at 1018 Hz, 2054 Hz and 3090 Hz (0.67 uV, 0.45 uV, 0.40 uV), which are 18 Hz below 2 f0, 4 f0 and 6 f0. The reference 2f0 ripple at X_OUT is 452.9 nV, against 44.5 nV from the ideal post-filter.
- **Cause:** the closed-loop output impedance of the OPA2196 stage in U26B is inductive, L = 81.6 uH (0.531 Ohm at 1036 Hz). Above the corner, C13 passes the current V(X_DEM) / R14 into this output, so X_OUT = X_DEM(f) (H_post(f) + j w L / R14). The feedthrough gain is 2.56e-9 f, -111 dB at 1 kHz, rising 20 dB/decade. With this model the 2f0 ripple, the 4f0 ripple and the sidebands agree with the simulation within 0.05 dB. The lines are physical, not numerical.
- **Workaround:** none needed for the sidebands. Use the feedthrough model of `docs/sim-results/scripts/P-34_interference.py` for any product of this entry, and do not compare such products with the ideal post-filter prediction.
- **Source:** P34_ref, P34_f500, P34_f550 and P34_f1036, 8 November 2026, verified from the CSDF and the feedthrough model of the judge notes (the reference 2f0 ripple gives L, the other lines agree within 0.05 dB). The OPA2196 output impedance has not been checked against the datasheet.
