# LIA-AFE-Eval — Layout Guidelines

Rules, critical routes and the placement plan for the first PCB layout of the evaluation board. Written 2026-11-14 from the netlist of that date, the partial placement in `LIA-AFE-Eval.kicad_pcb` (commit 5d52ec4) and a web search for analog layout guidance (sources in §L.5). §L.3 and §L.4 describe the layout as built after the owner's answers of the same day. Test-point numbers follow decision E-14. Coordinates are KiCad board coordinates in mm; the board outline is x 50…150, y 50…150.

## L.1 General Rules

| # | Rule | Why |
|---|------|-----|
| G-1 | Stackup: F.Cu = parts and sensitive signals; In1.Cu = solid GND, no traces, no splits; In2.Cu = +5VA and −5VA pours, other rails as wide traces; B.Cu = secondary routing (digital, DC bias lines, GATE) and the DAC | Every signal on F.Cu has an unbroken return directly below it |
| G-2 | One unsplit GND net and plane. Stitch GND pours on F.Cu/B.Cu to In1 at every GND pad, along every guard trace (about every 5 mm) and around the board edge. Remove floating copper | Split planes enlarge return loops ([1]); requirement R.1 asks for one join point, see §L.4 item 3 |
| G-3 | Each supply pin gets its 100 nF on the same layer, pin → capacitor → via to plane, ≤ 2 mm of trace. 10 µF bulk once per block | Trace inductance cancels the capacitor ([2], [3]) |
| G-4 | Feedback parts sit at the inverting pin. Summing-node traces ≤ 3 mm, no other net under or beside them | Parasitic capacitance on the summing node changes gain and phase ([2]) |
| G-5 | Analog_Sensitive nets (DRN, PIX_D, GATE, DAC_REF, INA190 IN+) stay on one layer, without vias where possible, with a GND guard on both sides and the DRC clearances of `LIA-AFE-Eval.kicad_dru` | Leakage and capacitive pick-up at 330 kΩ node impedance ([2]) |
| G-6 | The A and B sides are mirror images: drain path, R_D, calibration loads, heater path, trace lengths and via counts | Parasitics that are equal on both sides become common mode and the INA828 rejects them |
| G-7 | Signal flow runs left to right without backtracking: J7 / excitation → socket → muxes → in-amp → band-pass → demodulator → SMA | Short paths; inputs never run next to outputs of the same chain ([2]) |
| G-8 | Digital nets (SPI, MUX address, MUX_EN, REF_X, REF_Y) stay in their own corridor. They cross analog traces only at 90° and on another layer, never under the socket, muxes or front end | REF_X/REF_Y and the mux lines switch at f₀ or are static; coupling at f₀ looks like signal |
| G-9 | Heater current (+5VP → U9 → shunt → mux → socket → GND) forms a small loop at the top of the board, away from the in-amp and the band-pass | Heater current in the GND plane under the front end is a DC and 1/f error; heat changes the 0.1 % resistors |
| G-10 | No silkscreen, vias or other nets between the pads of high-value resistors (R25, R31, R90, R91, R14…R17). Clean the board after assembly | Surface leakage ([2]) |
| G-11 | Net-class widths: signal 0.2…0.25 mm, Heater 0.4 mm, Power 0.5 mm. Teardrops on power vias | As set in the project file |
| G-12 | Test loops at the edge of their block with a GND loop next to each group (LU-1). A probe on a sensitive node goes through its series resistor (R90, R91) | Probing must not load or disturb the node |
| G-13 | Routing order: draw the planes and keep-outs first, hand-route and lock the §L.2 routes, then route the rest (an autorouter only for digital and DC nets), then run DRC and review every Analog_Sensitive net by eye | Autorouters do not respect symmetry or return paths and mishandle zones ([4], [5]) |

## L.2 Critical Routes

| # | Route | How it must be routed |
|---|-------|-----------------------|
| CR-1 | `DRN_A`, `DRN_B`: U20.8 / U21.8 → R25 / R31 (R_D), R90 / R91 → U2.2 / U2.3 | A pair on F.Cu over In1 with one via each (the muxes are on B.Cu), GND pour between and beside the lanes, ≥ 0.5 mm to supply and digital nets. DRN_B is the left lane and DRN_A the right lane, so the pair reaches U2.3 and U2.2 without crossing. Never parallel to GATE, REF_X/Y, SPI, heater or the INA output |
| CR-2 | `PIX_D1…6`: J3 drain pins → U20.4…6 / U21.4…6 | On B.Cu inside the socket rows, one lane per pixel in pin order (no crossings, no vias), ≥ 0.55 mm between lanes, entering the drain pins from the inside of the row |
| CR-3 | `GATE`: U1.7 → C6 / R59 → `GATE` → J3 pins 5, 12, 19, 24, 32, 40 and TP11 | On F.Cu as a spine inside the socket rows, two planes (In1, In2) above the B.Cu drain lanes, and never on the same layer as a drain trace. Coherent coupling at f₀ cannot be rejected by the lock-in |
| CR-4 | In-amp U2: R10 across U2.1 / U2.8, REF U2.5 to GND, supply pins 7 / 4 | R10 tight and symmetric across the pins. U2.5 to In1 through its own via directly at the pin (REF impedance degrades CMRR). C88 / C89 at the supply pins |
| CR-5 | Op-amp feedback loops: U1B MFB (R7, C6, R5, C7, R6), U3 band-pass (R9, R11, R12, R13, C9…C12, R70…R73), U10 difference amplifiers, U26 / U27 (R78 / R79, R83 / R84, Sallen-Key R14…R17, C13…C16) | Per G-4. The 120 kΩ input R6 next to the EXC_DAC entry and the C7 node |
| CR-6 | `REF_X`, `REF_Y`: J7.4 / J7.6 → U24.1 / U24.9 (TP7, TP8 on the way) | 3.3 V square waves at f₀. Route along the board edge, away from `BPF_OUT`, DRN and GATE, with a GND trace or pour beside each one. Cross the analog chain only once, at 90° |
| CR-7 | Power entry and star: J5 → D5 / D10 → `+5VIN` / `-5VIN` → R18 (+5VA), R32 (+5VP), R19 (−5VA); J4 → D4 / D9 → ±15 V → U24.13 / U24.5 | R18 and R32 leave the `+5VIN` node at C56 / C57 as a star, so heater current never flows in the +5VA path. ±15 V as 0.5 mm traces along the bottom edge to U24 with C96 / C95 at the pins |

