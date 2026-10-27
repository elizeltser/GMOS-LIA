# Design issues

This register lists the design issues found by the design reviewer and by the judge. Each issue has a severity, its evidence, the recommended change and a status. The design reviewer updates it after every batch (see `.claude/agents/design-reviewer.md`). Closed issues stay in the register with the reason for closing.

Severity levels (Critical, Major, Minor, Note) are defined in `docs/design-context.md`, section 7. The numbers quoted below are evidence from the time each issue was written. The current design values are in `docs/design-context.md`.

D-01 to D-09 come from an external review of P-01 to P-07 on 27 October 2026. The design reviewer checked their datasheet values against the full datasheets on 27 October 2026 (batch 2 review, `docs/design-review/2026-10-27_batch2.md`) and added evidence. D-10 to D-16 are new from that review. Findings that rest on Draft or TBD values of `docs/design-context.md` say so.

## Open issues

### D-01 TMUX6136 is not rated for a single 5 V supply

- **Severity:** Critical (confirmed 27 October 2026).
- **Evidence:** TMUX6136 datasheet SCDS397B (August 2025), section 1 and section 5.4: supply +/-5 V to +/-16.5 V (dual) or 10 V to 16.5 V (single), and a VDD to VSS differential of at least 10 V. The LIA runs it from 0 V to 5 V, which is 5 V. The behavioural model `vendor/tmux6136/TMUX6136_BEH.LIB` does not enforce any supply range, so P-01 to P-17 pass. The datasheet gives RON = 235 Ohm typical at 12 V single supply and no value at 5 V. A dual +/-5 V supply meets only the lower limit with no margin (5 % tolerance gives 9.5 V).
- **Recommendation:** use a 5 V switch. First choice TMUX1136DGSR (1.08 V to 5.5 V, RON 2 Ohm, QC -6 pC, tTRAN 12 ns typical, VIH 1.49 V minimum, two SPDT in one VSSOP-10). Backup two TMUX1119DCKR. Charge injection is 15 times the model value, so rerun the demodulator with the new parameters (test R-04). Part data and stock (27 October 2026) are in the review.
- **Status:** open.

### D-02 INA828 input common-mode range on a 5 V supply

- **Severity:** Major (was Critical until checked). Conditional on the sensor common-mode voltage, which is TBD in `docs/design-context.md` section 4.
- **Evidence:** INA828 SBOS792A table 6.5: operating input range (V-) + 2 V to (V+) - 2 V, so 2.0 V to 3.0 V on 0 V to 5 V. Section 7.3.3 gives the dependence on the output voltage in figures 48 to 51 and 55 to 58, which could not be read (not verified). The model clamps at the same limits (P-09, P09b: within 1 mV from 2.02 V to 2.98 V, edges at 2.00 V and 3.00 V). The 2.5 V bias has 0.5 V of margin to each edge (Draft margin 0.2 V). Outside the range the output falls to the reference and does not clip, so the signal disappears without warning. Output swing is (V-) + 0.15 V to (V+) - 0.15 V at +/-15 V (5 V value not verified). With the 0.2 V Draft margin and 0.166 V amplitude the DC differential input budget is (2.5 - 0.15 - 0.2 - 0.166) V / 11 = 0.18 V. Ib and Ios are 0.15 nA typical and 0.6 nA maximum.
- **Recommendation:** keep the INA828 if the sensor common mode stays inside 2.1 V to 2.9 V over temperature. Otherwise use an in-amp with a wider range or level shift the sensor. Confirm with TI's common-mode calculator. The 100 kOhm bias to 2.5 V is correct for the single supply.
- **Status:** open, waiting for the sensor common-mode value.

### D-03 INA828 REF pin needs a low-impedance source

- **Severity:** Major.
- **Evidence:** INA828 SBOS792A section 8.1 and figure 61: any resistance at REF is in series with one of four internal 40 kOhm resistors. Keep it below 5 Ohm. In `chain_ss.cir` the filter returns (R18 and C3) add 8.8 uA and 17.8 uA at 15 mV input (26.7 uA total, calc1). A reference node with 1 Ohm carries 26.7 uV at f_osc, 10 Ohm 267 uV, and a 2.5 kOhm divider 67 mV.
- **Recommendation:** drive REF from a buffered 2.5 V reference, never from a resistor divider. Reference, noise filter and buffer are in the part recommendations of the review.
- **Status:** open.

### D-04 Reference ripple at f_osc demodulates to DC

