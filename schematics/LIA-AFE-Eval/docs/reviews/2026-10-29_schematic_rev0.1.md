# LIA-AFE-Eval — Design Review of Schematic Rev 0.1

Date: 2026-10-29. Reviewer: design-reviewer agent (analog hardware review). Status: first review of the uncommitted rev 0.1 entry.

## 1. Scope and Method

| Item | Content |
|------|---------|
| Reviewed | All nine sheets as exported in `LIA-AFE-Eval.net` (read with a script that dumps parts and nets; `netcheck`: 0 findings; `T01.txt`: 249/249 passed; `kicad-cli sch erc`: 12 messages, 1 error, 11 warnings, all discussed in F-18) |
| Documents used | [README.md](../README.md) (E-1…E-8, S-1…S-6), [requirements.md](../requirements.md) rev B, [component_selection.md](../component_selection.md), LIA-Readout [schematic_overview.md](../../../LIA-Readout/docs/schematic_overview.md) §3, §4.4–4.9 and [requirements.md](../../../LIA-Readout/docs/requirements.md), `simulations/design-context.md` (last change log line 2026-10-27), `simulations/design-issues.md` |
| Datasheets read in full text | TMUX6136 SCDS397B (Aug 2025), TMUX1109 SCDS406A (Feb 2024), DAC80508 SLASEL1D (Aug 2018), INA828 SBOS792A (Jan 2018), INA190 SBOS863D (Nov 2019), OPA196/OPA2196 SBOS869 (Jul 2017), LT3094 Rev. B (`docs/lt3094.pdf`) |
| Not available | ADP7118 datasheet (download timed out), STM32F303/NUCLEO-F303RE datasheet, GMOS sensor model. Statements that need them say "not verified" |
| Calculations | [scripts/2026-10-29_schematic_rev0.1_calc1.py](scripts/2026-10-29_schematic_rev0.1_calc1.py) (pure Python, all numbers in this review that carry units come from it unless a datasheet is cited) |

Severity words follow the request: **blocker** (the board will not work or a part is outside its rating), **major** (works, but an error or risk is large for the bench goal), **minor**, **suggestion**. The 0.2 V headroom margin and the 0.1 % / 1° error threshold of `design-context.md` §7 are Draft values and are used as such.

## 2. Summary

No blocker found. All pinouts that could be checked against a datasheet match the netlist (§6). The first spin should power up and the signal chain should work. Six items are rated major because each can cost a bench session or a part; four of them are cheap schematic changes.

| ID | Severity | Nets / parts | One line |
|----|----------|--------------|----------|
| F-01 | major (verify) | U8, C70, `+5VA` | DAC80508 reference alarm may trip with `+5VA` below 5.0 V: gain-2 coarse channels need VREF/DIV ≤ VDD/2 and the LDO is 5.0 V ±1 % (not verified) |
| F-02 | major | U23, R64/R67, `DSENSE_A/B`, J7.19/20 | Drain-sense output reaches 4.9 V into a NUCLEO ADC pin whenever no pixel is selected |
| F-03 | major | R74…R77, C92, C93, U26B/U27B | VMID_PF divider sets a DC offset and drift of the X/Y outputs; tolerance and TCR are unspecified (S-1) and C.9 would give 1 % basic parts |
| F-04 | major | TP15/TP16, `DRN_A/B`, J3, U20/U21 | Test loops and probes on the 330 kΩ drain nodes; leakage and guarding are not defined |
| F-05 | major | U24/U25 SEL, J7.4/6 | `REF_X/REF_Y` have no series resistor; NUCLEO powered with the board off clamps into the `+9V` rail through the TMUX6136 SEL diode |
| F-06 | major | C40, C62, C54 and other X7R caps | LDO output and input capacitors lose capacity with DC bias; LT3094 needs 10 µF effective, ratings are missing on most capacitors |
| F-07 | minor | U9, U10 | Loop phase margin 40…50° estimated with the OPA2196 (GBW 2.5 MHz); add DNP compensation pads |
| F-08 | minor | U10, U9, U26/U27 | Op-amp inputs sit in or at the OPA2196 input transition region (V+ − 3 V … V+ − 1.5 V) |
| F-09 | minor | IC1/IC3, U9, TMUX1109 | Heater path: INA190 full scale 8.7 mA, 300 Ω heater would clip, switch drop is outside the Kelvin loop |
| F-10 | minor | J7, U8 `CS`, `SPI_*`, `REF_*` | Idle levels and edge rates of the cable: no pull-up on `DAC_CS`, no damping on SPI and reference lines |
| F-11 | minor | C70 | DAC reference capacitor equals the datasheet minimum before X7R derating (answers S-2) |
| F-12 | minor | `GND` | One ground net for analog, digital, heater return and cable; DC-4 asks for a single join point |
| F-13 | minor | J4, `+9V`, `-9V` | No overvoltage or hot-plug protection; TMUX6136 and LT3094 limits define the allowed input |
| F-14 | minor | R80/R85, J8/J9 | 100 Ω output resistors: a 50 Ω scope input gives 1/3 of the amplitude and 17 mA from the op amp |
| F-15 | minor | J3 pins 15/36 | Sensor ESD-structure supply taken directly from `+5VA` |
| F-16 | suggestion | all OPA2196 | Simulations use the OPAx192 model; the board uses OPA2196 (GBW 2.5 MHz, 15 nV/√Hz) |
| F-17 | suggestion | — | A scope cannot resolve the X/Y noise floor (3.7 µV rms); plan DMM or averaging |
| F-18 | suggestion | ERC, footprints | Agree with the benign ERC list; two library clean-ups; footprint checks for S-5 |
| F-19 | note | documents | Disagreements between documents (listed in F-19) |

