# Design issues

> **Paths.** Paths that start with `simulations/` are relative to the repository root. All other backticked paths (`circuits/`, `tools/`, `ti-pspice-PSpiceFiles/`, `vendor/`, `archive/`, `docs/`) are relative to the PSpice for TI project, [`ti-pspice/`](ti-pspice/CLAUDE.md).

This register lists the design issues found by the design reviewer and by the judge. Each issue has a severity, its evidence, the recommended change and a status. The design reviewer updates it after every batch (see the repository root `.claude/agents/design-reviewer.md`). Closed issues stay in the register with the reason for closing.

Issues are numbered `DI-xx`. Board decisions (`D-n`, e.g. D-18) are a separate register in `schematics/LIA-Readout/docs/README.md` §9.

Severity levels (Critical, Major, Minor, Note) are defined in `simulations/design-context.md`, section 7. The numbers quoted below are evidence from the time each issue was written. The current design values are in `simulations/design-context.md`.

DI-01 to DI-09 come from an external review of P-01 to P-07 on 27 October 2026. The design reviewer checked their datasheet values against the full datasheets on 27 October 2026 (batch 2 review, `simulations/design-review/2026-10-27_batch2.md`) and added evidence. DI-10 to DI-16 are new from that review. Findings that rest on Draft or TBD values of `simulations/design-context.md` say so. DI-17 to DI-26 are new from the batch 4 review (`simulations/design-review/2026-11-08_batch4.md`). On 2026-11-08 DI-01 to DI-04, DI-09, DI-10, DI-12, DI-14 and DI-16 were closed because the board moved to LIA-AFE-Eval.

## Open issues

### DI-05 Resistor mismatch converts input offset into DC error and scale error

- **Severity:** Minor with 0.1 % resistors. Major with 1 % resistors. The tolerance is TBD (`simulations/design-context.md` section 6).
- **Evidence:** with R1/R2 = 1 + delta the output gets a DC error of (delta/2) times the input offset and a scale error of delta/2. P-11 confirmed this within 0.0005 mV for delta = +/-0.1 % and +/-1 %, with VY unchanged. The offset at the demodulator input is below 0.25 mV after the high-pass filter (P-09), so the offset term is 0.125 uV at delta = 0.1 %. The scale term dominates: 0.1 % for 0.1 % resistors (R1 against R2 worst case 0.2 %), 1 % for 1 % resistors. X and Y have separate pairs, so their ratio errs by up to 2 x delta/2, which tilts the phase by up to 0.11 deg (0.1 %) or 1.1 deg (1 %). The -0.103 mV/V term of P-11 is a PSpice PULSE-width artefact (quirk) and does not exist with a timer reference.
- **Recommendation:** thin-film 0.1 % resistors, 25 ppm/K, matched pairs (candidates in the review). A per-board gain calibration removes the term.
- **Status:** open.
- **Update:** Update 2026-11-08 (batch 4): applies to R78/R79 and R83/R84 (0.1 %, 10 ppm/K). Scale error up to 0.1 % per channel, 0.057 deg at most as X/Y mismatch (calc3 of the batch 4 review). Removed by the phase-sweep calibration, 12 ppm to 16 ppm residual (review section 5).

### DI-06 Demodulator input impedance switches at the reference rate

- **Severity:** Minor (Major if driven by a passive network).
- **Evidence:** in the +1 state no current flows in R2, so the input is high impedance. In the -1 state it sees 10 kOhm to the reference. P-12: 10 Ohm in series gives -0.0998 % of X, 100 Ohm -0.985 %, 1 kOhm -8.71 %. 10 Ohm is at the Draft major threshold. In the chain the node is driven by the OPA192 follower U3, whose closed-loop output resistance at 517 Hz is far below 1 Ohm (open-loop value not read, not verified).
- **Recommendation:** drive the node directly from an op amp output, DC-coupled. No series capacitor, protection resistor or RC at this node.
- **Status:** open.
- **Update:** Update 2026-11-08: P-28 and P-32 confirm the effect at the Y edges. The datasheet ZO of the OPA2196 is 700 Ohm at 1 MHz (SBOS869), half of the model value 1.47 kOhm. The 1 kOhm at S1A and S2A (DI-18) is in front of a high-impedance input and does not load the node.

