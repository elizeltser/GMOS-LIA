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
- **Source:** P05_step2u, 27 October 2026, verified.

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