## 3. Findings: Major

### F-01 DAC80508 reference alarm margin at VDD = 5.0 V (verify on the bench)

- **Where:** U8 `DAC80508ZRTET` (VDD pin 7 on `+5VA`, REF pin 1 with C70). Coarse drain channels `DAC2`, `DAC3` need gain 2 (LIA-Readout §4.6.1, range 0.5–3.5 V at the supply side of R_D, AN-9).
- **Evidence:** SLASEL1D §7.3: with the reference divider disabled, VREFIN must not exceed VDD/2 for VDD = 3.3…5.5 V. §8.3.2.1: an improper divider configuration "issues a reference alarm condition … the reference buffer is shut down, and all the DAC outputs go to 0 V". STATUS.REF-ALM (Table 16) "reads 1 when the difference between VREF/DIV and VDD is below the required minimum analog threshold"; the threshold value is not tabulated. Internal reference = 2.5 V, so gain 2 (full scale 2 × 2.5 V = 5.0 V) needs VDD ≥ 5.0 V. `+5VA` is a fixed 5.0 V ADP7118 whose accuracy is ±1 % in my recollection (4.95…5.05 V; datasheet not retrieved).
- **Consequence:** if the alarm criterion is the 5.0 V line of §7.3, any `+5VA` below 5.00 V (about half of all units) switches all eight outputs, including the gates and heaters, to 0 V with no error indication on the board. The failure looks like a firmware or wiring fault. If TI's alarm threshold is looser, there is no effect. This is also an LIA-Readout question (same rail, same DAC).
- **Fix / test:** (a) First bench test: read STATUS.REF-ALM with `+5VA` measured at TP3, at 25 °C and warm (test B-5). (b) If it trips or the margin is under 20 mV: feed VDD of the DAC from a rail above 5.0 V (an ADP7118 5.0 V cannot do this; the ±9 V rail through an LDO or a 5.5 V trimmed output would), or accept a coarse range of 0…2.5 V with gain 1 and re-derive the drain trim (3.5 V at the supply side is then out of reach, so this needs an owner decision on AN-9). Record the answer in `requirements.md`.
- **Also for firmware:** the 80508**Z** powers up with GAIN = 1 on all channels; the gain-2 bit must be set for `DAC2/3` before the drain supplies are used. Datasheet §8.3.3.1: registers reset on POR, outputs stay at zero code until written.

### F-02 `DSENSE_A/B` can reach 4.9 V at a NUCLEO ADC pin

- **Where:** U23 (drain sense, gain 8, on `±5VA`), R64/R67 10 kΩ, C78/C79 1 µF, J7.19/20, nets `DSENSE_A/B`.
- **Evidence:** with MUX_EN low (the power-up state, R38 pull-down) or a pixel position that is open, `DRN_A/B` is pulled to `VSUP_A/B` through R_D; the drain supply is 0.5…3.5 V (AN-9). U23 multiplies by 1 + 7.15 k/1.02 k = 8.01, so its output sits at the positive swing limit. OPA2196 swing is 50…110 mV from the rail at 10 kΩ (SBOS869 §6.5), so ≈ 4.9 V. The STM32F303 analog pins are not 5 V tolerant in analog mode (not verified; datasheet not available). The 10 kΩ limits the current to about 0.13 mA into a clamp at 3.3 V + 0.3 V, which the pin survives, but it disturbs the other ADC channels and the NUCLEO 3V3 rail (script section 7). The same happens at the negative side if `VSUP` is set negative (difference amplifier with k = 0.1 gives −0.1 × V_fine when V_coarse is 0).
- **Fix:** add a BAT54S (LCSC C7420333, preferred part, 760 190 in stock on 2026-10-29) from each `DSENSE` node to `+3V3` and `GND` (anodes/cathodes as a double clamp), after R64/R67. Alternative with the same effect: power U23 from `+3V3`/`GND`, but then the 3.3 V swing cuts the 0.41 V × 8 range only if V_DRN stays below 0.4 V, so the clamp is simpler. Firmware rule in any case: never leave a drain supply on with no pixel selected.
- **Test:** B-4 (measure `DSENSE` with EN = 0 and the drain DAC at 3 V before connecting the NUCLEO).

### F-03 VMID_PF divider: offset and drift of X_OUT / Y_OUT (S-1)

- **Where:** R74/R75 (VMID), R76 150 k / R77 100 k (VMID_PF), C92, C93, U26B/U27B +IN.
- **Derivation:** the post-filter is inverting with gain −R_F/R_IN = −1.5 and +IN = r × VMID with r = R77/(R76 + R77) = 0.4. X_OUT = (1 + 1.5) r × VMID − 1.5 V_dem = VMID + 2.5 (r − 0.4) VMID − 1.5 V_dem. The output is centred on VMID only if r is exactly 0.4. X_OUT − VMID is what the bench (and later the ADS1220) reads. The demodulator itself uses GND as its zero (S1B on `GND`), so VMID does not enter the demodulator; ripple on `+5VA` at 518 Hz is not demodulated (checked, no issue).
- **Numbers (script section 5):**