### DI-07 No capacitor across the feedback resistor R1

- **Severity:** Note.
- **Evidence:** in the +1 state the gain is 1 for any feedback impedance. In the -1 state it is -Z1/R2. A capacitor across R1 adds a pole to one state only, which gives a gain mismatch and a phase error of about f_osc/f_pole rad. Not exercised in batch 2, no new evidence.
- **Recommendation:** keep R1 without a parallel capacitor, or put its pole above 100 times f_osc and verify the effect.
- **Status:** open.
- **Update:** Update 2026-11-08: no new evidence. The heater loop compensation of DI-22 is a different node.

### DI-08 Filter phase tolerance at f_osc

- **Severity:** Major if the board is not calibrated. Minor with a per-board phase and gain calibration. The tolerances and the phase target are TBD, the 1 deg limit is Draft.
- **Evidence:** P-14 (499 samples): phase std 3.44 deg, gain std 3.62 %, 76 % of samples beyond 1 deg. The numpy run (200 000 samples) gives 3.36 deg and 77.3 %. Phase std against tolerance: 0.1 % R with 2 % C 1.32 deg, with 1 % C 0.66 deg, with 0.5 % C 0.34 deg. The capacitors set the spread. Drift: all R and C +0.1 % moves the phase by -0.457 deg and the gain by +0.010 %. Worst-case C0G (30 ppm/K) with thin film (25 ppm/K) over 50 K is 0.275 %, so -1.26 deg and 0.012 % of gain. X7R (-15 %) would give +36 deg and -10 %. The R = sqrt(X^2 + Y^2) reading is insensitive to drift because 517 Hz is near the gain peak. The -0.055 % and -0.13 deg deficit of P-09 and P-14 is not a tolerance issue. Adding 6.4 pF (OPA192 common-mode capacitance, SBOS620E) at the two follower inputs gives -0.058 % and -0.034 deg (calc4), plus the INA828 lag of -0.05 deg. The model connects its capacitors to an internal node, so this is a plausible cause, not a proven one (test R-03). A stray capacitance of a few pF on a board gives the same size.
- **Recommendation:** C0G capacitors, 0.1 % thin-film resistors, one-point gain and phase calibration per board with a tone of the signal waveform (DI-12). Compute R for monitoring. Do not use X7R or Y5V.
- **Status:** open.
- **Update:** Update 2026-11-08: P-25 gives phase std 3.36 deg (C 5 %) and 0.68 deg (C 1 %), gain std 7.0 % and 1.41 %. 52 % of the 1 % boards are outside ±1 % (48.1 % inside, P-25 Table 3). Handled by the calibration of DI-19 (common gain and phase).

### DI-11 Sensor source impedance, bias resistors and noise were not simulated

- **Severity:** Major. Rests on the sensor impedance, which is TBD.
- **Evidence:** all chain tests used 1 mOhm per leg (`rsens` in `chain_ss.cir`). With Rs per leg and 100 kOhm to the reference on each input, the gain is multiplied by 200 kOhm / (200 kOhm + 2 Rs): 0.990 at 1 kOhm, 0.909 at 10 kOhm. Gain loading exceeds the Draft 0.1 % threshold from 100 Ohm. Input-referred noise rises from 12.68 nV/sqrt(Hz) to 14.06 (1 kOhm), 23.77 (10 kOhm) and 88.6 (100 kOhm) nV/sqrt(Hz) referred to the sensor EMF, and A_min from 28.4 nV to 31.5, 53.2 and 198 nV (calc2). A sensor whose impedance carries the measurement makes the loading a signal-dependent gain error.
- **Recommendation:** define the sensor impedance range. Choose the bias resistors from it (larger values cost only offset, which the high-pass filter blocks). Test R-01.
- **Status:** open.
- **Update:** Update 2026-11-08: P-29 and P-30 model R_D = 330 kOhm and 71 pF per drain node. Sensor impedance is still TBD. The CMRR median is 49.3 dB, with 97 % of the leakage in Y.