- **Severity:** Major if the demodulator reference is separate from the filter and in-amp reference. Minor, if one shared reference node is built and test R-02 confirms the tracking.
- **Evidence:** P-10 (graded A): 1 mV at f_osc on a separate Vref gives 0.6366 mV (X) or -0.6363 mV (Y) of DC error, which is (2/pi) a. A reference derived from the rail carries half the rail ripple (0.3183 mV per mV). A 10 mA excitation step on a 1 Ohm rail gives -2.500 mV with a rail-derived reference and below 0.0003 mV with an ideal reference. The rail values are test values (TBD). New, from the batch 2 review: if the in-amp REF pin, the filter returns and the demodulator reference are one node, the chain tracks the ripple. The demodulator output is Vref + s and Vref - s and has no DC term. The nodal solution with ideal op amps keeps (VSAMPLE - Vref) / Vd at 11.0793 and +1.630 deg for a reference resistance from 0.1 Ohm to 2.5 kOhm (calc6). The remaining tracking error is estimated at 2e-3 or less, so below 1.3 uV per mV of ripple (not simulated). A coherent ripple of 0.31 uV in a separate reference already equals the SNR = 1 signal of 28.4 nV (P-15, D-13). The reference IC noise (REF3425 listing: 24 uV rms, 10 Hz to 10 kHz, about 240 nV/sqrt(Hz), not verified against the datasheet) is 1.9 times the chain density in a separate reference.
- **Recommendation:** one buffered reference node for INA828 REF, filter returns and demodulator reference, distributed in a star, with an RC noise filter (1.6 kOhm and 10 uF gives 0.0192 at 517 Hz) before the buffer. No reference from a divider or from the rail. Keep excitation current off this node. Test R-02 (AC tracking and one transient).
- **Status:** open.

### D-05 Resistor mismatch converts input offset into DC error and scale error

- **Severity:** Minor with 0.1 % resistors. Major with 1 % resistors. The tolerance is TBD (`docs/design-context.md` section 6).
- **Evidence:** with R1/R2 = 1 + delta the output gets a DC error of (delta/2) times the input offset and a scale error of delta/2. P-11 confirmed this within 0.0005 mV for delta = +/-0.1 % and +/-1 %, with VY unchanged. The offset at the demodulator input is below 0.25 mV after the high-pass filter (P-09), so the offset term is 0.125 uV at delta = 0.1 %. The scale term dominates: 0.1 % for 0.1 % resistors (R1 against R2 worst case 0.2 %), 1 % for 1 % resistors. X and Y have separate pairs, so their ratio errs by up to 2 x delta/2, which tilts the phase by up to 0.11 deg (0.1 %) or 1.1 deg (1 %). The -0.103 mV/V term of P-11 is a PSpice PULSE-width artefact (quirk) and does not exist with a timer reference.
- **Recommendation:** thin-film 0.1 % resistors, 25 ppm/K, matched pairs (candidates in the review). A per-board gain calibration removes the term.
- **Status:** open.

### D-06 Demodulator input impedance switches at the reference rate

- **Severity:** Minor (Major if driven by a passive network).
- **Evidence:** in the +1 state no current flows in R2, so the input is high impedance. In the -1 state it sees 10 kOhm to the reference. P-12: 10 Ohm in series gives -0.0998 % of X, 100 Ohm -0.985 %, 1 kOhm -8.71 %. 10 Ohm is at the Draft major threshold. In the chain the node is driven by the OPA192 follower U3, whose closed-loop output resistance at 517 Hz is far below 1 Ohm (open-loop value not read, not verified).
- **Recommendation:** drive the node directly from an op amp output, DC-coupled. No series capacitor, protection resistor or RC at this node.
- **Status:** open.

### D-07 No capacitor across the feedback resistor R1

- **Severity:** Note.
- **Evidence:** in the +1 state the gain is 1 for any feedback impedance. In the -1 state it is -Z1/R2. A capacitor across R1 adds a pole to one state only, which gives a gain mismatch and a phase error of about f_osc/f_pole rad. Not exercised in batch 2, no new evidence.
- **Recommendation:** keep R1 without a parallel capacitor, or put its pole above 100 times f_osc and verify the effect.
- **Status:** open.

### D-08 Filter phase tolerance at f_osc