| Resistors R76, R77 | Worst-case offset of X_OUT − VMID | Drift of X_OUT − VMID | Drain-referred (÷ 38.2) |
|--------------------|------------------------------------|------------------------|--------------------------|
| 0.1 %, tracking within 5 ppm/K | 3.0 mV | 8 µV/K | 0.20 µV/K (= AN-23b limit) |
| 0.1 %, 25 ppm/K parts, no tracking (50 ppm/K difference) | 3.0 mV | 75 µV/K | 1.96 µV/K |
| 1 %, basic part, 100 ppm/K | 30 mV | 300 µV/K | 7.9 µV/K |

AN-23b (LIA-Readout) allows 0.2 µV/K referred to the drain signal, and AN-9 of this board adopts it. The 3 mV offset is removed by the zero calibration; the drift is not.
- **Evidence for the risk:** the schematic fields give R76/R77 `Tolerance 0.1 %` but no MPN and no TCR; `component_selection.md` §C.9 says non-critical resistors are JLCPCB basic parts (1 %, 100 ppm/K).
- **Fix:** specify R76 and R77 as one thin-film pair (same family as R_IN/R_F: Yageo RT0603B, 0.1 %, ≤ 10 ppm/K), add MPN and TCR fields, and mark them as critical in C.8. Optional: since the board has no ADC, the post-filter +IN could go to `GND` and X_OUT would centre on 0 V, removing the divider; this breaks the "same circuit as LIA-Readout" rule (E-3, BU-1), so it is the owner's decision.
- **Also:** VMID is loaded by 250 kΩ and falls from 2.500 V to 2.451 V; this is harmless because X_OUT tracks VMID. J10.5 carries VMID (5 kΩ source): measure it with a DMM, not a 1 MΩ scope input.

### F-04 Drain nodes: test loops, probes, leakage, guarding

- **Where:** `DRN_A`, `DRN_B` (R25/R31 pin 1, TP15/TP16, U20/U21 DA, U2 pins 2/3, U23 +IN), J3 drain pins, unguarded.
- **Source impedance:** each node sees 330 kΩ (R_D) toward the supply. Node capacitance is estimated at 55 pF (TMUX1109 on-capacitance ≈ 38 pF per LIA-Readout §4.4, INA828 4 pF, OPA2196 1.6 pF, socket and trace ≈ 10 pF; assumed). Pole 8.8 kHz; at 518 Hz the lag is 3.4° and the gain −0.015 dB, equal on both sides.
- **Probe on one node (script section 3):**

| Load on one `DRN` node | DC loading of the node | Extra lag at 518 Hz | CMRR if on one side only |
|------------------------|------------------------|---------------------|---------------------------|
| 10 MΩ ∥ 11 pF (10:1 probe) | 3.2 % of R_D | 0.7° | 39 dB (10 pF mismatch) |
| 1 MΩ ∥ 100 pF (1:1 probe or cable) | 25 % | 6.1° | below 39 dB |
| Test loop only (≈ 1–2 pF), both sides equal | none | none | no change |
| 5 pF mismatch (layout or socket) | — | — | 45 dB (LIA-Readout system CMRR target is 48 dB, INA828 alone is ≥ 110 dB at G = 10) |

  A probe on a high-impedance node therefore wrecks the very CMRR the board is built to measure. The two loops also act as antennas.
- **Leakage:** TMUX1109 off leakage is ±0.08 nA (source) and ±0.1 nA (drain) at 25 °C, ±0.75 nA at 85 °C (SCDS406A §5.5). Into 330 kΩ this is 33 µV at 25 °C and 250 µV at 85 °C, DC only. Board contamination is the larger risk: 4 V (heater) across 10⁹ Ω is 4 nA = 1.3 mV on the node. In the GMOS pin map each drain pin has a heater pin as neighbour (pin 17 next to pin 18 = heater 6, pin 10 next to pin 11 = heater 1, pin 3 next to pin 4, and so on). The chosen socket (BOOMELE C2332, tin contacts) has no leakage figure in LCSC data.
- **Fix:** (a) Keep the loops but label them "DC only, 10 MΩ probe, one side at a time never"; or remove TP15/TP16 and rely on `DSENSE_A/B` (buffered ×8, DC) plus `INA_OUT` for the AC signal. (b) Add a DNP footprint for a unity-gain buffer (OPA2196 section) after a 10 kΩ at each drain node only if the owner needs the AC drain signal on the scope. (c) Layout: GND guard ring (not a driven guard) between drain and heater/gate traces, no solder mask openings, wash flux, keep `DRN_A` and `DRN_B` equal in length and neighbours; no digital or REF line within 5 mm. (d) Socket: machined-pin socket with PTFE or air gaps, or the ZIF option already named in C.3.
- **Test:** B-6 (CMRR with a deliberate 10 pF) and B-7 (leakage: open-pin DRN, measure DC drift with a hair dryer).

### F-05 Cross-powering with the NUCLEO, reference lines without damping

- **Where:** `REF_X`, `REF_Y` (J7.4/6 → TP8/TP9 → U24.1 / U25.1), `+3V3` (J7.25/26 → U8 VIO, IC1/IC3 VS and ENABLE).
- **Evidence:** TMUX6136 SCDS397B §5.1: digital pin voltage ≤ VDD + 0.3 V and ≥ GND − 0.3 V, current ±30 mA. SEL has a 6 MΩ internal pull-down (§5.5), VIH = 2 V min, VIL = 0.8 V max, so 3.3 V CMOS drives it correctly and a floating cable is safe. TMUX1109 logic pins: −0.5…6 V independent of VDD (SCDS406A §5.1). DAC80508 digital pins ≤ VIO + 0.3 V and VIO comes from the same NUCLEO 3V3, so they are consistent.