### DI-13 ADC resolution and interface

- **Severity:** Minor. Rests on the ADC and the resolution target, both TBD.
- **Evidence:** DC-band noise at VX is 0.2001 uV rms (126.56 nV/sqrt(Hz) x sqrt(2.5 Hz), P-15). A 16-bit, 5 V ADC adds 22.0 uV rms of quantisation noise (110 times), 18 bit 5.5 uV (27.5 times), 20 bit 1.38 uV (6.9 times), 24 bit 0.086 uV (0.43 times, ideal). Resolving 0.2 uV in 5 V needs 24.6 bits. The 10 kOhm output resistor with 1 uA of ADC input current drops 10 mV (9.5 % of 105.8 mV). The 2f ripple at VX is about 0.108 mV peak at tau = 0.1 s and 166 mV, attenuated only to 1.5e-3 at 1034 Hz by a first-order filter, which an ADC sampling can alias.
- **Recommendation:** pick the ADC from the resolution target. Add a buffer after R3 or use a high-impedance delta-sigma input, and set the sampling rate and filter so that the 2f ripple does not alias.
- **Status:** open.
- **Update:** Update 2026-11-08: LIA-AFE-Eval has no ADC. The issue stays for LIA-Readout. The 2f0 ripple at X_OUT is 453 nV in the model and 0.22 uV to 0.28 uV with the datasheet ZO (DI-24).

### DI-15 OPA192 at mid-supply on a 5 V rail

- **Severity:** Minor.
- **Evidence:** OPA192 SBOS620E: the input stage has a transition region for (V+) - 3 V < VCM < (V+) - 1.5 V, which is 2.0 V to 3.5 V on 5 V. All OPA192 stages work at 2.5 V, inside it. Offset at VCM = (V+) - 1.5 V is +/-25 uV typical and +/-150 uV maximum (0 C to 85 C), table 6.7 of the 8 V to 36 V case. Two times the offset is a static baseline at VX of 10 uV to 300 uV, which is 50 to 1500 times A_min after division by 7.05 V/V. P-13 shows a model offset below 2 uV, so the model probably does not represent the region (not verified).
- **Recommendation:** keep the OPA192 for the filters. For the demodulator op amps consider the zero-crossover OPA388 (candidates in the review). The measurement can use the active/blind difference to remove the baseline.
- **Status:** open.
- **Update:** Update 2026-11-08: the board uses OPA2196 on ±5.1 V, transition region 2.12 V to 3.62 V (SBOS869: Vos ±25 uV typical, ±100 uV maximum, noise 1.4 uVpp below and 7 uVpp above). U10A and U10B inputs at 2.4 V and U26A, U27A inputs above 53 mV drain are inside. The models show no step (P-28, P-33c). The effect is at most 0.2 mV at X_OUT, 0.016 % at 50 mV. It needs the bench check R-11 step 5.

### DI-17 TMUX6136 SEL pins are driven above VDD + 0.3 V when the NUCLEO runs before J4

