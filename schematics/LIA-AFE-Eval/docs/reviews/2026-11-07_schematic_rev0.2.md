# LIA-AFE-Eval — Schematic Review and Simulation Comparison, 2026-11-07

Date: 2026-11-07. Reviewer: Claude (main session), at the owner's request. Netlist: `kicad-cli sch export netlist` of commit 3429288 ("slight placenment fixes"). Status: review of the schematic as it stands after the changes of 2026-10-31 to 2026-11-07, compared with the PSpice circuits in `simulations/ti-pspice/circuits/`.

## 1. Scope and Method

| Item | Content |
|------|---------|
| Reviewed | All sheets of the exported netlist, dumped part by part with their pin nets. `netcheck.py`: 2 findings (SINGLE-NODE `/Sensor/HTR_A`, `/Sensor/HTR_B`). ERC not run |
| Owner assumption | All DC rails come from the bench connectors. The 10 Ω resistors in series with the TMUX6136 supplies were removed, because the switch is now supplied from its own ±15 V input |
| Compared with | `circuits/lia_v3_fast.cir` (demodulator), `circuits/chain_ss.cir` (full chain), `circuits/frontend_mc.cir`, `circuits/diffamp_*.cir` |
| Calculations | [`simulations/ti-pspice/docs/sim-results/scripts/afe_eval_expected.py`](../../../../simulations/ti-pspice/docs/sim-results/scripts/afe_eval_expected.py) (ideal transfer functions and Monte Carlo) |
| Simulations | Smoke runs `smoke_afe_op`, `smoke_afe_tran`, `smoke_afe_demod` of the new circuits `afe_eval.cir` and `afe_demod.cir` (index Batch 4). Not graded |
| Datasheet facts | Taken from the [2026-10-29 review](2026-10-29_schematic_rev0.1.md), which read TMUX6136, TMUX1109, DAC80508, INA828, INA190 and OPA2196 in full. B5819W was not read |

Severity: **blocker**, **major**, **minor**, **note**, as in the 2026-10-29 review.

## 2. Board Netlist Against the Simulated Circuits

The simulations so far model the single-rail candidate FE-C with parts of FE-B. The board is FE-B (E-1) with its own post-filter (E-9). Only the demodulator core is the same topology.

| Block | Simulated (`chain_ss.cir`, `lia_v3_fast.cir`) | Board netlist (2026-11-07) | Consequence |
|-------|-----------------------------------------------|----------------------------|-------------|
| Supply | One ideal 0–5 V rail, ideal 2.5 V reference | Bench ±15 V (J4) and ±5 V (J5) through B5819W, +5VA, −5VA, +5VP through 1 Ω each. No LDOs. TMUX6136 on ±15 V directly | Rail values, diode drop and power-up order never simulated |
| Signal reference | 2.5 V node (INA828 REF, filter returns, demodulator zero) | GND everywhere | DI-02, DI-03, DI-04, DI-15 do not apply to the board |
| Sensor and drains | Floating differential source, 100 kΩ bias to 2.5 V | DAC → U10 difference amplifier (1.1·DAC2 − 0.1·DAC6) → R60 1 kΩ / C74 10 µF → R_D 330 kΩ → TMUX1109 → pixel. INA828 VIN+ = DRN_B, VIN− = DRN_A | Source impedance, node capacitance, CMRR and bias noise never simulated |
| Excitation | None (signal injected at the in-amp) | NUCLEO DAC → MFB U1B (−1/120, f₀ 4.95 kHz, Q 0.728), DC from DAC ch. 4 via R8/C8 → R59 100 Ω → one `GATE` net | Gate amplitude and phase never simulated |
| In-amp | INA828, RG = 5 kΩ, G = 11 | INA828, RG = 5.62 kΩ, G = 9.897 | Scale factor differs by 10 % |
| Band-pass | Unity-gain SK: HPF 33 n/33 n, 4.64 k/18.7 k; LPF 4.64 k/4.64 k, 130 n/33 n. Peak 11.08 V/V | K = 2 equal-part SK: 9.31 kΩ, 33 nF in both sections, R70–R73 10 kΩ. Peak 39.59 V/V at 518.0 Hz, Q = 1 per section | Different gain, sensitivity and Monte Carlo spread |
| Op amps | OPAx192 (GBW 10 MHz) | OPA2196 (GBW 2.5 MHz), TI model `OPAx196` available in `nom_pspti.lib` | Smoke run: −1.53° and −0.17 % more at 518 Hz than the ideal filter |
| Switch | SPDT_PREC on the 5 V rail, SEL 0/5 V | Same model, TMUX6136 on ±15 V, SEL 0/3.3 V from NUCLEO. SEL = 1 → S1A = BPF_OUT, SEL = 0 → S1B = GND | DI-01 resolved by the ±15 V input |
| Demodulator | U2/U4: +IN from the switch, 10 kΩ / 10 kΩ, gain ±1 | U26A/U27A: same, R78/R79 and R83/R84 10 kΩ 0.1 % | Same topology. P-11 to P-13 mechanisms carry over |
| Post-filter | RC 10 kΩ / 10 µF (τ 0.1 s), or 1 µF | Unity-gain SK U26B/U27B, 200 kΩ, 1.5 µF, two poles at 0.53 Hz (τ 0.3 s each), R88 0 Ω / R89 10 kΩ, R80 100 Ω to SMA | 2f₀ ripple −132 dB instead of −50 dB. Settling to 5e-4 takes 3 s |
| Heaters, DAC, mux | Not simulated | U9A/B on +5VP with 15 Ω shunts and INA190, DAC80508 on +5VA, TMUX1109 on +5VA | Never simulated |