| State | Result |
|-------|--------|
| Board powered, NUCLEO off | Safe. SEL pulled down internally; MUX_EN pulled down by R38; DAC VIO = 0 → DAC outputs stay at zero code; INA190 off |
| NUCLEO on, board off, firmware running | `REF_X/Y` swing to 3.3 V while TMUX6136 VDD ≈ 0 V: SEL exceeds VDD + 0.3 V and conducts through its input diode into the `VDD_SW`/`+9V` net |
| Both on, NUCLEO resets | GPIO high-Z for a few ms: `DAC_CS`, `SPI_*` float (F-10) |

  Estimated clamp current for the second state (3.3 V source, 25 Ω MCU output resistance): 108 mA with no resistor (the MCU limits it, but the 30 mA datasheet limit and the 25 mA STM32 pin limit are exceeded), 22 mA with 100 Ω, 7.6 mA with 330 Ω, 2.6 mA with 1 kΩ. The injected current also charges C52/C56/C60 on `+9V` and can start the ADP7118 partially.
- **Fix:** series resistor of 330 Ω to 1 kΩ in each of `REF_X` and `REF_Y` at the connector (J7 side of TP8/TP9), as LIA-Readout AN-6 already specifies 100 Ω at the MCU; with 5 pF input capacitance the edge stays below 10 ns. Add a note on the silkscreen: "power the board first, NUCLEO second; remove the NUCLEO before powering the board down". Also put 100 Ω–330 Ω in series with `SPI_SCLK`, `SPI_MOSI`, `DAC_CS` (F-10).
- **Test:** B-3 (drive the cable with the board off, measure `+9V`).

### F-06 LDO and rail capacitors: DC-bias derating and missing voltage ratings

- **Where:** C40 (`-5VA`, 10 µF 0805 X7R), C62 (`+5VP`, 2.2 µF 0603 X7R, plus two 100 nF), C58 (`+5VA`), C43 (4.7 µF SET), C52/C54 (`±9V`, already 25 V), all C74/C75 (10 µF 0805).
- **Evidence:** LT3094 pin functions (`docs/lt3094.pdf` p. 15): "For stability, use a minimum 10 µF output capacitor with an ESR below 30 mΩ". A 10 µF 0805 X7R of 10 V or 16 V typically keeps 40…70 % of its value at 5 V DC (typical for class II ceramics; the part is not chosen, so the figure is an estimate). The ADP7118 datasheet minimum was not retrieved (`component_selection.md` §C.2 says C_OUT ≥ 2.2 µF X7R). `+5VP` has only C62 and 2 × 100 nF, so after derating 2.2 µF 0603 keeps about 1.0…1.4 µF.
- **Voltage field:** the schematic carries `Voltage 25V` only on the `±9V` capacitors. C40, C58, C62, C43, C67, C74/C75 and all signal-path capacitors have no voltage field; JLC basic 0805 10 µF parts are often 10 V. At 5 V a 10 V part derates strongly and at the `-5VA`/`+5VA` rails of the LT3094 start-up there is no margin.
- **Consequence:** LDO peaking or oscillation shows as noise on `-5VA` at 10…500 kHz. It couples into the in-amp reference (REF = GND) and the demodulator, not at 518 Hz but through rectification.
- **Fix:** set C40 to 22 µF 1206 X7R ≥ 16 V (or two 10 µF in parallel); C62 to ≥ 4.7 µF 0805 X7R ≥ 10 V; give every capacitor a `Voltage` field (≥ 16 V on ±5 V rails, ≥ 25 V on ±9 V rails, ≥ 16 V for C74/C75). For the 10 µF drain-filter capacitors C74/C75 the derating only moves the 16 Hz corner (see F-07 for the loop), but film or C0G would remove the piezo and leakage effects; leave as is for the first spin.
- **Test:** B-2 (scope the three rails with a load step).

## 4. Findings: Minor

### F-07 Phase margin of U9 (heater) and U10 (drain supply)

- OPA2196: GBW 2.5 MHz, open-loop output impedance 700 Ω at 1 MHz, input capacitance 1.6 pF differential and 6.4 pF common mode (SBOS869 §6.5). With 49.9 kΩ feedback (U9) or 9 kΩ source (U10), the input capacitance (8…14 pF including layout) puts a pole at 0.6…1 MHz near the 0.4…1.7 MHz loop crossover.
- Script sections 1 and 2: U9 (feedback after the 15 Ω shunt, load 600 Ω ∥ 100 pF) PM = 42…53° without compensation, 55…66° with 3.3 pF across R26/R20; U10 PM = 40…51°, 52…62° with 3.3 pF across R21/R27. The estimate uses a single-pole op-amp model and assumed capacitances, so it is a risk, not a failure. A 45° margin shows as 20 % overshoot and ringing at a few hundred kHz on `VSUP` and `HTR`.
- **Fix:** add DNP 0603 C0G footprints (3.3 pF to 5.6 pF) in parallel with R26, R20 (U9) and R21, R27 (U10). Cheap on a spin where everything is hand-probed. Test B-8 (step response of `HTR_A` and `VSUP_A`).

### F-08 OPA2196 input transition region