- **Severity:** Major if the board is not calibrated. Minor with a per-board phase and gain calibration. The tolerances and the phase target are TBD, the 1 deg limit is Draft.
- **Evidence:** P-14 (499 samples): phase std 3.44 deg, gain std 3.62 %, 76 % of samples beyond 1 deg. The numpy run (200 000 samples) gives 3.36 deg and 77.3 %. Phase std against tolerance: 0.1 % R with 2 % C 1.32 deg, with 1 % C 0.66 deg, with 0.5 % C 0.34 deg. The capacitors set the spread. Drift: all R and C +0.1 % moves the phase by -0.457 deg and the gain by +0.010 %. Worst-case C0G (30 ppm/K) with thin film (25 ppm/K) over 50 K is 0.275 %, so -1.26 deg and 0.012 % of gain. X7R (-15 %) would give +36 deg and -10 %. The R = sqrt(X^2 + Y^2) reading is insensitive to drift because 517 Hz is near the gain peak. The -0.055 % and -0.13 deg deficit of P-09 and P-14 is not a tolerance issue. Adding 6.4 pF (OPA192 common-mode capacitance, SBOS620E) at the two follower inputs gives -0.058 % and -0.034 deg (calc4), plus the INA828 lag of -0.05 deg. The model connects its capacitors to an internal node, so this is a plausible cause, not a proven one (test R-03). A stray capacitance of a few pF on a board gives the same size.
- **Recommendation:** C0G capacitors, 0.1 % thin-film resistors, one-point gain and phase calibration per board with a tone of the signal waveform (D-12). Compute R for monitoring. Do not use X7R or Y5V.
- **Status:** open.

### D-09 Simulations use a 2 V amplitude, far above the expected signal

- **Severity:** Note.
- **Evidence:** P-01 to P-07 use A = 2 V. P-08 to P-13 use 0.2 V and P-09, P-15 to P-17 use 15 mV at the in-amp input (166 mV at the demodulator input, Draft). Errors that scale with amplitude are no longer overstated. The recommendation also asked for the 5 V-rated parts, which is not yet done because the switch model carries the TMUX6136 parameters.
- **Recommendation:** repeat the key demodulator checks at 0.2 V with the TMUX1136 parameter set (R-04). Close this issue after R-04.
- **Status:** open (partly addressed).

### D-10 The Capture front end differs from the simulated single-supply chain

- **Severity:** Major. Critical if the Capture pages are joined as drawn.
- **Evidence:** `differential-amplifier.net` uses +5 V and -5 V (R14, R15 3 Ohm, diode D3), INA828 REF and the filter returns at node 0, and no input bias. `circuits/chain_ss.cir` uses one 5 V rail, REF and the filter returns at a 2.5 V node, and 100 kOhm bias to that node. The front-end output is centred on 0 V and the demodulator input on 2.5 V (0 V to 5 V supply). `docs/design-context.md` section 2 gives a single rail as Current, with the architecture still open. P-09, P-14 to P-17 describe the rework, which exists only as a file in `circuits/`.
- **Recommendation:** the user decides the supply architecture, then edits the front-end page in Capture to match it: one supply, INA828 REF and filter returns on one buffered 2.5 V node, 100 kOhm bias to the same node, no ground reference in the signal path. If +/-5 V is kept, the demodulator needs +/-5 V and 0 V reference, a switch rated for at least +/-5.5 V, and a bipolar ADC.
- **Status:** open.

### D-11 Sensor source impedance, bias resistors and noise were not simulated

- **Severity:** Major. Rests on the sensor impedance, which is TBD.
- **Evidence:** all chain tests used 1 mOhm per leg (`rsens` in `chain_ss.cir`). With Rs per leg and 100 kOhm to the reference on each input, the gain is multiplied by 200 kOhm / (200 kOhm + 2 Rs): 0.990 at 1 kOhm, 0.909 at 10 kOhm. Gain loading exceeds the Draft 0.1 % threshold from 100 Ohm. Input-referred noise rises from 12.68 nV/sqrt(Hz) to 14.06 (1 kOhm), 23.77 (10 kOhm) and 88.6 (100 kOhm) nV/sqrt(Hz) referred to the sensor EMF, and A_min from 28.4 nV to 31.5, 53.2 and 198 nV (calc2). A sensor whose impedance carries the measurement makes the loading a signal-dependent gain error.
- **Recommendation:** define the sensor impedance range. Choose the bias resistors from it (larger values cost only offset, which the high-pass filter blocks). Test R-01.
- **Status:** open.

### D-12 Square-wave signals read low against a sine calibration

