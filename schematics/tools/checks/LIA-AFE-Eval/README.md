# LIA-AFE-Eval — Expected Results

Check files for the LIA-AFE-Eval KiCad project (`../../../LIA-AFE-Eval/`). One file per task, named after the task (`Txx.txt` or `Txx_<option>.txt`). Syntax and workflow: [tools/README.md §2.3](../../README.md#23-check-file-syntax).

| File | Task |
|------|------|
| `T01.txt` | Schematic entry from requirements rev B: power, excitation, socket and selection, DAC, heaters, drain bias and sense, front end FE-B, demodulators, control header (lines adapted from LIA-Readout T01, T02, T04_FEB, T06; TMUX1109 pins by name because the UQFN numbering differs) |

Where a LIA-AFE-Eval circuit is identical to its LIA-Readout counterpart, copy the relevant lines from [../LIA-Readout/](../LIA-Readout/) and adapt the designators to the LIA-AFE-Eval netlist.