- SBOS869: offset and CMRR change for (V+) − 3 V < VCM < (V+) − 1.5 V; noise density is 53 nV/√Hz at 100 Hz above (V+) − 1.5 V (versus 18 nV/√Hz below). V+ = 5 V gives 2.0…3.5 V.
- U10 +IN is the coarse DAC at 0.45…3.2 V (AN-9, factor 1.1): the supply range above ≈ 2.2 V runs through the transition region, so the DAC-to-supply transfer has a kink of up to the offset specification (±100 µV max; typical shift not read from the curves). AN-10 wants 100 µV steps.
- U9 +IN at 4.0 V heater voltage is 2.0 V: on the edge.
- U26A/U27A +IN follows `BPF_OUT`; at the 50 mV pk drain limit (AN-23a) it reaches 1.98 V (script section 4): on the edge, which is acceptable. The in-amp output with 200 mV drain mismatch is 1.98 V DC + 0.5 V pk; the HPF removes the DC (checked, no issue).
- **Fix / test:** none before the spin; B-9 sweeps the coarse DAC and looks for a step near 2.0…3.5 V. If a step appears, power U10 from `+9V`/`-5VA` (output stays below 5.5 V by DAC range) or keep the operating point below 2.0 V.

### F-09 Heater path

- INA190A1 (G = 25) on 3.3 V (SBOS863D): full-scale output ≈ VS − 50 mV; at a 15 Ω shunt this is 8.7 mA. At 4.0 V a 600 Ω heater (6.7 mA, 2.5 V out) fits; 300 Ω (13.3 mA, would give 5 V) clips. LIA-Readout AN-16 lists 600 Ω–1.2 kΩ as an `ASSUMPTION` and conflicts with 300 Ω in the experiment notes; this board must be tested with the real heater value first.
- Driver output at 4.0 V and 6.7 mA is 4.10 V on `+5VP` = 5.0 V; OPA2196 swing is 50…110 mV (10 kΩ) and 200…500 mV (2 kΩ) from the rail, so the margin (0.9 V) is above the 0.2 V limit.
- The Kelvin point (R26/R20, INA190 IN−) is before the TMUX1109 DB switch. The switch drop (RON ≤ 4.5 Ω at 85 °C, SCDS406A §5.5) × 6.7 mA = 30 mV is not compensated; the pixel gets 4.0 V − 30 mV. The reading `HSENSE` still shows the true current. Acceptable; record it.
- U9 +IN: see F-08.

### F-10 Cable idle levels and edges

- `DAC_CS` (J7.11 → U8.12) has no pull-up. While the NUCLEO pins are high-Z (reset, boot, unplugged ribbon) CS can float low and `SPI_SCLK` noise can clock a spurious frame into the DAC (heater and gate setpoints). Add 100 kΩ from `DAC_CS` to `+3V3` (`+3V3` is from the NUCLEO, so it is off when the NUCLEO is off: nothing can write then).
- `SPI_SCLK/MOSI`, `REF_X/Y` run in a 26-way ribbon with edges of a few ns. Without damping this means ringing (undershoot below −0.3 V at the TMUX SEL pins) and radiated pick-up in `INA_OUT`. 100 Ω to 330 Ω in series at the J7 side. This is the same advice as F-05.
- The ribbon order (IF-5) puts a GND wire on both sides of `EXC_DAC`, `REF_X`, `REF_Y`: good (checked, no issue).

### F-11 DAC reference capacitor (S-2)

- SLASEL1D §8.3.2: "A minimum 150 nF capacitor is recommended between the reference output and GND for noise filtering". C70 is 150 nF X7R 0603; with DC bias (2.5 V) and tolerance it is below the minimum. Use 220 nF…1 µF (reference noise 130 nV/√Hz at 10 kHz with 10 nF load; output noise density 78 nV/√Hz at 1 kHz). The reference load capability is ±5 mA and the REF pin has no other load (checked).
- Resolution check: DAC noise at `VSUP` after the 16 Hz R60/C74 filter is 2.6 nV/√Hz (78 nV × 1.1 × 0.031), well under the 50 nV/√Hz limit of AN-10.

### F-12 Ground strategy

- All analog, digital, heater and cable returns are one net `GND` (netlist). DC-4 asks for digital and analog ground to join at one point; the schematic gives the layout no way to do it (no `DGND`, no net tie).
- Currents that matter: heater returns (2 × 6.7 mA DC) enter at J3 HN pins; the NUCLEO digital return flows through the ribbon GND wires (ten wires); the SMA shields join through the scope. A 10 mΩ shared trace gives 67 µV DC from the heater return alone. 518 Hz content on the return paths comes only from the reference lines and the excitation.
- **Fix:** a single `GND` plane is fine for a bench board if (a) heater returns J3 HN1…HN6 and the DIP source pins leave the socket through separate vias to the plane at the power entry (the INA828 REF pin, the TMUX6136 S1B zero and the GND of C13…C14 stay on the quiet side), (b) the J7 ribbon returns enter on the opposite side from the front end. If separate nets are wanted, add a net tie symbol now and `AGND`/`DGND` names.
- Bench loops: NUCLEO USB ground, the lab supply ground and the scope earth form loops through this ground. Power the NUCLEO from the same PC as the scope, or use a USB isolator; check B-10.

### F-13 Input protection and limits