## 3. Summary of Findings

| ID | Severity | Nets / parts | One line |
|----|----------|--------------|----------|
| A-01 | blocker | J4, J5, `VIN_P`, `VIN_N`, D4, D5, D9, D10 | J4 and J5 are on the same two nets, so ±15 V on either connector reaches +5VIN, +5VA and +5VP |
| A-02 | blocker | U9A/B, IC1, IC3, U20.9, U21.9, `HTR_A/B`, `HSENSE_A/B` | The heater drivers are not connected to the TMUX1109 bank B, and the A/B names are crossed |
| A-03 | major | D5, D10, R18, R19, `+5VA`, U8 | The series Schottky drop puts +5VA near 4.6 V: DAC80508 reference alarm and less OPA2196 input range |
| A-04 | major | documents | The power, demodulator-sheet and post-filter documents no longer describe the schematic |
| A-05 | major | U24, J4, J5 | Two independent bench supplies: with ±5 V on and ±15 V off, signals drive the unpowered TMUX6136 |
| A-06 | minor | U3, U26, U27 | Front-end phase with OPA2196 is 1.5° behind the ideal filter and follows the op-amp bandwidth |
| A-07 | minor | R25, R31, J3, U20, U21 | System CMRR median 49.8 dB against the 48 dB target with 50 pF ± 10 % node capacitance |
| A-08 | minor | C9–C12 | With 5 % C0G the band-pass gain spreads by 7.1 % (std) |
| A-09 | note | C13–C16 | Post-filter settles to 5e-4 only after 3 s; acrylic-film dielectric absorption not checked |
| A-10 | note | earlier findings | F-05, F-09, F-10, F-14 of the 2026-10-29 review are still open in this netlist |

## 4. Findings

### A-01 J4 and J5 share `VIN_P` and `VIN_N` (blocker)

- **Where:** Power sheet. Net `/Power/VIN_P` = J4.1, J5.1, D4.A, D5.A. Net `/Power/VIN_N` = J4.3, J5.3, D9.K, D10.K.
- **Evidence:** netquery `net J4.1` and `net J5.3`. Both connectors carry the labels `VIN_P` and `VIN_N`, so they are in parallel. D4 (to +15V) and D5 (to +5VIN) take their anode from the same net.
- **Consequence:** with ±15 V on J4 and ±5 V on J5 the two bench supplies are shorted together. The higher one wins, and +5VIN rises to about 14.6 V. The DAC80508 and TMUX1109 are 5.5 V parts (operating range per the 2026-10-29 review; absolute maximum not read) and fail. The INA828 and OPA2196 survive (36 V parts). With only J4 or only J5 connected, all rails get the same voltage.
- **Fix:** separate nets, for example `VIN15_P`/`VIN15_N` on J4 with D4/D9 and `VIN5_P`/`VIN5_N` on J5 with D5/D10. Mark the connectors on the silkscreen. Add a check line to a new check file.
- **Simulation:** `afe_eval.cir` models the intended separate inputs, not the netlist.

### A-02 Heater outputs not connected, A/B names crossed (blocker)

