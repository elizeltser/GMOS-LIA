# GMOS LIA Board — Schematic Task List (netlist 2026-10-24 17:20)

Step-by-step plan for finishing the KiCad schematic, written to be executed with Claude Code in the local repo. It replaces the 2026-10-22 list. Designators are those of the **2026-10-24 17:20** export; if you re-annotate, update this file and `tools/checks/` first.

Design references: [schematic_overview.md](schematic_overview.md) (circuits and values), [requirements.md](requirements.md) (targets), [simulation-plan.md](../../../simulations/simulation-plan.md) (verification, decision matrix), [firmware.md](firmware.md) (pin/trigger needs), [README.md §9](README.md#9-decisions--open-items) (decision log).

---

## 0. Instructions for Claude Code

Read this section before every session.

**Repo layout:** KiCad project in `schematics/LIA-board/` (`GMOS-LIA.kicad_pro`, `*.kicad_sch`); these docs in `schematics/LIA-board/docs/`; tools in `schematics/LIA-board/tools/` (`netcheck.py`, `netquery.py`, `checks/Txx*.txt`); simulations in `simulations/`. Commands below run from `schematics/LIA-board/`.

**Loop for each task (one task per session or commit):**

1. Read the task. If it depends on a decision in §1 that is still open, stop and ask the user.
2. Do the `[CC]` steps yourself by editing the `.kicad_sch` text. Allowed `[CC]` edits: a symbol instance's `Value`, `Footprint`, `Datasheet`, `Description`, `Reference`, or adding an `MPN` property, copying the exact property format used elsewhere in the same file. KiCad must be closed (or the sheet reloaded) while you edit. Never move, add or delete wires, labels or symbols in the file.
3. Print the `[GUI]` steps for the user as a numbered list, then wait until the user says they are done and saved.
4. Export and check:
   ```bash
   kicad-cli sch export netlist --format kicadsexpr -o GMOS-LIA.net GMOS-LIA.kicad_sch
   python3 tools/netquery.py GMOS-LIA.net check tools/checks/Txx.txt
   python3 tools/netcheck.py GMOS-LIA.net
   kicad-cli sch erc -o erc.rpt GMOS-LIA.kicad_sch
   ```
5. If a check fails, show the failing lines and `netquery.py GMOS-LIA.net net <PIN>` output, propose the fix, go back to 3.
6. When all checks pass: tick the box in §3, add a line to the log in §5, commit (`git commit -m "Txx: <title>"`).

**Rules:** never change a value this file does not specify; enter values exactly as written (check files compare strings); when a task adds a symbol, use the next free designator and record it in the task.

---

## 1. Decisions

| ID | Question | Status | Outcome / options |
|----|----------|--------|-------------------|
| D-A | Lock-in references | **Closed** 2026-10-22 | MCU timer square waves (TIM8 CH1/CH2, PC6/PC7, `VERIFY-CUBEMX`) |
| D-B | Split gate | **Closed** | Keep: `GATE_A` (1–3), `GATE_B` (4–6), same sine |
| D-D | VDDA source | Open | Ferrite L3 from +3V3_D (as drawn) + firmware amplitude calibration / precision 3.3 V reference |
| D-F | Drain bias | **Closed** 2026-10-24 | U10 coarse/fine difference amplifier, k = 0.1, R_D on the board side (R25/R31) |
| D-18 | Front-end architecture | **Open — gates T03, T04** | FE-A (AD630, ±5 V, as drawn) / FE-B (switch demodulator, ±5 V) / FE-C (switch demodulator, single 5 V). Decide with the procedure in [simulation-plan.md §7.4](../../../simulations/simulation-plan.md#74-decision-matrix-for-d-18-fill-in-from-73-and-research) (Claude Code prompt: [prompts/frontend_decision.md](prompts/frontend_decision.md)) |
| D-19 | Readout muxes IC5/IC6 | **Closed** 2026-10-24 (user) | Removed; in-amp taps the R_D/switch node |
| D-20 | MCU pins and triggers | **Closed** 2026-10-28 | PA1 is SPI1_SCK; TIM8 on PC6/PC7 (AF3); TIM2 ← TIM8 via ITR5 ([firmware.md §F.2.1](firmware.md#f21-pin-and-trigger-verification-d-20-closed), [decisions/D-20_pins.md](decisions/D-20_pins.md)). CubeMX settings: [firmware.md §F.2.4](firmware.md#f24-cubemx-checklist) |
| D-21 | UART cable power | Open | FTDI TTL-232R-3V3 supplies 5 V on VCC: confirm its RXD tolerates 5 V logic, or add a 3.3 V LDO on the isolated side, or specify the TTL-232R-5V |

---

## 2. Findings Summary (2026-10-24 17:20 netlist)

`netcheck.py`: SINGLE-NODE 9, NO-FOOTPRINT 50, CAP-ON-R-FP 16, NO-VALUE 42.

| Sev | Sheet | Finding | Task |
|-----|-------|---------|------|
| 🔴 | USB_PD | R42 (Q1 gate pull-up) goes to Q1 **drain** (V_USB_PD); with Q1 off the drain is ≈ 0 V, so it pulls the gate low and turns Q1 on regardless of the STUSB4500. Must go to **VBUS_PD** (source) | T03 |
| 🔴 | Regulators | U14/U16/U17 still adjustable ADP7118ACPZN with SENSE tied to VOUT → 1.2 V outputs | T03 |
| 🟠 | Regulators | Buck/IBB dividers 5.1 k/820 and 1 k/1 k; L2, many C values placeholders; Q1, D1, D2 without footprint | T03 |
| 🔴 | MCU/isolator | ISO6721 (U11) MCU side swapped: PA2 (TX, output) on OUTB pin 6, PA3 (RX) on INA pin 7. Correct: PA2 → pin 7 (INA), PA3 ← pin 6 (OUTB) | T08 |
| 🔴 | Connectors | J6 pin 5 on board GND (defeats isolation); J6 not in FTDI pin order | T08 |
| 🔴 | DAC | IC2/IC4 (INA190) across R_D (R25/R31) and on the drain node: saturate at 10 µA and load the most sensitive node | T06 |
| 🟠 | DAC | R21/R27 and R23/R29 = 50 k/50 k (k = 1, no resolution gain); no output RC filter; no drain-sense buffer (PC2/PC3 wired to IC2/IC4) | T06 |
| 🟠 | GMOS_soc | R54/R55 (R_CAL) 100 kΩ → node ≈ 0.7 V; R56 dummy heater 100 kΩ and only on U21 | T02 |
| 🔴 | Excitation | `mcu_sin_ref` (R2, R6) not connected to PA4; values are placeholders | T01 |
| 🔴 | LIA_FE | Architecture pending D-18; as drawn: R10 = 1 kΩ (G = 51), filter placeholders, unity SK post-filters, AD630 SEL B on unconnected `X_chop/Y_chop`, `Vmid` divider 1 k/1 k | T04 |
| 🟠 | ADC | CS, DRDY, CLK, inputs unconnected | T07 |
| 🔴 | MCU | VBAT, VCAP, VDDUSB, BOOT0, PA4, PC6/PC7, CS lines, mux GPIO, PH0 unconnected; no XO, no decoupling | T08 |
| 🟡 | All | Footprints, MPN and datasheet fields | T09 |

Fixed since 2026-10-22 ✓: U1B inputs; both gate stages on one sine net; heater Kelvin feedback (R20/R26); R22/R28 to GND; USB D+/D− (now replaced by isolated UART); R_D 330k on the board side; IC5/IC6 removed; mux_en pull-down R38; D7 back-feed diode; D8 TVS; Q1 real P-FET with correct S/D; SWD 33 Ω + NRST on J5; USART2 on PA2/PA3; I²C pull-ups 4.7 kΩ.

---

## 3. Tasks

Order: **T00 first** (decision), then T01 → T02 → T03 → T04 → T05, then T06–T10 in any order.

- [ ] T00 Decide D-18 (front-end architecture); D-20 (MCU pins) closed 2026-10-28
- [ ] T01 Excitation sheet
- [ ] T02 GMOS_soc (selection, calibration loads)
- [ ] T03 Power (USB_PD + Regulators), per D-18
- [ ] T04 LIA front end, per D-18
- [ ] T05 Net naming pass
- [ ] T06 DAC sheet (drain bias, drain sense, heaters)
- [ ] T07 ADC sheet
- [ ] T08 MCU sheet and isolated UART
- [ ] T09 Footprints, MPNs, datasheet fields
- [ ] T10 Docs sync

### T00 Decide D-18 and D-20

Run the prompt in [prompts/frontend_decision.md](prompts/frontend_decision.md). Output: [decisions/D-18_frontend.md](decisions/D-18_frontend.md) with the filled decision matrix and a recommendation; the user decides and records it in README §9.1. D-20 is closed ([firmware.md §F.2.1](firmware.md#f21-pin-and-trigger-verification-d-20-closed)); the CubeMX settings to check before code generation are in [firmware.md §F.2.4](firmware.md#f24-cubemx-checklist).

### T01 Excitation Sheet (`/Analog/Excitation/`)

**[GUI]**
1. Rename `mcu_sin_ref` → `EXC_DAC` and connect it (hierarchical label) to PA4 on the MCU sheet.
2. Rename `Exct1` → `GATE_A`, `Exct0` → `GATE_B`; `GMOS_Vadj4` → `GATE_DC_A`, `GMOS_Vadj5` → `GATE_DC_B` (on both sheets).
3. Recommended: 100 Ω between each U1 output and its gate net (feedback stays on the op-amp side).
4. Test points on `EXC_DAC`, `GATE_A`, `GATE_B` (AN-34).

**[CC] values:** R2, R6 `120k` (0.1 %); R1, R5, R3, R7 `1k` (0.1 %); C3, C7 `47n` (C0G 1 %); C1, C6 `22n` (C0G 1 %); R4, R8 `10k`; C5, C8 `1u`; C2, C4 `100n`. Check file `T01.txt`.

### T02 GMOS_soc (`/Analog/GMOS_soc/`)

**[GUI]**
1. Add a dummy heater on U20 pin 10 (S4B) to GND, like R56 on U21.
2. Optional tone injection (only if wanted): return R54 to GND through a new 100 Ω; add 10 kΩ from `CAL_DAC` (PA5) to that node; return R55 through 100 Ω to GND.
3. Rename `ch_sel_0/1` → `MUXA_A0/A1`, `ch_sel_2/3` → `MUXB_A0/A1`, `mux_en` → `MUX_EN`; connect them to MCU GPIO (T08).
4. 100 nF at each TMUX1109 VDD.

**[CC] values:** R54, R55 `18k` (0.1 %, MPN e.g. RT0603BRD0718KL); R56 + new dummy `1k` (0.1 %, 0603 ≥ 0.1 W) or `680`; U20/U21 `TMUX1109PW`, footprint TSSOP-16, MPN TMUX1109PWR. Check file `T02.txt`.

### T03 Power (depends on D-18)

**[GUI], all options**
1. Move R42 pin 1 from `V_USB_PD` to `VBUS_PD` (gate-to-source pull-up).
2. Footprints: Q1 SOT-23, D1/D2/D4/D7 SOD-123, D8 SMA, J4 terminal block.

**[GUI], FE-C only**
3. Delete U18, L2, R35, R36, C37, C39, C41, C42 (IBB), U19, R37, C40, C43 (LT3094), D2; delete the `-7V`/`-5VA` nets; connect every former −5VA pin per T04-C.
4. Add REF3325 (+5VA in, `VREF_2V5` out, 1 µF in, 1 µF out) and LM7705 (+5VA in, −0.23 V out to the in-amp V− only, capacitors per datasheet).

**[CC] values:** R32 `22k`; R33 `107k`, R34 `10k`; (FE-A/B) R35 `107k`, R36 `10k`, R37 `49.9k`; L1/L2 `8.2u` (SWPA4020S8R2MT); U14, U16 `ADP7118ACPZN5.0-R7`; U17 `ADP7118ACPZN3.3-R7`; C29, C38 `4.7u` 50 V; C27, C31, C41, C42 `22u` 25 V; C40 `10u`; C43 `4.7u`. Check file `T03.txt` (FE-C: lines tagged `[AB]` are removed).

### T04 LIA Front End (`/Analog/LIA_FE/`), per D-18

Common to all options:
1. Rename `readout` → `BPF_OUT`, `X_readout`/`Y_readout` → `X_OUT`/`Y_OUT`, `X_chop`/`Y_chop` → `REF_X`/`REF_Y` (→ PC6/PC7).
2. Post-filters U4A/U4B become inverting first-order LPFs: R14/R16 input, R15/R17 feedback, C13/C14 feedback (film), +IN from the mid reference ([schematic_overview §4.9](schematic_overview.md#49-front-end-architecture-options-decision-d-18)).
3. Test point on `BPF_OUT` and the mid reference (AN-34).

**FE-A (keep AD630):** R10 `5.62k`; HPF C10, C11 `33n`, R9 `4.64k`, R13 `18.7k`; LPF R11, R12 `4.64k`, C12 `33n`, C9 4 × `33n`; AD630 SEL B ← REF_X/REF_Y, SEL A ← `Vmid` (R52/R53 → `10k`/`10k` + 100 nF); post-filter R14/R16 `100k`, R15/R17 `301k`, C13/C14 `1.5u` + `150n` film, +IN divider `30.1k`/`10k` from VMID. Check `T04_FEA.txt`.

**FE-B (switch demodulator, ±5 V):** delete U5, U6, R18, R19, R52, R53; add TMUX6136 (dual SPDT, ±5 V) + OPA2196 + 4 × 10.0 kΩ 0.1 %; wiring per [schematic_overview §4.9](schematic_overview.md#49-front-end-architecture-options-decision-d-18) (zero input = GND); band-pass K = 2: R9, R13 → `9.31k` as the two equal R of the HPF (re-wire as equal-component SK), C10, C11 `33n`; LPF R11, R12 `9.31k`, C9, C12 `33n`; add gain resistors 10.0 kΩ/10.0 kΩ per section; post-filter R14/R16 `200k`, R15/R17 `301k`, +IN = VMID·(1/2.5) divider. In-amp unchanged (R10 `5.62k`). Check `T04_FEB.txt`.

**FE-C (single supply):** as FE-B, but: U2 → INA333 (V+ = +5VA, V− = LM7705 output, REF = `VREF_2V5`, R10 `11k`); U3, U4 and the demodulator op-amp → OPA2365 on +5VA/GND; switches 2× TMUX1219 (zero input = `VREF_2V5`); all band-pass returns, post-filter +IN, ADS1220 AIN1/AIN3 → `VREF_2V5`. Check `T04_FEC.txt`.

### T05 Net Naming Pass

Rename per [schematic_overview §1.2](schematic_overview.md#12-net-naming); `netcheck.py` SINGLE-NODE should then list only items of T06–T08.

### T06 DAC Sheet (`/DAC/`)

**[GUI]**
1. Delete IC2, IC4 (INA190 across R_D) and their decoupling.
2. Add the U10 output filter per side: 1 kΩ in series between U10A output (feedback node) and R25, 10 µF X7R from the junction to GND (same for U10B/R31).
3. Add a dual OPA2196 drain-sense buffer: +IN ← `DRN_A`/`DRN_B` (R25/R31 lower node = `GMOS_Vadj2/3`), ×8 (7.15 kΩ / 1.02 kΩ), 10 kΩ + 1 µF → PC2/PC3 (`DSENSE_A/B`).
4. INA190 IC3/IC1 outputs → 1 kΩ + 100 nF → PC0/PC1.
5. DAC80508 REF pin decoupling per datasheet; DAC_CS → MCU GPIO.

**[CC] values:** R21, R27 `10k` (0.1 %); R23, R29 `100k` (0.1 %); R25, R31 `330k` (MPN TC0325B3303T5F or RT0603BRD07330KL, one reel); R24, R30 `15` (0.1 %); R20, R22, R26, R28 `50k` (0.1 %); U8 `DAC80508ZRTER`. Check `T06.txt`.

### T07 ADC Sheet (`/ADC/`)

**[GUI]** AIN0 ← X_OUT (100 Ω + 10 nF), AIN1/AIN3 ← mid reference, AIN2 ← Y_OUT (100 Ω + 10 nF); CLK → DGND; DRDY → MCU EXTI pin; CS → MCU GPIO; AVDD/DVDD decoupling. Check `T07.txt`.

### T08 MCU Sheet and Isolated UART

**[GUI]**
1. U11 (ISO6721): PA2 → pin 7 (INA), PA3 ← pin 6 (OUTB); pins 1–4 on the cable side (VCC1 = `ISO_VCC`, GND1 = `ISO_GND`), pins 5/8 on GND/+3V3_D; 100 nF on each side.
2. J6: 6-pin header in FTDI order: 1 `ISO_GND`, 2 CTS (→ `ISO_GND` or NC), 3 `ISO_VCC`, 4 cable TXD → U11 pin 3 (INB), 5 cable RXD ← U11 pin 2 (OUTA), 6 RTS NC. **No board GND on J6.** Per D-21: 3.3 V LDO on `ISO_VCC` if needed.
3. MCU power pins and decoupling per [schematic_overview §5.1](schematic_overview.md#51-mcu-stm32u575rgt6-u12); XO on PH0; PA4 ← `EXC_DAC`; PA5 ← `CAL_DAC` (if used); PC6/PC7 → `REF_X/REF_Y` via 100 Ω; DAC_CS, ADC_CS, ADC_DRDY, MUX lines to free GPIO; SPI1 SCK on PA1 (D-20).
4. TMP117, SHT40 on I²C1.

Check `T08.txt`.

### T09 Footprints, MPNs, Datasheet Fields

**[CC]** For every symbol: datasheet link of the real part, description, footprint, `MPN`. Done when `netcheck.py GMOS-LIA.net --mpn` reports nothing and ERC = 0 errors.

### T10 Docs Sync

**[CC]** Make [schematic_overview.md](schematic_overview.md) values equal to the KiCad values; update README §9; archive this file as `schematic_review_<date>.md` when all tasks are ticked.

---

## 4. Tools

| Tool | Use |
|------|-----|
| `tools/netcheck.py NETLIST [--mpn]` | Dangling nets, missing footprints/values/MPNs |
| `tools/netquery.py NETLIST net PIN` / `part REF` / `check FILE` | Pin/net/part queries and assertions (`same`, `diff`, `nc`, `conn`, `name`, `between`, `value`, `valuein`, `fp`, `field`, `exists`, `absent`) |
| `kicad-cli sch export netlist`, `kicad-cli sch erc` | Netlist export, ERC |

## 5. Log

| Date | Task | Result | Commit |
|------|------|--------|--------|
| 2026-10-22 | — | Task list created (11:42 export) | |
| 2026-10-24 | review | 17:20 export reviewed; list rebuilt (this version) | |