- J4 → D4/D9 (B5819W: 40 V, 1 A) give reverse-polarity protection (checked: reversing +V/−V or both blocks). The drop is 0.35…0.4 V at the load current (≈ 50 mA).
- No fuse, TVS or bulk capacitor on the input. Hot-plug of a charged supply through a lead of about 1 µH onto 10 µF + 3 × 1 µF ceramic can ring to 2 × V_in. The ADP7118 absolute maximum for VIN is 20 V (not verified), LT3094 IN −20 V, TMUX6136 VDD−GND 18 V and VDD−VSS 36 V (SCDS397B §5.1). The TMUX6136 recommended range is VDD ≤ 16.5 V, i.e. an input of about ±16.9 V.
- **Fix (optional, cheap):** SMAJ12A (LCSC C152123, 32 538 in stock on 2026-10-29, Vrwm 12 V, clamp 19.9 V) on `+9V`→GND and GND→`-9V` (reverse orientation) after the diodes, or a one-line note on the silkscreen "max ±12 V". Do not set ±15 V on the bench supply.
- Sequencing (checked, no issue): `-5VA` needs 550 ms (LT3094 C_SET 4.7 µF, `docs/lt3094.pdf` start-up table, PGFB tied to IN so no fast start-up), `+5VA/+5VP` need under 1 ms. For 0.5 s the OPA2196 and INA828 have V− = 0 V with inputs at 0 V: inside their range, no latch-up path, outputs sit near 0 V. DAC outputs are zero (Z variant). The LT3094 pins are handled as the datasheet says: EN/UV and PGFB tied to IN ("if unused"), ILIM to GND ("tie ILIM to GND, do not float"), PG and VIOC floating, GND and SET return at the ground side; the exposed pad is IN (−9 V), not ground, so the pour under U19 is `-9V` and must not touch `GND`.
- Dissipation: ADP7118 at ±12 V in with 40 mA is 0.26 W (LFCSP 2 × 2); at ±9 V 0.14 W (script section 9).

### F-14 Output resistors into cables

- R80/R85 (100 Ω) are outside the feedback loop (`X_OUT` feedback is taken at R15.2/C13.2, before R80): checked, correct. Into the scope at 1 MΩ the node is 99.99 % of its value. Into 50 Ω the output is 33 % (0.83 V instead of 2.5 V centre) and the op amp supplies 16.7 mA continuously (OPA2196 short-circuit current ±65 mA). Cable capacitance of 100 pF per metre with 100 Ω gives a 16 MHz pole: no stability issue (CL drive 1 nF, SBOS869).
- Fix: silkscreen "1 MΩ input only"; mention in the bench procedure.

### F-15 Sensor ESD supply

- J3.15/J3.36 connect to `+5VA` without a filter (AN-33, ≈ 5 mA). Supply ripple reaches gates and drains through the package ESD structure capacitance. A local 10 Ω + 10 µF would reduce it; `+5VA` is a quiet LDO output, so this is a layout item (bypass 100 nF at the socket, short return). Not blocking.

## 5. Findings: Suggestions and Notes

### F-16 Simulation model of the op amp

`design-context.md` §6 lists OPAx192 as the current demodulator op amp and the model in `simulations/ti-pspice/vendor/sbom862f/` is for OPAx192. The board uses OPA2196 (SBOS869: GBW 2.5 MHz, noise 15 nV/√Hz at 1 kHz below the transition region, 700 Ω open-loop output impedance, offset ±100 µV max). OPA192 is faster and quieter (values from memory of SBOS620E, not re-checked here). Filter phase and gain errors at 518 Hz from the finite GBW are small (≈ 0.05° per section), but stability, noise and settling simulations of U9, U10 and the demodulator must use an OPA196 model. Stability results from the OPAx192 model are optimistic.

### F-17 Measuring the result

Noise at the drain input: R_D legs 73.9 nV/√Hz each, INA828 current noise 56 nV/√Hz per leg (170 fA/√Hz × 330 kΩ), INA828 voltage noise 7 nV/√Hz: 131 nV/√Hz differential, 3.2 % of the 730 nV/√Hz sensor shot noise (AN-23: ≤ 10 %, passes). In the 0.56 Hz noise bandwidth of τ = 0.45 s this is 98 nV rms at the drain, 3.7 µV rms on X_OUT. A scope shows ≈ 1 mV resolution at 100 mV/div, so only large signals (0.57 V at 15 mV pk drain) are visible; plan DMM readings of X_OUT − VMID (two channels or a 6½-digit meter) for small signals.

### F-18 ERC items and library checks

| ERC item | Opinion |
|----------|---------|
| `+5VP` not in the KiCad power library (7 `lib_symbol_mismatch`) | Agree, benign. The netlist shows `+5VP` connects U14.1, U9.8, C62, C63, C82, TP5 |
| U24/U25 VSS on `-9V` "ground_pin_not_ground" | Agree, benign. The TMUX6136 GND pin 6 is on `GND` and VSS is the supply pin (SCDS397B Table 4-1) |
| U2 REF "Output" connected to power output on `GND` (error) | Agree it is harmless. The cause is the library pin type: INA828 REF is an input. Change the symbol's pin type to passive and remove the extra PWR_FLAG afterwards, so a wrong future connection of REF shows up |
| U24/U25 S1B (bidirectional) on `GND` | Agree, benign. S1B is the switch pin used as zero |

Footprint checks for S-5: DAC80508 WQFN-16 3 × 3 mm EP 1.68 mm, pitch 0.5 mm matches the RTE package; TMUX1109 UQFN-16 1.8 × 2.6 mm pitch 0.4 mm matches RSV; footprints of OPA2196 (VSSOP-8), TMUX6136 (TSSOP-16), INA828 (SOIC-8), INA190 (thin SOT-23-8 DDF; the KiCad `SOT-23-8` footprint is slightly larger: compare pads against the manufacturer drawing). J4: part C72334 (Kangnex WJ500V, height 14.07 mm) against the Phoenix MKDS horizontal footprint: pitch is right but the wire entry direction and body outline are not verified (check the LCSC drawing). J7 DC3-2.54-26PAL is right-angle (LCSC) and the footprint is `IDC-Header_2x13_Horizontal`: consistent. SMA BWSMA-KE-Z001 against Amphenol 132134 footprint: drill and ground-pin positions not verified.