- **Severity:** Major. The excitation is a Draft square wave and the sensor waveform is TBD.
- **Evidence:** P-17: X is 1.276 % below the fundamental-only value, square/sine ratio 1.25700. The harmonic factor is 0.98725 and its spread with component tolerance is small: std 0.037 % (1 % R, 5 % C), 0.007 % (0.1 %, 1 %) (calc5). The error is systematic and correctable. It assumes an ideal square from the sensor.
- **Recommendation:** calibrate with the signal waveform, or apply the factor 0.98725 with its uncertainty. Do not calibrate a square-wave measurement with a sine tone.
- **Status:** open.

### D-13 ADC resolution and interface

- **Severity:** Minor. Rests on the ADC and the resolution target, both TBD.
- **Evidence:** DC-band noise at VX is 0.2001 uV rms (126.56 nV/sqrt(Hz) x sqrt(2.5 Hz), P-15). A 16-bit, 5 V ADC adds 22.0 uV rms of quantisation noise (110 times), 18 bit 5.5 uV (27.5 times), 20 bit 1.38 uV (6.9 times), 24 bit 0.086 uV (0.43 times, ideal). Resolving 0.2 uV in 5 V needs 24.6 bits. The 10 kOhm output resistor with 1 uA of ADC input current drops 10 mV (9.5 % of 105.8 mV). The 2f ripple at VX is about 0.108 mV peak at tau = 0.1 s and 166 mV, attenuated only to 1.5e-3 at 1034 Hz by a first-order filter, which an ADC sampling can alias.
- **Recommendation:** pick the ADC from the resolution target. Add a buffer after R3 or use a high-impedance delta-sigma input, and set the sampling rate and filter so that the 2f ripple does not alias.
- **Status:** open.

### D-14 The noise estimate of P-15 is probably optimistic

- **Severity:** Minor.
- **Evidence:** INA828 SBOS792A table 6.5: eNI 7 nV/sqrt(Hz), eNO 90 nV/sqrt(Hz), in 170 fA/sqrt(Hz). At G = 11 the RTI noise is sqrt(7^2 + (90/11)^2) = 10.77 nV/sqrt(Hz). With RG (8.28 nV/sqrt(Hz)) the in-amp gives 13.58 nV/sqrt(Hz), above the 12.68 of the whole chain simulated. With about 4 nV/sqrt(Hz) of filters (assumption) the total is 14.2 nV/sqrt(Hz), 7 % to 12 % above P-15, so A_min is 30.4 nV to 31.7 nV. The factor 0.909 of RG in P-15 is the physical ratio 2RF / (RG + 2RF) = 50 kOhm / 55 kOhm. G = 26 (RG = 2 kOhm) would give 9.5 nV/sqrt(Hz) but cuts the DC input budget to 68 mV. Demodulator op amps at 2.5 V on 5 V may reach 12.5 nV/sqrt(Hz) (D-15), which raises the demodulator part to 30.9 nV/sqrt(Hz), about 6 % of the noise power.
- **Recommendation:** use the datasheet-based 13.6 nV/sqrt(Hz) to 14.2 nV/sqrt(Hz) for the noise budget. Choose the gain with the sensor DC level (TBD).
- **Status:** open.

### D-15 OPA192 at mid-supply on a 5 V rail

- **Severity:** Minor.
- **Evidence:** OPA192 SBOS620E: the input stage has a transition region for (V+) - 3 V < VCM < (V+) - 1.5 V, which is 2.0 V to 3.5 V on 5 V. All OPA192 stages work at 2.5 V, inside it. Offset at VCM = (V+) - 1.5 V is +/-25 uV typical and +/-150 uV maximum (0 C to 85 C), table 6.7 of the 8 V to 36 V case. Two times the offset is a static baseline at VX of 10 uV to 300 uV, which is 50 to 1500 times A_min after division by 7.05 V/V. P-13 shows a model offset below 2 uV, so the model probably does not represent the region (not verified).
- **Recommendation:** keep the OPA192 for the filters. For the demodulator op amps consider the zero-crossover OPA388 (candidates in the review). The measurement can use the active/blind difference to remove the baseline.
- **Status:** open.

### D-16 Fixed band-pass against the frequency requirement

- **Severity:** Minor (requirement conflict).
- **Evidence:** `docs/design-context.md` section 3: 100 Hz to 10 kHz (Draft). The front end is tuned to 520 Hz and the chain gain is 0.425 V/V at 100 Hz and 0.030 V/V at 10 kHz (calc1). The operating frequency of 517 Hz is not in `docs/design-context.md`.
- **Recommendation:** the user states f_osc, or the tunable range, in `docs/design-context.md`.
- **Status:** open.

## Closed issues

None yet.