- **Severity:** Critical (part outside its absolute rating, in an order that the owner's power rule does not cover).
- **Evidence:** SCDS397B section 5.1: digital pins GND - 0.3 V to VDD + 0.3 V, ±30 mA. REF_X and REF_Y connect J7, TP8 or TP9 and U24 pins 1 and 9 with no resistor (P-31, KiCad netlist of commit 16ad253). P-31: SEL1 forward biases, the +15 V rail floats to 3.24 V, 32 uC flow (the 2.45 A peak is the 1 Ohm placeholder). Estimate with a 25 Ohm MCU output resistance (assumed): 108 mA, 3.6 times the rating (batch 4 review F-01, calc1).
- **Recommendation:** 1 kOhm in series at U24 pins 1 and 9 (peak 2.6 mA, edge delay 9.5 ns, 0.0018 deg, equal in X and Y). Firmware and procedure rule: references off until J4 is on and stopped before J4 is switched off. Test R-06.
- **Status:** open.

### DI-18 BPF_OUT drives the TMUX6136 signal pins when the switch is unpowered

- **Severity:** Major (outside the rating only in a fault or a wrong order).
- **Evidence:** analog pins VSS - 0.3 V to VDD + 0.3 V, ±30 mA (SCDS397B section 5.1). BPF_OUT of 2 V to 4 V pk into VDD = VSS = 0 V is limited only by the OPA2196 short-circuit current of ±30 mA to ±65 mA (SBOS869). No resistor at S1A and S2A.
- **Recommendation:** 1 kOhm in series at U24 pins 2 and 10 (peak 1.4 mA at 2 V, 3.4 mA at 4 V). It adds 14 ns to the +1 state, equal in X and Y. Test R-06.
- **Status:** open.

### DI-19 Offsets, common gain and common phase are not calibrated (A-06 to A-08)

- **Severity:** Major at 1 mV to 10 mV drain signal, Minor at 50 mV (Draft threshold 0.1 % or 1 deg). Targets for accuracy and resolution are TBD.
- **Evidence:** offset at X_OUT 125 uV RSS typical, 0.5 mV RSS and 0.91 mV worst case at the maximum Vos (36 uV at the drain, 54 times the drain noise). It is 0.36 % of the output at 10 mV drain and gives 0.21 deg, at 1 mV drain 3.6 % and 2.1 deg. Common gain std 7.0 % (C 5 %) and 1.41 % (C 1 %), common phase std 3.36 deg and 0.68 deg (P-25). Drift 2.5 uV/K RSS to 4.5 uV/K worst case against 17 uV noise.
- **Recommendation:** the procedure of review section 5: a zero reading with the references and excitation running, an 8-point excitation phase sweep with an ellipse fit (offset 2 uV, gain ratio 16 ppm, orthogonality 0.001 deg), and a gain reading with a known tone at TP15. Tests R-10 (simulation) and R-11 (bench).
- **Status:** open.

### DI-20 Drain supply window against 7.5 uA through 330 kOhm and the TMUX1109 range

- **Severity:** Major, conditional on the sensor current and compliance (sensor model TBD).
- **Evidence:** drain = VSUP_A - 2.475 V. For the window 0.5 V to 3.5 V the drain is -1.98 V to +1.03 V. TMUX1109 Sx and Dx: -0.5 V to VDD + 0.5 V absolute, 0 V to VDD recommended (SCDS406A sections 5.1 and 5.3). The drain is below the recommended 0 V for VSUP_A below 2.475 V and reaches -0.5 V at VSUP_A = 1.975 V (DAC2 = 1.80 V) without a clamp. With the ESD clamp the drain stays at about -0.40 V (estimate), inside the absolute rating, so the risk is to the pixel and to the linearity, not to the TMUX1109. DAC80508Z powers up at code 0, so a MUX_EN before the DAC write gives -2.475 V at the pixel.
- **Recommendation:** firmware limit DAC2 and DAC3 to at least 2.30 V (drain at least +50 mV) and never below 1.80 V. The owner decides the pixel current and the window for AN-4 and AN-9. Test R-09.
- **Status:** open.

### DI-21 Heater driver headroom with the datasheet swing

- **Severity:** Minor (a margin below the Draft 0.2 V is Minor by the levels of `simulations/design-context.md`). Becomes Major if R-08 finds a ceiling below 4.0 V on the heater used, because the swing is not guaranteed at 6 mA to 14 mA. Conditional on the heater resistance (TBD).
- **Evidence:** the model needs 10.9 mV + 40.8 mV/mA below +5VP. The OPA2196 datasheet gives 60 mV typical (VS = 4.5 V to 8 V) and 500 mV maximum at 2 kOhm (SBOS869 section 6.8), a typical slope of 54.8 mV/mA to 30.5 mV/mA. The maximum is specified only at about 1 mA to 2 mA. Ceiling of HFB_A on the typical part at +5VP = 4.97 V to 5.09 V: 4.04 V to 4.43 V (300 Ohm), 4.45 V to 4.73 V (600 Ohm), 4.69 V to 4.90 V (1200 Ohm). The margin at 4.0 V on 300 Ohm is 0.04 V to 0.43 V against the Draft 0.2 V. 300 Ohm also clips HSENSE_B above 8.8 mA (F-09 of 2026-10-29, confirmed by P-33a). The B5819W stand-in matters little because J5 is set at TP3.
- **Recommendation:** state the heater resistance and voltage. For 300 Ohm limit the command to 3.8 V or change the shunt (F-09). Test R-08.
- **Status:** open.

### DI-22 Heater loop is poorly damped with cable capacitance

- **Severity:** Minor.
- **Evidence:** P-33b overshoot 1.8 % at 100 pF, 22.5 % at 1 nF, 58.4 % at 10 nF (phase margin about 19 deg). Model output impedance 1.47 kOhm, datasheet ZO 700 Ohm at 1 MHz (SBOS869).
- **Recommendation:** DNP C0G pads in parallel with R20 and R26, populate 22 pF if the leads are long. Test R-07.
- **Status:** open.

### DI-23 Reference edges can couple into the drain nodes

- **Severity:** Minor, Major if the layout puts the reference traces next to the drains without a guard.
- **Evidence:** not simulated. A stray 0.01 pF gives 22 uV pk at the drain and up to 0.56 mV (0.22 %) at X_OUT, 0.1 pF ten times more (review F-07, upper bound, assumed Cs).
- **Recommendation:** layout rule (5 mm and a ground guard from REF_X, REF_Y, SPI and EXC_DAC to DRN_A, DRN_B and the TMUX1109 pins). The zero with references running removes the constant part. Bench test R-11.
- **Status:** open.

### DI-24 Sallen-Key post-filter stopband is set by the op-amp output impedance

- **Severity:** Minor.
- **Evidence:** P-34 model: 2f0 ripple 453 nV, floor 2.56e-9 f, comb 10.4 uV rms. Datasheet ZO scaling: 216 nV to 281 nV, floor 1.4e-9 f to 1.6e-9 f. Both are above the 0.1 uV check of the index (no source in `simulations/design-context.md`, performance targets TBD). No effect on a DMM or scope reading.
- **Recommendation:** none for this board. For a board with an ADC use 1 MOhm and 300 nF. Test R-13.
- **Status:** open.

### DI-25 Post-filter capacitors 1.5 uF acrylic film, ±20 %, with no insulation resistance figure

- **Severity:** Minor.
- **Evidence:** Rubycon 16MU155MA23216 (component_selection C.8). DC gain error -(R14 + R15) / R_IR: 0.4 % at 100 Mohm, 0.1 % at 400 Mohm. X and Y have separate capacitors. Datasheet not read.
- **Recommendation:** read the datasheet. Measure with R-12. Replace with a film or C0G part if R_IR is below 400 Mohm.
- **Status:** open.

### DI-26 Simulation models differ from the parts in ways that change verdicts

- **Severity:** Note.
- **Evidence:** OPAx196 ZO and swing, DSCHOTTKY for B5819W, ideal DAC and pixel sources, `.OP` bias point not settled for the post-filter, TMUX6136 model without supply and ESD. Details in review section 3 (F-11).
- **Recommendation:** use the datasheet values in the findings, the bench tests R-08, R-11 and R-12, and the cheaper methods of review section 8.
- **Status:** open.

## Closed issues

### DI-01 TMUX6136 is not rated for a single 5 V supply

- **Severity:** Critical (confirmed 27 October 2026).
- **Evidence:** TMUX6136 datasheet SCDS397B (August 2025), section 1 and section 5.4: supply +/-5 V to +/-16.5 V (dual) or 10 V to 16.5 V (single), and a VDD to VSS differential of at least 10 V. The LIA runs it from 0 V to 5 V, which is 5 V. The behavioural model `vendor/tmux6136/TMUX6136_BEH.LIB` does not enforce any supply range, so P-01 to P-17 pass. The datasheet gives RON = 235 Ohm typical at 12 V single supply and no value at 5 V. A dual +/-5 V supply meets only the lower limit with no margin (5 % tolerance gives 9.5 V).
- **Recommendation:** use a 5 V switch. First choice TMUX1136DGSR (1.08 V to 5.5 V, RON 2 Ohm, QC -6 pC, tTRAN 12 ns typical, VIH 1.49 V minimum, two SPDT in one VSSOP-10). Backup two TMUX1119DCKR. Charge injection is 15 times the model value, so rerun the demodulator with the new parameters (test R-04). Part data and stock (27 October 2026) are in the review.
- **Status:** Closed 2026-11-08. The board supplies the TMUX6136 from its own ±15 V input (E-12, `simulations/design-context.md` section 6). VDD - VSS = 29.2 V is inside 10 V to 33 V. The remaining TMUX6136 rating problems are the SEL and S pins (DI-17, DI-18).

### DI-02 INA828 input common-mode range on a 5 V supply

- **Severity:** Major (was Critical until checked). Conditional on the sensor common-mode voltage, which is TBD in `simulations/design-context.md` section 4.
- **Evidence:** INA828 SBOS792A table 6.5: operating input range (V-) + 2 V to (V+) - 2 V, so 2.0 V to 3.0 V on 0 V to 5 V. Section 7.3.3 gives the dependence on the output voltage in figures 48 to 51 and 55 to 58, which could not be read (not verified). The model clamps at the same limits (P-09, P09b: within 1 mV from 2.02 V to 2.98 V, edges at 2.00 V and 3.00 V). The 2.5 V bias has 0.5 V of margin to each edge (Draft margin 0.2 V). Outside the range the output falls to the reference and does not clip, so the signal disappears without warning. Output swing is (V-) + 0.15 V to (V+) - 0.15 V at +/-15 V (5 V value not verified). With the 0.2 V Draft margin and 0.166 V amplitude the DC differential input budget is (2.5 - 0.15 - 0.2 - 0.166) V / 11 = 0.18 V. Ib and Ios are 0.15 nA typical and 0.6 nA maximum.
- **Recommendation:** keep the INA828 if the sensor common mode stays inside 2.1 V to 2.9 V over temperature. Otherwise use an in-amp with a wider range or level shift the sensor. Confirm with TI's common-mode calculator. The 100 kOhm bias to 2.5 V is correct for the single supply.
- **Status:** Closed 2026-11-08 for LIA-AFE-Eval. The in-amp runs on ±5 V (input range -3 V to +3 V, number quoted from this register) and the drains are -1.98 V to +1.03 V. The limit that applies on the board is the TMUX1109 (DI-20).

### DI-03 INA828 REF pin needs a low-impedance source

- **Severity:** Major.
- **Evidence:** INA828 SBOS792A section 8.1 and figure 61: any resistance at REF is in series with one of four internal 40 kOhm resistors. Keep it below 5 Ohm. In `chain_ss.cir` the filter returns (R18 and C3) add 8.8 uA and 17.8 uA at 15 mV input (26.7 uA total, calc1). A reference node with 1 Ohm carries 26.7 uV at f_osc, 10 Ohm 267 uV, and a 2.5 kOhm divider 67 mV.
- **Recommendation:** drive REF from a buffered 2.5 V reference, never from a resistor divider. Reference, noise filter and buffer are in the part recommendations of the review.
- **Status:** Closed 2026-11-08. INA828 REF and the filter returns are on GND, a low-impedance plane (E-1, no mid-supply reference).

### DI-04 Reference ripple at f_osc demodulates to DC

- **Severity:** Major if the demodulator reference is separate from the filter and in-amp reference. Minor, if one shared reference node is built and test R-02 confirms the tracking.
- **Evidence:** P-10 (graded A): 1 mV at f_osc on a separate Vref gives 0.6366 mV (X) or -0.6363 mV (Y) of DC error, which is (2/pi) a. A reference derived from the rail carries half the rail ripple (0.3183 mV per mV). A 10 mA excitation step on a 1 Ohm rail gives -2.500 mV with a rail-derived reference and below 0.0003 mV with an ideal reference. The rail values are test values (TBD). New, from the batch 2 review: if the in-amp REF pin, the filter returns and the demodulator reference are one node, the chain tracks the ripple. The demodulator output is Vref + s and Vref - s and has no DC term. The nodal solution with ideal op amps keeps (VSAMPLE - Vref) / Vd at 11.0793 and +1.630 deg for a reference resistance from 0.1 Ohm to 2.5 kOhm (calc6). The remaining tracking error is estimated at 2e-3 or less, so below 1.3 uV per mV of ripple (not simulated). A coherent ripple of 0.31 uV in a separate reference already equals the SNR = 1 signal of 28.4 nV (P-15, DI-13). The reference IC noise (REF3425 listing: 24 uV rms, 10 Hz to 10 kHz, about 240 nV/sqrt(Hz), not verified against the datasheet) is 1.9 times the chain density in a separate reference.
- **Recommendation:** one buffered reference node for INA828 REF, filter returns and demodulator reference, distributed in a star, with an RC noise filter (1.6 kOhm and 10 uF gives 0.0192 at 517 Hz) before the buffer. No reference from a divider or from the rail. Keep excitation current off this node. Test R-02 (AC tracking and one transient).
- **Status:** Closed 2026-11-08. There is no separate reference on the board. The coherent paths that remain are the reference edges (DI-23) and the bench supply ripple (R-11).

### DI-09 Simulations use a 2 V amplitude, far above the expected signal

- **Severity:** Note.
- **Evidence:** P-01 to P-07 use A = 2 V. P-08 to P-13 use 0.2 V and P-09, P-15 to P-17 use 15 mV at the in-amp input (166 mV at the demodulator input, Draft). Errors that scale with amplitude are no longer overstated. The recommendation also asked for the 5 V-rated parts, which is not yet done because the switch model carries the TMUX6136 parameters.
- **Recommendation:** repeat the key demodulator checks at 0.2 V with the TMUX1136 parameter set (R-04). Close this issue after R-04.
- **Status:** Closed 2026-11-08. P-27 to P-34 use 10 mV, 50 mV and 100 mV drain amplitudes (10 mV default, 50 mV linear range of `simulations/design-context.md` section 4). A 5 V switch is not needed (DI-01).

### DI-10 The Capture front end differs from the simulated single-supply chain

- **Severity:** Major. Critical if the Capture pages are joined as drawn.
- **Evidence:** `differential-amplifier.net` uses +5 V and -5 V (R14, R15 3 Ohm, diode D3), INA828 REF and the filter returns at node 0, and no input bias. `circuits/chain_ss.cir` uses one 5 V rail, REF and the filter returns at a 2.5 V node, and 100 kOhm bias to that node. The front-end output is centred on 0 V and the demodulator input on 2.5 V (0 V to 5 V supply). `simulations/design-context.md` section 2 gives a single rail as Current, with the architecture still open. P-09, P-14 to P-17 describe the rework, which exists only as a file in `circuits/`.
- **Recommendation:** the user decides the supply architecture, then edits the front-end page in Capture to match it: one supply, INA828 REF and filter returns on one buffered 2.5 V node, 100 kOhm bias to the same node, no ground reference in the signal path. If +/-5 V is kept, the demodulator needs +/-5 V and 0 V reference, a switch rated for at least +/-5.5 V, and a bipolar ADC.
- **Status:** Closed 2026-11-08. Superseded by the decision to simulate and build LIA-AFE-Eval (E-1). `circuits/afe_eval.cir` follows the KiCad netlist, and the sheets of the old Capture project are no longer the reference.

### DI-12 Square-wave signals read low against a sine calibration

- **Severity:** Major. The excitation is a Draft square wave and the sensor waveform is TBD.
- **Evidence:** P-17: X is 1.276 % below the fundamental-only value, square/sine ratio 1.25700. The harmonic factor is 0.98725 and its spread with component tolerance is small: std 0.037 % (1 % R, 5 % C), 0.007 % (0.1 %, 1 %) (calc5). The error is systematic and correctable. It assumes an ideal square from the sensor.
- **Recommendation:** calibrate with the signal waveform, or apply the factor 0.98725 with its uncertainty. Do not calibrate a square-wave measurement with a sine tone.
- **Status:** Closed 2026-11-08. The excitation is a sine (requirements Q-7, AN-2), so the square-wave calibration offset does not apply. P-26 gives THD 0.027 % at the gate.

### DI-14 The noise estimate of P-15 is probably optimistic

- **Severity:** Minor.
- **Evidence:** INA828 SBOS792A table 6.5: eNI 7 nV/sqrt(Hz), eNO 90 nV/sqrt(Hz), in 170 fA/sqrt(Hz). At G = 11 the RTI noise is sqrt(7^2 + (90/11)^2) = 10.77 nV/sqrt(Hz). With RG (8.28 nV/sqrt(Hz)) the in-amp gives 13.58 nV/sqrt(Hz), above the 12.68 of the whole chain simulated. With about 4 nV/sqrt(Hz) of filters (assumption) the total is 14.2 nV/sqrt(Hz), 7 % to 12 % above P-15, so A_min is 30.4 nV to 31.7 nV. The factor 0.909 of RG in P-15 is the physical ratio 2RF / (RG + 2RF) = 50 kOhm / 55 kOhm. G = 26 (RG = 2 kOhm) would give 9.5 nV/sqrt(Hz) but cuts the DC input budget to 68 mV. Demodulator op amps at 2.5 V on 5 V may reach 12.5 nV/sqrt(Hz) (DI-15), which raises the demodulator part to 30.9 nV/sqrt(Hz), about 6 % of the noise power.
- **Recommendation:** use the datasheet-based 13.6 nV/sqrt(Hz) to 14.2 nV/sqrt(Hz) for the noise budget. Choose the gain with the sensor DC level (TBD).
- **Status:** Closed 2026-11-08. Replaced by P-30: 729 nV/sqrt(Hz) at the drains (95.9 % pixel shot noise of an ideal 7.5 uA sink), amplifiers 2.1 % of the power, X_OUT noise 16.96 uV rms.

### DI-16 Fixed band-pass against the frequency requirement

- **Severity:** Minor (requirement conflict).
- **Evidence:** `simulations/design-context.md` section 3: 100 Hz to 10 kHz (Draft). The front end is tuned to 520 Hz and the chain gain is 0.425 V/V at 100 Hz and 0.030 V/V at 10 kHz (calc1). The operating frequency of 517 Hz is not in `simulations/design-context.md`.
- **Recommendation:** the user states f_osc, or the tunable range, in `simulations/design-context.md`.
- **Status:** Closed 2026-11-08. The excitation frequency is 518 Hz with the band 377 Hz to 711 Hz (`simulations/design-context.md` section 3, P-24).