### F-19 Disagreements between documents

| # | Documents | Disagreement | Effect on this review |
|---|-----------|--------------|------------------------|
| 1 | `design-context.md` §2, §3, §4, §6 vs board documents | Single 0…5 V rail, gain 11, τ = 0.1 s, square excitation, 100 Hz…10 kHz, OPAx192, vs ±5 V, G = 10, τ = 0.5 s, sine, 518 Hz, OPA2196. The AFE requirements record the answers (Q-7…Q-10); `design-context.md` and `design-issues.md` (DI-02 range 2.0…3.0 V on a 5 V supply) still use the single-supply values | Review follows the AFE documents; `design-issues.md` was not changed |
| 2 | LIA-Readout [schematic_overview §4.9](../../../LIA-Readout/docs/schematic_overview.md) vs AFE `DC-3` | FE-B calls the TMUX6136 "dual SPDT, ±5 V", which breaks SCDS397B §5.4 (VDD − VSS ≥ 10 V). AFE-Eval supplies it from the filtered ±9 V; LIA-Readout has ±7 V rails but does not say the switch uses them | The AFE choice is correct (VDD − VSS = 15.2 V at ±8 V input); LIA-Readout needs the same statement |
| 3 | LIA-Readout §4.9 vs component_selection C.8 | "VMID divider" values are not given in LIA-Readout; AFE entered 10 k/10 k and 150 k/100 k as `ASSUMPTION` (S-1) | F-03 |
| 4 | LIA-Readout AN-6 vs AFE sheet DEMODULATOR | AN-6 specifies 100 Ω series on the reference outputs; AFE-Eval has none | F-05 |
| 5 | LIA-Readout AN-16 (600 Ω–1.2 kΩ) vs experiment notes (≈ 300 Ω) | Heater resistance unresolved; INA190 range depends on it | F-09 |
| 6 | LIA-Readout §4.4 R_D tolerance 25 ppm/K vs AFE AN-4a 10 ppm/K | Recorded decision E-8 | none |
| 7 | AFE-Eval S-3 | `SPI_SCLK`, `HSENSE_A/B` vs LIA-Readout `SPI_SCK`, `IHTR_A/B` | none, recorded |

## 6. Checks Passed (one line each)

| Checklist item | Result |
|----------------|--------|
| Ratings against the supply | TMUX6136: dual supply 5…16.5 V, VDD−VSS 10…33 V (SCDS397B §5.4) → 15.2…23.2 V over ±8…±12 V input; analog pins ±2 V on VSS…VDD; SEL VIH 2 V with 3.3 V logic. TMUX1109: VDD 1.08…5.5 V, signals 0…4.1 V, EN/A0/A1 up to 5.5 V. OPA2196: 4.5…36 V; U9 on 10 V total. INA828: ±5 V, CM range (V−)+2…(V+)−2 = −3…+3 V (Fig. 50/57 not readable, G = 10 not plotted), drain CM is 0.05…0.25 V. DAC80508 VDD 2.7…5.5 V, VIO 1.7…5.5 V. INA190: VS 1.7…5.5 V, inputs to 42 V with VS off |
| Pinouts against datasheets | INA828 SOIC-8 (RG 1/8, −IN 2, +IN 3, V− 4, REF 5, OUT 6, V+ 7), INA190 DDF (VS 1, ENABLE 2, REF 3, GND 4, OUT 5, NC 6, IN+ 7, IN− 8), TMUX1109 RSV (A0 15, EN 16, VSS 1, S1A…S4A 2…5, DA 6, DB 7, S4B…S1B 8…11, VDD 12, GND 13, A1 14), TMUX6136 PW, DAC80508 RTE (REF 1, OUT0…3 2…5, GND 6, VDD 7, OUT4…7 8…11, CS 12, SCLK 13, SDI 14, SDO 15, VIO 16), OPA2196 DGK, LT3094 MSE (IN 1/2/13, EN/UV 3, PG 4, PGFB 5, ILIM 6, VIOC 7, SET 8, GND 9, OUTS 10, OUT 11/12) all match the netlist. ADP7118 and the GMOS socket pin map are only compared with LIA-Readout §1.3 (matches) |
| TMUX6136 truth table | SEL = 1 connects S1A (`BPF_OUT`), SEL = 0 connects S1B (`GND`): same as LIA-Readout (SEL = 0 → zero). Gain +1/−1 as the wiring R78/R79 = 10 kΩ gives |
| DC paths | Each in-amp input has a DC path through R_D to `VSUP` even with all switches off; the post-filter +IN has 60 kΩ to GND/VMID; the TMUX6136 D1 is always connected to `BPF_OUT` or `GND` |
| Headroom | INA_OUT: 1.98 V DC (200 mV mismatch × 9.9) + 0.5 V pk, swing limit ±4.85 V (SBOS792A §6.5 (V±)∓0.15 V). `BPF_OUT` 1.98 V pk at the 50 mV pk limit (AN-23a), swing 4.9 V. X_OUT stays in 0…5 V up to 2.5 / (1.5 × 2/π) = 2.6 V pk BPF amplitude |
| References and coherent errors | INA828 REF direct to GND (DI-03 asks < 5 Ω: met). Demodulator zero is GND, so `+5VA` ripple at the reference frequency does not demodulate. Heater supply `+5VP` is separate (DC-5). Switch charge injection is small: −0.4 pC at ±15 V and −0.7 pC at 12 V (SCDS397B), settles in about RON × C = 3 ns |
| Switch timing | tTRAN 66…117 ns (±15 V) and break-before-make 20…40 ns; 100 ns on a 1.93 ms period is 0.019° |
| Noise | F-17: 3.2 % of the sensor noise power |
| Stability of the gate stages | R58/R59 100 Ω outside the MFB loop, C0G 22 nF/47 nF: no cap-load problem |
| Decoupling | 100 nF at every supply pin pair (netlist: C2/C4, C88…C91, C97/C98, C102/C103, C71…C73, C76/C77, C80/C81, C63…), TMUX6136 1 µF each side per datasheet 0.1…10 µF |

