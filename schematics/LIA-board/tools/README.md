# GMOS LIA Board — Netlist Tools

Two dependency-free Python 3 scripts (3.10+, standard library only) that read a KiCad netlist export and check the schematic from the command line. They are used in the task loop of [schematic_review.md §0](../schematic_review.md#0-instructions-for-claude-code).

| File | Purpose |
|------|---------|
| `netquery.py` | Ask questions about a netlist (which net is this pin on, what is this part) and assert expected connections from a check file |
| `netcheck.py` | Generic sanity scan of the whole netlist (dangling nets, missing footprints/values/MPNs) — no check file needed |
| `checks/Txx*.txt` | Check files: the expected state of the schematic after task Txx of schematic_review.md |

## 1. Export the Netlist

The tools read the KiCad S-expression netlist (`.net`), not the `.kicad_sch` files. Export after every saved change:

```bash
# from the KiCad project folder
kicad-cli sch export netlist --format kicadsexpr -o GMOS-LIA.net GMOS-LIA.kicad_sch
```

GUI alternative: Schematic Editor → File → Export → Netlist… → KiCad format.

## 2. netquery.py

```
python3 netquery.py NETLIST net   PIN            # net of PIN and all its members
python3 netquery.py NETLIST part  REF            # value, footprint, datasheet, sheet, custom fields
python3 netquery.py NETLIST check FILE [FILE..]  # run check files; exit 1 if anything fails
```

### 2.1 Pin references

| Form | Example | Meaning |
|------|---------|---------|
| `REF.NUMBER` | `U5.9` | Pin by number — always unambiguous |
| `REF:NAME` | `U12:PA4`, `U7:AIN0`, `U2:-IN` | Pin by its symbol pin name (KiCad *pinfunction*). A trailing `_<num>` is ignored and alternate names after `/` also match (`AIN0` matches `AIN0/REFP1`) |

If a name matches several pins (e.g. `GND` on a multi-GND IC) the tool stops with `ambiguous pin name …; use REF.NUMBER`. If a pin does not exist the check reports `pin not found`. Pin names come from the symbol, so a different symbol for the same function (e.g. INA333 vs INA828) can use different names — use pin numbers in that case.

### 2.2 Examples

```text
$ python3 netquery.py GMOS-LIA.net net U12:PA2
U12:PA2 -> /MCU/mcu_uart_tx
  U11.6 U12.16

$ python3 netquery.py GMOS-LIA.net part U7
value       ADS1220xPW
footprint   Package_SO:TSSOP-16_4.4x5mm_P0.65mm
datasheet   http://www.ti.com/lit/ds/symlink/ads1220.pdf
sheet       /ADC/
Description Low-power, quad-input, 24-bit analog to digital converter, ...

$ python3 netquery.py GMOS-LIA.net check checks/T07.txt
FAIL checks/T07.txt:2: conn U7:AIN0   [unconnected-(U7-AIN0{slash}REFP1-Pad11): only this pin]
...
2/8 checks passed
```

Only failures are printed, then the total. Exit code: `0` all passed, `1` at least one failure, `2` usage error.

### 2.3 Check-file syntax

One assertion per line; `#` starts a comment; blank lines are ignored.

| Assertion | Passes when | Example |
|-----------|-------------|---------|
| `same PIN PIN [PIN…]` | all pins are on one net | `same U12:PA2 U11:INA` |
| `diff PIN PIN` | the pins are on different nets | `diff U20.8 U21.8` |
| `nc PIN` | the pin is unconnected (no other member on its net) | `nc U12.60` |
| `conn PIN` | the pin has at least one other member on its net | `conn U12:VCAP` |
| `name PIN TEXT` | the pin's net name contains TEXT (case-insensitive) | `name U12:PA4 EXC_DAC` |
| `between REF A B` | the 2-pin part REF connects A and B, either orientation. A/B are pins or `@TEXT` = a net whose name contains TEXT | `between R42 Q1:S U13:VBUS_EN_SNK`, `between C5 U1.3 @GND` |
| `value REF TEXT` | the value field equals TEXT exactly | `value R25 330k` |
| `valuein REF TEXT` | the value field contains TEXT | `valuein U3 OPA2365` |
| `fp REF TEXT` | the footprint contains TEXT | `fp U20 TSSOP-16` |
| `field REF FIELD TEXT` | custom field FIELD (e.g. `MPN`) contains TEXT | `field D1 MPN B5819W` |
| `exists REF` | the component exists | `exists Q1` |
| `absent REF` | the component does not exist | `absent IC2` |

Notes:
- `value` is an exact string compare: enter values in KiCad exactly as written in the check file (`4.7u`, not `4u7` or `4.7µF`).
- `name` matches a substring of the full hierarchical net name (`/Analog/EXC_DAC` contains `EXC_DAC`), so give nets the names listed in [schematic_overview.md §1.2](../schematic_overview.md#12-net-naming).
- Option-dependent lines: `T03.txt` has lines prefixed `# [AB]` (front-end options FE-A/FE-B, ±5 V) and `# [C]` (FE-C, single supply). After decision D-18, delete the `# [..] ` prefix of the chosen option's lines. `T04` has one file per option (`T04_FEA.txt`, `T04_FEB.txt`, `T04_FEC.txt`); run only the chosen one.

### 2.4 Writing a new check

1. Find the pins: `python3 netquery.py GMOS-LIA.net net U5.9` (or `part U5` for value/footprint).
2. Write the intended end state, not the current one — a new check file is expected to fail until the task is done.
3. Dry-run it once on the current netlist and fix every `pin not found` / `ambiguous` / `component not found` message caused by a typo in the check itself; the remaining failures are the to-do list.

## 3. netcheck.py

```
python3 netcheck.py [NETLIST] [--mpn] [--ignore NET_OR_REF ...]
```

`NETLIST` defaults to `GMOS-LIA.net`. Reports, by category:

| Category | Meaning | Typical cause |
|----------|---------|---------------|
| `SINGLE-NODE` | a named net with only one pin (KiCad's own `unconnected-…` nets are excluded) | Hierarchical/global label spelled differently on two sheets; a label not attached to a wire |
| `NO-FOOTPRINT` | symbol without a footprint | Footprint not assigned yet |
| `CAP-ON-R-FP` | a capacitor on a resistor footprint | Copy-pasted resistor turned into a capacitor |
| `NO-VALUE` | placeholder value (`R`, `C`, `L`, `?`) | Value not entered |
| `NO-MPN` | no `MPN` field (only with `--mpn`) | BOM not finished — use before ordering |

Ends with a summary line, e.g. `Summary: SINGLE-NODE=9, NO-FOOTPRINT=50, CAP-ON-R-FP=16, NO-VALUE=42, NO-MPN=0`. Exit code `0` when nothing is reported, `1` otherwise. Use `--ignore` for intentional single-pin nets (test points, spare pins), e.g. `--ignore TP_SPARE /MCU/osc_in`.

## 4. Typical Session

```bash
kicad-cli sch export netlist --format kicadsexpr -o GMOS-LIA.net GMOS-LIA.kicad_sch
python3 docs/tools/netquery.py GMOS-LIA.net check docs/tools/checks/T01.txt
python3 docs/tools/netcheck.py GMOS-LIA.net
kicad-cli sch erc -o erc.rpt GMOS-LIA.kicad_sch
```

Run all checks at once (summary per file):

```bash
for f in docs/tools/checks/T0*.txt; do
  printf '%-32s %s\n' "$f" "$(python3 docs/tools/netquery.py GMOS-LIA.net check "$f" | tail -1)"
done
```

## 5. Limitations

- Reads only the KiCad S-expression netlist format (KiCad 6 and later; tested on KiCad 10 exports).
- Checks connectivity and fields, not geometry: placement, routing, ERC rules and pin electrical types are out of scope (use KiCad ERC/DRC).
- `between` requires a 2-pin part; for multi-pin parts use `same` on the individual pins.
- Designators must match the export. After re-annotating in KiCad, update the check files and the docs first.