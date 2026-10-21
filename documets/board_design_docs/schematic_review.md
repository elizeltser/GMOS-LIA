# GMOS LIA Board — Schematic Review (Netlist 2026-10-20)

Review of `GMOS-LIA.net` (KiCad 10.0.7, exported 2026-10-20 22:04; power items re-checked against the 2026-10-21 export) against the design in [schematic_overview.md](schematic_overview.md) and the decisions in [README.md §9.1](README.md#91-decision-log). Use it as a checklist while editing in KiCad: tick an item when fixed, and delete this file (or archive it as `schematic_review_<date>.md`) once all items are closed and the docs match the schematic.

**Severity:** 🔴 board will not work / damage risk · 🟠 wrong value or deviates from design · 🟡 cleanup / missing data.

---

## How to Use This File Locally

1. Work sheet by sheet in the order of [§C](#c-work-order). Each item has an ID (e.g. `PWR-3`) so commits can reference it (`git commit -m "PWR-3: IBB ground to -7V"`).
2. After each sheet: run ERC, export the netlist (`File → Export → Netlist`, KiCad format) to the repo root, and run `tools/netcheck.py` ([§D](#d-net-check-script)). Every single-node net it lists must be either intentional (test point, documented spare) or fixed.
3. When a value is decided, write it **once** in [schematic_overview.md](schematic_overview.md) (implemented values) and put the same value in the KiCad symbol `Value` field. Requirement targets stay in [requirements.md](requirements.md).
4. When a decision changes, add a row to README §9.1 rather than editing old rows.
5. Before layout: all 🔴 and 🟠 items closed, every symbol has footprint + MPN + datasheet field, net-check script clean.

---

## A. Global Findings

| ID | Sev | Finding | Fix |
|----|-----|---------|-----|
| G-1 | 🔴 | **Hierarchical label mismatches.** Twenty-one single-node nets exist because labels on parent and child sheets have different names: `LIA_FE/active_readout` ≠ `GMOS_MUX/active_out`, `LIA_FE/blind_readout` ≠ `GMOS_MUX/blind_out`, `LIA_FE/sin`/`cos` ≠ `oscillator/sin`/`cos`, `oscillator/gate_dc_bias` not connected to any DAC, `oscillator/v_gate` ≠ `GMOS_MUX/gate_voltage`, `DAC/GMOS_Vadj0…3` not connected to any heater, `GMOS_MUX/*_heater_voltage`, `*_drain_voltage` unconnected, `GMOS_Imeas2/3` unconnected (IC4, IC5 are deleted anyway, DAC-5) | Adopt the net names of [§1.2](schematic_overview.md#12-net-naming) and use identical hierarchical labels on both sides |
| G-2 | 🟡 | 57 symbols without footprint or with a resistor footprint on a capacitor (e.g. C1, C2, C6–C15, C16, C43, C44 use `SparkFun-Resistor:R_0603`) | Assign `Capacitor_SMD:*` footprints; footprints for all ICs (IC1–IC7, U10), L1/L2, J2, Q1 |
| G-3 | 🟡 | Many values still placeholder (`C`, `L`, `1k` everywhere in filters) | Use the value tables in schematic_overview §3.4, §4.5, §4.8, §4.9 |
| G-4 | 🟡 | **Symbol fields copied from the library part they were derived from, not from the real part.** Each KiCad symbol carries `Datasheet` and `Description` fields that end up in the BOM. U10 has value `INA828` but its Datasheet link and Description are those of the INA128 (`ina128.pdf`, "DIP-8/SOIC-8"); every resistor, including R_D (R47–R50) and the filter resistors, links to Vishay's CRCW thick-film datasheet (1 %/5 %), while these must be 0.1 % thin film; D4/D5 have the unresolved value `${DEVICE}`. Someone ordering from the BOM would buy the wrong parts | For every symbol: set `Value`, `Datasheet` to the actual part's datasheet, and add an `MPN` field (e.g. `TNPW0603330KBEEA` for R_D, `INA828IDR` for U10). For generic passives the MPN can be added at BOM time, but precision parts (R_D, filter R/C, attenuator, R_G, shunts) need it now. `tools/netcheck.py --mpn` lists what is missing |
| G-5 | 🟠 | Op-amp type OPA2196 in schematic vs OPA2192 in old docs | Resolved by D-11 (OPA2196); docs updated |
| G-6 | 🟠 | Stray rail label `+3V3` (only R31, R33) is a separate net from `+3V3_D` | Merge into `+3V3_D` |

## B. Punch List per Sheet

### B.1 `/DC/USB_PD/` and `/Connectors/` (PWR-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| PWR-1 | 🔴 | J2, VBUS | Net `VBUS` connects only to J2 pins A9/B9 — nothing is powered | VBUS → STUSB4500 VDD and VBUS_VS_DISCH (per datasheet) and to the source of the input P-MOSFET |
| PWR-2 | 🔴 | Q1 | Generic SPICE symbol `NMOS` (VDMOS model), source unconnected, drain on STUSB4500 VDD (pin 24). An N-channel FET cannot be used here: as a high-side switch its gate would need to be driven above VBUS, while VBUS_EN_SNK can only pull low | **AO3407A** (P-ch, −30 V, ±20 V V_GS, SOT-23, LCSC C15155 ≈ USD 0.11; clones ≈ USD 0.04). Symbol `Device:Q_PMOS_GSD` (check the SOT-23 pin order G=1, S=2, D=3 against the AO3407A datasheet). Source = connector VBUS, drain = VIN; 100 kΩ gate–source; R53 = 22 kΩ gate → U21 VBUS_EN_SNK (pin 16) (ST example values). U21 VDD (24) and VBUS_VS_DISCH (18) move to connector-side VBUS |
| PWR-3 | 🔴 | U21 | GND pins 10 and 25 on isolated net `Net-(U21-GND-Pad10)` | Connect to GND |
| PWR-4 | 🔴 | U21 | CC1/CC2 (pins 2, 4) unconnected; J2 CC lines go only to D1 | J2 CC1/CC2 → U21 CC1/CC2; tie CC1DB→CC1, CC2DB→CC2 |
| PWR-5 | 🟠 | U21 | VREG_1V2 (21), VREG_2V7 (23) unconnected; RESET, ADDR0/1 floating; SCL/SDA unconnected | 1 µF on each VREG; RESET, ADDR0, ADDR1 → GND; I²C to MCU I²C1 with pull-ups; ALERT/POWER_OK2 → MCU GPIO (optional) |
| PWR-6 | 🟠 | U21 | VSYS on +3V3_D | Acceptable per datasheet (or GND); confirm, and keep NVM PDO setting "≥ 9 V only" so VBUS_EN_SNK never closes on 5 V |
| PWR-7 | 🔴 | U1/U18 | `Net-(U1-EN)` (VIN of both converters) has no source and no TVS | Connect to Q1 drain (rename `VIN`). **SMAJ18A** TVS (V_RWM 18 V, V_C 29.2 V, SMA, LCSC C908771 ≈ USD 0.03) on connector-side VBUS next to J2; optional DNP SMAJ18A footprint on VIN |

### B.2 `/DC/Regulators/` (REG-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| REG-1 | 🔴 | U18 | IBB: IC GND (pin 1) on system GND | IC GND → `-7V` (VEE). Inductor L2 SW→GND is already correct |
| REG-2 | 🟠 | R4, R5 | IBB feedback 1 kΩ / 1 kΩ | R4 (GND→FB) = 107 kΩ, R5 (FB→−7V) = 10.0 kΩ |
| REG-3 | 🟠 | U18 | No C_IN between VIN and −7V | Add 2 × 4.7 µF 50 V VIN↔−7V |
| REG-4 | 🟠 | R2, R3 | Buck feedback 5.1 kΩ / 820 Ω → 4.33 V | R2 = 107 kΩ, R3 = 10.0 kΩ → 7.02 V |
| REG-5 | 🟡 | L1, L2 | L1 = 6.2 µH, L2 = "L" | 8.2 µH both (6.2 µH acceptable for L1), I_sat ≥ 1.5 A |
| REG-6 | 🔴 | U4, U5, U20 + dividers | Adjustable ADP7118ACPZN with dividers; +5VA set to **3.29 V** by R12/R13 | Use the **fixed** versions, same LFCSP-6 footprint: U4, U5 → **ADP7118ACPZN5.0-R7** (LCSC C659349), U20 → **ADP7118ACPZN3.3-R7** (C659348). **Delete R10, R11 (U4), R12, R13 (U5), R51, R52 (U20)** and connect each SENSE/ADJ (pin 2) directly to its VOUT (pin 1), with the trace taken at the load side of C_OUT. EN (4) stays on VIN, SS (5) stays open (380 µs start-up; do not ground it). C_OUT ≥ 2.2 µF X7R |
| REG-7 | 🟠 | U4 | `+5VP` (5.03 V) is used by nothing | Keep as heater rail (D-10): heater op-amp V+ and heater current |
| REG-8 | ✅ | U4, U5, U20 | SS pins unconnected | OK: datasheet allows SS open (380 µs typical start-up). No change |
| REG-9 | 🟠 | U3 | LT3094 ILIM (6) and VIOC (7) unconnected, PGFB tied to IN | Follow LT3094 datasheet for unused ILIM/VIOC/PG (ILIM normally to GND or a resistor; verify) |
| REG-10 | 🟡 | R8 | R_SET 50 kΩ (doc 49.9 kΩ 0.1 %) | Either is fine (−5.00 V / −4.99 V); use 0.1 % for low drift |
| REG-11 | 🟠 | D4, D5 | Rail clamps added (D4 cathode +5VA, D5 anode −5VA) but value `${DEVICE}`, no footprint; π-filter placeholders missing | D4, D5 = **B5819W** (40 V, 1 A Schottky, SOD-123, LCSC C7420330 / C64885, JLC preferred, ≈ USD 0.02); footprint `Diode_SMD:D_SOD-123`. Check D5 orientation: anode −5VA, cathode GND. Add 0 Ω + 2× DNP cap π placeholders between switchers and LDOs |

### B.3 `/Analog/oscillator/` → rename `excitation` (EXC-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| EXC-1 | 🟠 | U6, U7A, D2, D3, R6, R7, R9, R14–R20, C16, C17 | Analog 3-op-amp oscillator (f₀ = 1/(2π·310 kΩ·1 nF) ≈ 513 Hz). Note: it is not the 2-op-amp SLYT164 circuit described in the old docs, and its diode limiter is **asymmetric** (R15/R16 = 1 kΩ/12.1 kΩ on the D2 side vs R18/R19 = 12.1 kΩ/1 kΩ on the D3 side: only the negative peak is limited, at ≈ −1.1 V) | Remove (D-3) |
| EXC-2 | 🟠 | U7A | Becomes the reconstruction LPF | SK Butterworth 5 kHz: 10.2 kΩ, 10.2 kΩ, 2.2 nF (to GND), 4.4 nF (feedback); input `EXC_DAC` from MCU sheet |
| EXC-3 | 🟠 | R21, R22, R23 | AC attenuation 1 kΩ/300 kΩ | R21 = 120 kΩ 0.1 % via 1 µF film from U7A output; R22 = 1.00 kΩ; R23 1 kΩ OK |
| EXC-4 | 🔴 | U7B | `gate_dc_bias` and `v_gate` not connected | `gate_dc_bias` ← DAC80508 ch4 (`GATE_DC`); `v_gate` → 100 Ω → `GATE` (J1 gate pins) |

### B.4 `/Analog/LIA_FE/` (LIA-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| LIA-1 | 🔴 | R24 | INA828 R_G = 1 kΩ → G = 51; ±200 mV drain mismatch → ±10 V (saturates) | 5.56 kΩ 0.1 % → G = 10 |
| LIA-2 | 🟠 | R25–R28, C19–C22 | HPF/LPF placeholders (1 kΩ, "C") | Values in schematic_overview §4.8 |
| LIA-3 | 🔴 | — | ×4 stage missing; LPF output drives the AD630s directly | Add on spare U12A (3.01 kΩ / 1.00 kΩ) |
| LIA-4 | 🔴 | U8, U9 | AD630: CHA+ (2) and CHB+ (18) floating; V_OUT (13) not connected to the feedback resistor (RF/RB); RB (14) grounded and RF (15) shorted to CHA−/CHB− | Re-draw from the AD630 datasheet gain ±1 lock-in configuration; simulate (SIM-7) |
| LIA-5 | 🔴 | U8/U9 pins 9/10 | SEL B on `LIA_FE/sin`/`cos` (unconnected), SEL A on GND | SEL B ← REF_X/REF_Y, SEL A ← REF_XN/REF_YN, 100 Ω series at MCU side |
| LIA-6 | 🟡 | U8/U9 pin 7 | `X_sync`/`Y_sync` pulled up to stray `+3V3`, go nowhere | Pull-up to +3V3_D, route to MCU input-capture pins |
| LIA-7 | 🟠 | U12B, U13B, R29–R34, C23–C26 | Post-filter is a unity-gain SK with 1 kΩ; no gain, no level shift; outputs not connected to the ADC | Replace by the inverting LPF of §4.9 (100 kΩ, 301 kΩ ∥ 1.66 µF film, V₊ = VMID/4); outputs → ADC sheet |
| LIA-8 | 🟡 | U13A | Unused op-amp: inputs must not float | Tie as follower to GND (reserved for the optional split-gate summing amp, D-13) |

### B.5 `/GMOS_MUX/` (MUX-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| MUX-1 | 🔴 | J1 pins 10, 22, 4, 18 | Pixels 2 (active) and 6 (blind), drain and heater, unconnected | Connect to the new muxes (MUX-2) |
| MUX-2 | 🟠 | IC1, IC6, IC7 (3× TMUX6136) | Dual SPDT reaches only 2 of 3 pixels per side; drain node, drain supply and heater use three separate chips | Replace all three with **2× TMUX1109** (dual 4:1): U_MA = active side (S1–S3 = pixels 1–3, S4 = CAL/off), U_MB = blind side (pixels 4–6). Section A switches the drain node, section B the heater force line. Independent A0/A1/EN per chip (D-12, schematic_overview §4.7) |
| MUX-3 | 🔴 | IC1 / IC6 grouping | Side named `blind` (IC1 S1B/S2B, `blind_sel`) is wired to drains 1 and 3, which are **active** pixels; side `active` to drains 4 and 5 (blind) | Active = pixels 1–3, blind = 4–6. Rename nets, connect active pixels to U_MA → INA828 +IN (`ACT_D`), blind to U_MB → −IN (`BLD_D`) |
| MUX-4 | 🟠 | R47–R50 | Four R_D on the pixel side of the mux; drain supply switched by IC6 | **Two** R_D on the board side of the mux (`SUP_A`→R_D→`ACT_D`, `SUP_B`→R_D→`BLD_D`), 330 kΩ 0.1 % thin film ≤ 25 ppm/°C, matched pair placed together. Drain supply is then not switched at all |
| MUX-5 | 🟡 | C36, C41, C42 | Decoupling caps, value "C" | 100 nF per mux VDD; TMUX1109 on single +5VA (VSS = GND) |
| MUX-6 | 🟠 | — | Calibration network missing | CAL_P on U_MA S4A, CAL_N on U_MB S4A; S4B open (heater off) |

### B.6 `/DAC/` (DAC-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| DAC-1 | 🟠 | U15 | One DAC80508, 4 drain/heater channels used, DAC4–7 dangling, gate DC not connected | Keep **one** DAC80508 with the allocation of schematic_overview §4.6.1 (D-13): heater A/B, drain supply A/B, gate DC, VMID, 2 spares to test points |
| DAC-2 | 🔴 | IC2, IC3 | Outputs of two INA190 shorted on net `GMOS_Imeas1` | One net per INA190 (`IHTR_A`, `IHTR_B`) |
| DAC-3 | 🟠 | U16 (R36, R37 / R41, R42) | Heater-driver feedback taken at the op-amp output (before the 15 Ω shunt): shunt drop outside the loop, contrary to AN-13 | Take feedback from the heater side of the shunt (`ACT_HTR`/`BLD_HTR`, before the mux) |
| DAC-4 | 🟠 | IC2, IC3 | INA190 VS on +5VA: output can exceed the MCU ADC range on a fault | VS = VDDA (INA190 CM range is independent of VS) |
| DAC-5 | 🟠 | U16, U17, IC4, IC5 | Four heater drivers and four INA190 | **Two** heater drivers (one dual, U16), two INA190 (IC2, IC3); delete IC4, IC5; U17 becomes the drain-sense dual (§4.6.4). Heater op-amp V+ = +5VP |
| DAC-6 | 🟡 | U15 | REF pin unconnected; SPI pins unconnected | REF decoupling per datasheet; SPI2 + CS to MCU |
| DAC-7 | 🟡 | R43–R46 | Four 15 Ω shunts | Two, 0.1 %; value pending heater resistance (README §9.2 item 2) |

### B.7 `/ADC/` (ADC-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| ADC-1 | 🟠 | U14 | All analog inputs, REF and SPI unconnected | AIN0 = X_OUT, AIN1 = VMID, AIN2 = Y_OUT, AIN3 = VMID, RC filters; internal ref; SPI2 + CS + DRDY |

### B.8 `/MCU/` (MCU-x)

| ID | Sev | Ref | Finding | Fix |
|----|-----|-----|---------|-----|
| MCU-1 | 🔴 | U2 | VDD (19, 32, 64), VDDA (13), VBAT (1), VCAP (30), VDDUSB (48), NRST (7), PH3-BOOT0 (60) unconnected | Per schematic_overview §5.2 |
| MCU-2 | 🟠 | — | No clock source | 16 MHz XO on PH0 (§5.3) |
| MCU-3 | 🟠 | L3, C46 | VDDA is now fed from +3V3_D through a ferrite (L3). That filters noise but makes VDDA (= the MCU DAC/ADC reference on LQFP64) only as accurate and stable as the ADP7118 output (percent-level accuracy over line, load and temperature; see its datasheet), far from a ≤ 10 ppm/°C reference, which sets the excitation amplitude (AN-7) and the drain-sense scale | Decide: (a) keep L3 and accept it, calibrating amplitude against the DAC80508 internal reference (e.g. measure a DAC80508 spare channel with ADC1 and correct in firmware, §4.6.1 ch7); or (b) precision 3.3 V reference from +5VA as in §3.3. (a) is cheaper and is enough if firmware calibration is implemented |
| MCU-4 | 🟠 | U19, P1 | CP2102N ground on isolated net, no ISO7721, no supply. New P1 is a USB-C **plug** symbol (`USB_C_Plug_USB2.0`, the cable side), all pins unconnected | Use a **receptacle** symbol/footprint for the board (`Connector:USB_C_Receptacle_USB2.0_16P`, with 5.1 kΩ Rd on CC1/CC2); P1 VBUS → CP2102N supply, D+/D− → CP2102N, P1 GND = isolated ground; add ISO7721 |
| MCU-5 | 🟡 | — | Missing SWD header, TMP117, SHT40, LEDs | Add |
| MCU-6 | 🟠 | — | Pin allocation | Start from schematic_overview §5.4, confirm in CubeMX, export the `.ioc` to the repo |

## C. Work Order

Order agreed on 2026-10-21. Steps marked "any order" can be done in parallel. Draw the new circuits (steps 1–4) directly with the net names of [§1.2](schematic_overview.md#12-net-naming); step 5 then only has to rename what is left.

1. **Excitation sheet (EXC).** Delete the oscillator (U6, D2, D3 and its network), rename the sheet to `excitation`, draw the reconstruction filter and the gate summing amp. Hierarchical inputs `EXC_DAC`, `GATE_DC`; output `GATE`.
2. **MUX sheet (MUX).** Delete IC1/IC6/IC7, place 2× TMUX1109 (symbol `kicad/TMUX1109.kicad_sym`), two matched R_D on the board side, calibration network, pixels 2 and 6, fix the active/blind grouping (MUX-3). Outputs `ACT_D`, `BLD_D`; inputs `ACT_HTR`, `BLD_HTR`, `SUP_A`, `SUP_B`, `CAL_DAC`, `MUXA_*`, `MUXB_*`.
3. **Power (PWR, REG).** VBUS path and AO3407A, STUSB4500 pins, SMAJ18A, IBB ground and both converter dividers, fixed-voltage ADP7118 (delete the LDO dividers), B5819W values on D4/D5, VDDA decision (MCU-3).
4. **LIA_FE (LIA).** INA gain, filter values, ×4 stage, AD630 wiring from the datasheet, new post-filters. Inputs `ACT_D`, `BLD_D`, `REF_X/XN`, `REF_Y/YN`; outputs `X_OUT`, `Y_OUT`.
5. **Net naming (G-1).** Rename the remaining labels per §1.2 on all sheets in one pass; rerun `tools/netcheck.py`; the single-node list should shrink to signals not drawn yet.
6. **Rest, any order:**
   - **MCU sheet (MCU-1…6).** Power pins, XO, SWD, then the CubeMX project to freeze the pin map (PA4/PA5 and the TIM1 pins are fixed by silicon).
   - **DAC sheet (DAC).** One DAC80508 (allocation §4.6.1), two heater drivers with Kelvin feedback, two INA190 on VDDA, delete IC4/IC5, outputs `SUP_A`/`SUP_B`, `ACT_HTR`/`BLD_HTR`, `GATE_DC`, `VMID`.
   - **ADC sheet (ADC-1).**
   - **Footprints, MPNs, datasheet fields (G-2…G-4)**, then ERC = 0 errors and `tools/netcheck.py --mpn` clean.
   - **Docs sync.** Update the "Schematic now" columns in schematic_overview, close items here, update README §1.1 status.

## D. Net-Check Script

`tools/netcheck.py` (committed next to the docs). Run it after each netlist export:

```bash
python3 tools/netcheck.py GMOS-LIA.net                 # dangling nets, footprints, placeholder values
python3 tools/netcheck.py GMOS-LIA.net --mpn           # also require an MPN field (before layout)
python3 tools/netcheck.py GMOS-LIA.net --ignore TP1 /DAC/DAC7   # skip intentional spares / test points
```

It reports single-node nets (excluding KiCad's explicit `unconnected-` nets), symbols without a footprint, capacitors on resistor footprints, placeholder values (`C`, `R`, `L`, `?`) and, with `--mpn`, symbols without an MPN field. Exit code is 1 when anything is found, so it can run as a pre-commit hook or in CI.

Baseline: 2026-10-20 netlist SINGLE-NODE 21, NO-FOOTPRINT 41, CAP-ON-R-FP 15, NO-VALUE 37; 2026-10-21 netlist 23 / 45 / 17 / 40 (new parts D4, D5, L3, P1, C45, C46 not finished yet).

## E. Keeping Docs and Schematic Consistent

- A design value appears in the docs only in [schematic_overview.md](schematic_overview.md) and must equal the KiCad `Value` field. If you change one, change the other in the same commit.
- Theory and derivations never contain part designators except as examples; if a derivation needs a value, it links to the overview.
- When this review is closed, remove the "Schematic now" columns from schematic_overview §4.8 and the "schematic has …" remarks in §3.4.