## 7. Bring-Up and Test Plan (bench)

Run the tests in this order. Each is a bench measurement on the first board; none needs a simulation.

| ID | Test | Setup | Expected | Closes |
|----|------|-------|----------|--------|
| B-1 | Rails, no NUCLEO, current limit 100 mA | Lab supply ±9 V, no ribbon, no sensor | `+9V` 8.6 V, `-9V` −8.6 V, `+5VA`/`+5VP` 5.00 V ±1 %, `-5VA` −4.99 V after 0.55 s, input current ≈ 60…90 mA | F-06, F-13 |
| B-2 | Rail noise and LDO stability | Scope AC 20 MHz limit on `+5VA`, `+5VP`, `-5VA`; apply a 20 mA load step | No ringing above 5 mVpp; `-5VA` start-up 0.55 s | F-06 |
| B-3 | Cross-powering | NUCLEO on, board off, firmware toggling `REF_X/Y`; meter on `+9V` | `+9V` below 0.3 V with the series resistors; note the value without them if tested once | F-05 |
| B-4 | `DSENSE` clamp | EN = 0, drain DAC 3 V, NUCLEO not connected | `DSENSE_A/B` ≤ 3.6 V with the clamp (4.9 V without) | F-02 |
| B-5 | DAC reference alarm | Read STATUS.REF-ALM with `+5VA` at its actual value, then lower it to 4.95 V with a series resistor test only on a spare board, or by reading ADP7118 spread over 5 units | REF-ALM = 0 | F-01 |
| B-6 | CMRR with a deliberate mismatch | Both `DRN` inputs of U2 driven from one 518 Hz source through 330 kΩ, one side with 10 pF added | Measure CM-to-diff conversion; expected 39 dB with 10 pF, 45 dB with 5 pF; no mismatch ≈ 60 dB or better | F-04 |
| B-7 | Drain leakage | Open pin, `DRN` DC read via `DSENSE`, heat the socket to 50 °C, then clean and repeat | Drift ≤ 100 µV; if larger, guard and wash | F-04 |
| B-8 | Loop step response | 0.5 V step on the heater DAC and on the coarse DAC; scope on `HTR_A` and `VSUP_A` | Overshoot ≤ 10 %; if more, fit the DNP C_f | F-07 |
| B-9 | Transition-region sweep | Sweep coarse DAC 0.4…3.3 V in 10 mV steps, read `VSUP_A` | No step above 100 µV near 2.0…3.5 V | F-08 |
| B-10 | Ground loop | Scope on `X_OUT` with NUCLEO on the same USB port versus a separate supply | 50 Hz pick-up unchanged within 3 dB | F-12 |

## 8. Parts

No replacement part is needed. Suggested additions (owner approval needed; stock on 2026-10-29):

| Purpose | MPN | LCSC | Stock | Price | Package | Simulation model |
|---------|-----|------|-------|-------|---------|------------------|
| `DSENSE` clamp (first choice) | BAT54S (hongjiacheng) | C7420333 | 760 190 | USD 0.0129 | SOT-23 | generic Schottky model |
| `DSENSE` clamp (backup) | BAT54S (MDD) | C408389 | 777 021 | USD 0.0186 | SOT-23 | generic |
| Input TVS (optional) | SMAJ12A (BORN) | C152123 | 32 538 | USD 0.0608 | SMA | not needed |

## 9. Open Questions for the Owner

1. Is `+5VA` allowed to be 5.5 V, or is the coarse DAC range limited to ≤ 2.5 V (F-01)? Decide after test B-5.
2. Are R76/R77 to be 0.1 %, ≤ 10 ppm/K thin film, or should the post-filter reference be GND (F-03)?
3. Which heater resistance does the real sensor have (600 Ω–1.2 kΩ or 300 Ω)? It sets the INA190 range (F-09).
4. Are the drain-node loops needed for AC probing, or are `DSENSE` and `INA_OUT` enough (F-04)?
5. Is a separate `DGND`/`AGND` net with a net tie wanted (F-12)?

## 10. Not Verified

- ADP7118 minimum output capacitance, VIN absolute maximum, accuracy over temperature and UVLO (datasheet not retrieved).
- STM32F303/NUCLEO-F303RE analog-pin tolerance and injection current limits.
- INA828 common-mode range at G = 10 with ±5 V (only G = 1 and G = 100 curves exist; figures not readable as text) and its output swing at ±5 V (the table value is for ±15 V).
- DAC80508 REF-ALM threshold voltage (not tabulated).
- OPA2196 offset and CMRR inside the transition region (typical curves not read).
- Node capacitance of 55 pF and the capacitances in F-07 are assumptions; the GMOS electrical model is not available (`design-context.md` §1 TBD).
- Footprint pad dimensions against manufacturer drawings (S-5).
- `design-issues.md` and `simulations/design-review/` were not updated: this is a board review and the register is organised by simulation batch. F-01, F-03, F-05 and F-16 should become DI entries when the owner accepts them.
