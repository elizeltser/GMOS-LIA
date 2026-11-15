# LIA-AFE-Eval — Layout Work in Progress (2026-11-15)

Scripts and state of the layout done with Claude. Rules and the as-built placement are in [../docs/layout_guidelines.md](../docs/layout_guidelines.md). Nothing here is committed yet.

## State

- `../LIA-AFE-Eval.kicad_pcb`: 100 × 110 mm, all nets routed (0 unconnected), four GND pours filled, 436 GND stitching vias.
- `owner_2026-11-15.kicad_pcb`: the owner's board as saved on 2026-11-15, before this session (it still had the J7 short, see below).
- `placed_unrouted.kicad_pcb`: the current placement without copper (start point for a re-route).
- `drc_2026-11-15.json`: DRC of the saved board: 0 unconnected, 80 clearance errors, all of them one of three net-class conflicts at fine-pitch pins (below). Silkscreen warnings not cleaned yet.

## Remaining DRC errors (all need an owner decision on the rules)

| Count | Where | Cause |
|-------|-------|-------|
| 59 | Pad to pad inside VSSOP-8 / TSOT-23-8 / TSSOP-16 / WQFN-16 footprints | Net-class clearance (Analog_Sensitive 0.3 mm, 0.5 mm to supply/digital) larger than the pin gap; present without any routing |
| 16 | Heater shunt nodes `Net-(IC1-IN+)`, `Net-(IC3-IN+)` at U9, IC1, IC3 | These nodes are in Analog_Sensitive (pattern `Net-(IC*-IN+)`); U9.7 sits 0.65 mm from U9.8 (+5VP) |
| 5 | U8 `DAC_REF`, `GATE_DC` | Analog_Sensitive at 0.5 mm pitch; `GATE_DC` is in the class only because of the pattern `/GATE*` |

## Changes made on 2026-11-15

1. Schematic CONNECTORS: the owner's J7 edit shorted `REF_X` and `REF_Y` to `EXC_DAC` (TP7/TP8 placed on the EXC_DAC wire with drop wires to their own lines). TP7/TP8 now sit on their own lines; two wires and two junctions removed. A script slip had removed the uuid line of two wires and two junctions; fresh uuids were added (no connectivity change). Netlist now differs from the earlier one only by the intended J7 odd/even swap.
2. Schematic DAC: OUT0/OUT1 labels swapped (decision E-15).
3. PCB: pad nets synced to the netlist, TP6 restored, board enlarged (E-16), heater and drain-bias blocks moved up, full re-route with In2 kept-out under the socket and mux drain pins, hand fixes at U8 (DAC0/DAC1 lanes, GATE_DC, +5VA), GND stitching.

## Open items

1. Owner decision on the three rule conflicts above.
2. Requirements IF-5 pinout table and check file T01 still list the old J7 order (signals on even pins).
3. Silkscreen overlaps (warnings), review in KiCad.
4. Schematic note: IC1 senses `HTR_B` but drives `HSENSE_A` (R68); IC3 senses `HTR_A` and drives `HSENSE_B` (R69).

## Scripts (KiCad python `C:/Program Files/KiCad/10.0/bin/python.exe`; plots with system python)

| Script | Use |
|--------|-----|
| `netfix.py BOARD PINNET.json` | Sync pad nets to the netlist (JSON pin map), restore TP6, strip copper |
| `place.py BOARD` | Placement dict, board outline, overlap report |
| `handroute.py BOARD` | Hand routes CR-1…CR-3 (drain pair, PIX_D1…6, GATE spine) |
| `route.py BOARD [nets] [--partial] [--complete]` | 0.1 mm grid router with keep-outs and region costs; `first.txt` = routing order |
| `passes.sh` | Repeated passes, keeps the best |
| `fix_u8.py`, `fixes2.py` | The hand fixes of 2026-11-15 |
| `zones.py`, `stitch.py` | GND pours and stitching vias |
| `geodump.py` + `render.py` / `render2.py` | Board pictures |