- **Where:** Sensor sheet. `/Sensor/HTR_A` has only U20.9 (DB), `/Sensor/HTR_B` only U21.9 (netcheck SINGLE-NODE). The driver side is net `Net-(IC3-IN-)` = IC3.8, R20.1, R24.2, TP19 ("HTR_A") and `Net-(IC1-IN-)` = IC1.8, R26.1, R30.2, TP20 ("HTR_B").
- **Evidence:** U9A (+IN = DAC1) drives R24 / IC3, whose output reaches `HSENSE_B` through R69. U9B (+IN = DAC0) drives R30 / IC1, whose output reaches `HSENSE_A` through R68. TP19, on the U9A side, is named "HTR_A".
- **Consequence:** no heater current can flow. The Kelvin divider closes the loop at the shunt, so U9 does not saturate and the fault is silent until the heater is measured. If the label is later added to the TP19 net, side A heater is read on `HSENSE_B`.
- **Fix:** put the `HTR_A` label on the node that U20.9 must reach (the R24 / R20 / IC3.IN− node) and `HTR_B` on the R30 / R26 / IC1.IN− node, then make the DAC channel, INA190 and `HSENSE` names agree with the LIA-Readout assignment (`schematic_overview.md` §1.2). Which side is which is a decision for the owner. Check that TP19 and TP20 end on the right side.
- **Simulation:** P-33 assumes the connection is fixed.

### A-03 Schottky drop on the ±5 V rails (major)

- **Where:** D5, D10 (B5819W) in series with the ±5 V input, then R18, R19, R32 (1 Ω).
- **Evidence:** the smoke run gives +5VA = 4.820 V at 3.3 mA with a generic Schottky model (V_F = 0.18 V). Component selection §C.2 quotes about 0.4 V for B5819W at the load current. With a 5.0 V bench supply +5VA is therefore between about 4.55 V and 4.82 V (not verified with the datasheet curve).
- **Consequence:** (1) DAC80508: with the reference divider off, VREF must not exceed VDD/2 (SLASEL1D §7.3, F-01 of the 2026-10-29 review). At VDD = 4.6 V, VDD/2 = 2.3 V < 2.5 V, so the gain-2 channels trip the reference alarm and every output goes to 0 V. F-01 was a margin question at 5.0 V. Here it is expected to fail. (2) OPA2196 input transition region V+ − 3 V … V+ − 1.5 V starts at 1.6 V instead of 2.0 V. The demodulator inputs U26A/U27A +IN carry BPF_OUT, which reaches 1.98 V pk at the AN-23a drain level of 50 mV pk.
- **Fix:** either set the bench +5 V input so that +5VA measures 5.0–5.2 V at TP3 (about 5.4–5.5 V at J5, to be confirmed on the bench, and never above the 5.5 V rating of U8 and U20/U21 at +5VA), or replace the series diodes by a reverse shunt diode with a PTC fuse, so the rail equals the bench voltage. Record the chosen bench voltage in the requirements.
- **Simulation:** P-23 (rails, P23c sweep of the bench voltage), P-28 (transition region at 4.6 V and 5.0 V).

### A-04 Documents no longer describe the schematic (major)

| Document item | Says | Netlist |
|---------------|------|---------|
| requirements DC-2 | One ±9 V input on a 3-pin terminal block | Two 3-pin blocks, ±15 V and ±5 V (owner assumption) |
| requirements DC-3, DC-5; component_selection §C.2 | LDOs for ±5VA and +5VP, TMUX6136 through 10 Ω + 1 µF from ±9 V | No LDOs, rails through 1 Ω from the bench input, TMUX6136 on ±15 V with 1 µF |
| README sheet table, AN-10, E-7 | Two `DEMODULATOR` instances (Demod_X, Demod_Y), one TMUX6136 per sheet | One `/Demod/` sheet with X and Y, one TMUX6136 (U24) with both channels used |
| E-9 | R89 DNP | R89 = 10 kΩ, R88 = 0 Ω (gain still 1) |
| `simulations/design-context.md` §2, §4, §6 | Single 5 V rail, G = 11, OPAx192, RC 10 kΩ / 10 µF | ±5 V and ±15 V, G = 9.897, OPA2196, SK 200 kΩ / 1.5 µF |

Per `schematics/CLAUDE.md` the documents are authoritative until the owner updates them. These changes need decision records (next free number E-12) and updates to requirements and component selection. I did not change them.

### A-05 Two independent bench supplies (major)

