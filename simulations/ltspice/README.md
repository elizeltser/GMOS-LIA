# LTspice drafts

Early LTspice schematics from before the PSpice for TI project. None has recorded results, and none is used by the current decisions except as a starting point. Index entries for any new run go in [../simulation-index.md](../simulation-index.md).

| File | Contents |
|------|----------|
| `gmos.lib` | GMOS transistor model (BSIM3 v3.1 parameter set, T58F). Included by the schematics below with a relative `.include gmos.lib` |
| `ad630.asc` | AD630 demodulator (LTspice built-in ADI model) with ideal 2nd-order high-pass / low-pass blocks and two GMOS transistors. FE-A topology sketch |
| `quadrature_oscillator.asc` | Analog quadrature oscillator (MAX4489). Rev A excitation, obsolete since decision D-3 |
| `Draft11.asc` | Larger draft with MAX4489 op-amps and GMOS transistors (oscillator and readout) |
| `Draft1.asc`, `filter.asc` | Small drafts (filter) |

Raw output (`*.raw`, `*.log`) is git-ignored.