## L.3 Placement as Built

The middle row of the root sheet (Excitation → Sensor → Front_End) runs from left to right. The demodulator sits between the SMAs on the right edge, power and the control header on the left edge.

| Block | Location | Notes |
|-------|----------|-------|
| Power J4, J5, diodes, rails (kept) | Left edge, x 52…82, y 102…142 | C53 and C59 moved by about 1 mm to clear TP1, TP2, TP24 |
| Control header J7 (kept), control loops TP6…TP10, C65, C66, R38 | Left edge; loops at x 71…80, y 94…99 | Digital nets enter and stay on the left |
| Excitation U1 and DAC U8 (B.Cu) | x 72…92, y 72…92 | R5, R8, C8, R59, C2, C4 moved to U1's pins; TP11 (GATE) and TP13 (GND) next to R59 |
| Heaters U9, IC1, IC3 and parts, TP18…TP20 | Top band, x 59…93, y 45…56 (loops at y 65) | Side A left of U9, side B right. C82 above U9.8, C83 below U9.4, IC1 rotated 180° with R30 between U9.7 and IC1 |
| Muxes U20, U21 | **B.Cu**, y 62…70 above the socket, drain pins towards the socket | Mirroring puts PIX_D in the same order as the socket pins (CR-2). C71, C72, R56, R57 on B.Cu at the top-row pins; R54, R55 on F.Cu over the mux bodies |
| Drain bias U10 and parts, TP16, TP17 | x 113…131, y 50…61 | R25 and R31 (R_D) sit on the DRN lanes next to the muxes |
| Socket J3 (kept) | x 92…109, y 74…124 | GATE spine on F.Cu inside, PIX_D lanes on B.Cu inside |
| In-amp U2 | Rotated to 0°: inputs face the pair. R10 above, C88 / C89 at the supply pins, R90 / TP14 and R91 / TP15 on the lanes | |
| Band-pass U3 and parts (kept) | x 119…137, y 81…100 | |
| Demodulator U24 | Between J8 and J9 at (140.5, 103); J10 on the right edge | C95 / C96 at the ±15 V pins |
| X channel U26 and parts, TP26, TP27, TP30 | x 129…148, y 58…75 above J8 | |
| Y channel U27 and parts, TP28, TP29, TP31 | x 129…148, y 121…138 below J9 | Same arrangement as X, shifted by 63 mm |
| Front-end loops TP21…TP23, TP25 | Moved left to x 125 | Room for the Y channel |

## L.4 Owner Answers

1. One solid GND plane (G-2) is accepted.
2. TMUX1109 stays in TSSOP-16, sourced from DigiKey or Mouser (E-14).
3. TP6 removed, later test points renumbered (E-14).
4. Rotations accepted. The muxes were also moved to B.Cu, because on F.Cu the PIX_D order is reversed against the socket and the drain nets would need extra crossings (CR-2).
5. (2026-11-15) Board enlarged to 100 × 110 mm (E-16) and DAC outputs OUT0/OUT1 swapped (E-15). J7 rows swapped by the owner: signals on odd pins, GND on even pins.

In2 is kept as a GND plane: no In2 tracks inside the socket rows or under the mux drain pins, In2 used mainly for power rails. GND stitching vias on a 4 mm grid and every 3 mm along the edge tie the four GND layers together.

## L.5 Sources

1. Electronic Design, "How to ground mixed-signal circuits properly": https://www.electronicdesign.com/technologies/analog/article/21749867/how-to-ground-mixed-signal-circuits-properly
2. TI, OPA827 data sheet, layout guidelines: https://www.ti.com/document-viewer/OPA827/datasheet/layout
3. Analog Devices, StudentZone April 2017 (decoupling): https://www.analog.com/en/resources/analog-dialogue/studentzone/studentzone-april-2017.html
4. KiCad forum, autorouter examples: https://forum.kicad.info/t/for-those-that-are-considering-an-autorouter-a-couple-examples-to-consider/28271
5. Freerouting issue 152 (zones and planes): https://github.com/freerouting/freerouting/issues/152