- **Where:** U24 (TMUX6136) on ±15 V, its signal pins S1A/S2A on `BPF_OUT` from U3B on ±5VA, SEL pins on `REF_X/REF_Y` from the NUCLEO.
- **Consequence:** with ±5 V on and ±15 V off, `BPF_OUT` (up to ±2 V) and the 3.3 V references drive the switch ESD cells into the unpowered VDD/VSS. With the 1 µF + 10 µF + 100 nF rail capacitance the current is limited only by the op-amp output. The earlier 10 Ω series resistors limited it a little. The switching off order has the same issue. F-05 of the 2026-10-29 review (no series resistor on `REF_X/REF_Y`) is part of this.
- **Fix:** add 1 kΩ in series with `REF_X/REF_Y` at the SEL pins (F-05), state the power-up order (±15 V first, off last) in the bench procedure, and consider a BAT54S from `BPF_OUT` to the ±15 V rails or a series resistor of 100 Ω–1 kΩ at S1A/S2A (it adds to the switch on-resistance seen by the op-amp +IN, which draws no current, so the gain is unaffected).
- **Simulation:** P-31 (power-up orders, missing ±15 V, ESD stand-ins).

### A-06 Front-end phase with OPA2196 (minor)

The smoke run shows the vendor-model front end 1.53° behind and 0.17 % below the ideal filter at 518 Hz. The K = 2 Sallen-Key sections are sensitive to the op-amp gain-bandwidth. The offset is removed by the phase calibration. A change of the bandwidth with temperature moves the phase and reads as an X error if only X is used. P-24 measures it per stage.

### A-07 CMRR margin (minor)

With R_D 0.1 % and node capacitance 50 pF ± 10 % (SIM-12 assumptions) the numpy Monte Carlo gives a median CMRR of 49.8 dB, 5 % point 41.5 dB. This meets the 48 dB median by 1.8 dB. The capacitance mismatch dominates: with matched capacitance the median is 64.6 dB. Keep the TMUX1109, TP15/TP16 traces and socket wiring of both sides symmetric. P-29 checks it.

### A-08 Band-pass spread with 5 % capacitors (minor)

With C9–C12 at 5 % (E-5) the gain at 518 Hz spreads by 7.13 % std and the phase by 3.31° std. With 1 % parts: 1.43 % and 0.67°. Each board needs its own gain and phase calibration until the 1 % rework. P-25 checks it.

### A-09 Post-filter settling (note)

Two coincident poles of 0.3 s settle to 1 % in 2 s and to 5e-4 in 3 s. C13–C16 are 1.5 µF acrylic film, 20 %. Their dielectric absorption was not checked. For bench tests the assembly option of smaller capacitors (AN-12) stays useful. The simulations use 15 nF (τ = 3 ms) as the fast setting.

### A-10 Still open from 2026-10-29 (note)

F-05 (no series resistor on `REF_X/REF_Y`), F-09 (INA190 full scale 8.8 mA, a 300 Ω heater would clip), F-10 (no pull-up on `DAC_CS`), F-14 (100 Ω outputs into a 50 Ω scope input give 1/3 amplitude) apply unchanged. F-01 is now A-03. F-02, F-03 are closed by E-10 and E-9.

## 5. What Was Confirmed

| Item | Result |
|------|--------|
| Demodulator wiring | U24 SEL1 = `REF_X`, S1A = `BPF_OUT`, S1B = GND, D1 = U26A +IN. Gain +1 for SEL = 1, −1 for SEL = 0. Same for Y. Smoke run: 254.69 mV for 400 mV pk (ideal 254.65 mV) |
| Band-pass values | f₀ = 518.03 Hz, Q = 1 per section, −3 dB band 377.5–710.9 Hz, as LIA-Readout AN-21 |
| Excitation | Gate 5.003 mVpp for 0.3 V pk at EXC_DAC (AN-4: 5 mVpp). Gate DC 0.99460 V for DAC 1.0 V (hand value 0.99458 V). Lag 8.27° at 518 Hz |
| Drain bias | VSUP_A = 2.63252 V and DRN_A = 0.15745 V at DAC2 = 2.4 V and 7.5 µA, as 1.1·2.4 V − 7.5 mV − 2.475 V |
| Scale factor | X_OUT = 25.20 × v_drain pk × cos θ with the ideal front end (E-9 quotes 25.5 at G = 10) |

## 6. Simulations Added

The new index entries are P-23 to P-34 in [simulation-index.md](../../../../simulations/simulation-index.md) (Batch 4), with the circuits `circuits/afe_eval.cir`, `circuits/afe_demod.cir` and `circuits/gen_exc_stair.py`. Entries P-18 to P-22 are deprecated. The mapping to the board-level requirements SIM-8 … SIM-20 is in [simulation-plan.md §7.2a](../../../../simulations/simulation-plan.md).
