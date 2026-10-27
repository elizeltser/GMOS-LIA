# LIA offset sweep (26 October 2026)

This folder is a frozen copy of the `LIA/lia_sanity` run that finished on 26 October 2026 at 23:21. It was copied before the schematic was changed, so the result can still be opened and plotted later. Simulation index entry: C-07 in `docs/simulation-index.md`.

## What was simulated

| Item | Value |
|---|---|
| Netlist | `LIA.net` (copy in this folder) |
| Analysis | `.TRAN 0 2 0 20u SKIPBP` |
| Sweep | `.STEP LIN PARAM ost -2 2 0.1` (41 runs) |
| Fixed parameters | `p = 0`, `f_osc = 517 Hz`, `vdc = 5 V`, `t_slope = 100 ns` |
| Input V4 | `SIN({Vdc/2+ost} 2 {f_osc} 0 0 {p})`, so 2 V amplitude on a 2.5 V + ost offset |
| Y reference V6 | delay 482.6 us (fixed value, not tied to `f_osc`) |
| Solver time | 8672 s (about 2.4 h) |

The Probe window was set to a performance-analysis plot of `max(V(Vy))`.

## How to open it

Open `lia_sanity.dat` in PSpice with File > Open. The `.prb` file in this folder has the same base name, so the saved plot window settings load with it. Do not run a simulation from this folder. A run would overwrite the copy.

The `.dat` (2.95 GB) and `.out` files are git-ignored. They exist only on this computer.
