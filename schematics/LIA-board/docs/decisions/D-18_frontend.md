# D-18 — Front-End Architecture: Evidence and Recommendation

**Status: recommended FE-B (provisional, confidence low–medium), pending owner approval.** Prepared 2026-10-28 with [frontend_decision.md](../prompts/frontend_decision.md). Research tables: [D-18_research.md](D-18_research.md). MCU facts: [D-20_pins.md](D-20_pins.md).

Evidence tags: *simulated* (PSpice run in this repo), *datasheet*, *estimated* (hand calculation shown here), *measured* (none yet).

## 1. Recommendation

| Item | Result |
|------|--------|
| Recommendation | **FE-B** (±5 V, INA828, K = 2 band-pass, TMUX6136 + OPA2196 switch demodulator), with one change: **TMUX6136 supplied from +7 V / −7 V** (through 10 Ω + 1 µF per pin), not from ±5 V |
| Confidence | **Low–medium.** Most decision-critical simulations (SIM-12, SIM-13, SIM-18, and SIM-10/11 with vendor switch models) have not been run for any candidate. The ranking rests on datasheet limits and estimates |
| Evidence sufficient? | **No** for a final decision by the rule in [simulation-plan.md §7.4](../../../../simulations/simulation-plan.md#74-decision-matrix-for-d-18-fill-in-from-73-and-research). Provisional ranking: **FE-B ≳ FE-C > FE-A** (weighted 51 / 50 / 47 of 75) |
| What flips it to FE-C | (a) The in-amp headroom problem of §3.2 is fixed (INA333 at G = 2 with the gain moved after the HPF, or AN-12b tightened to ≤ ±40 mV), **and** SIM-13-C shows no clipping at the new mismatch limit, **and** SIM-18-C passes. FE-C then wins on cost, rails and area |
| What flips it to FE-A | Only a hard first-pass requirement that outweighs availability: the AD630 is proven, already drawn, but has 0 stock at JLC/LCSC and costs ≈ USD 84 per board for two |

## 2. Simulation Inventory (§1 of the prompt)

**Where the simulations are.** The only decision-relevant simulations are in the PSpice for TI project `simulations/ti-pspice/` (index `simulations/simulation-index.md`, results `simulations/ti-pspice/docs/sim-results/P-xx.md`, all graded A by the project judge, 26–27 Oct 2026). `simulations/ltspice/` holds older LTspice drafts (`ad630.asc` with the LTspice AD630 model and ideal filter blocks, oscillator drafts) with no recorded results. SIM-D1 in simulation-plan.md §7.3 is index entry C-07 (`archive/2026-10-26_lia_sanity_ost_sweep/`).

**What the PSpice circuits are.** `circuits/lia_v3_fast.cir` (demodulator) and `circuits/chain_ss.cir` (chain) run on **one 0–5 V rail with V_REF = 2.5 V**: INA828 (G = 11) → unity-gain SK HPF + LPF (OPA192) → switch demodulator (OPAx192 + behavioural `SPDT_PREC` switch with TMUX6136 parameters), f = 517 Hz, τ = 10 ms (fast) or 0.1 s. This is the FE-C topology with FE-A's filter and the FE-B parts. It matches **no candidate exactly**.

**Models.** OPAx192 (TI, Final 1.7) and INA828 (TI, Final 1.4) are vendor models. The switch `SPDT_PREC` is a **home-made behavioural model** ("not a TI model", `vendor/README.md` §3). It does not enforce the supply range. By rule 5 of the prompt, every demodulator result is therefore **topology only**. The vendor model files are on the Windows PSpice installation, not in this repo (`vendor/` is git-ignored), and no raw `sim-runs/` data is in the repo. So no `simulations/_analysis/` script could be written. The numbers below are taken from the graded summaries.

| SIM-ID | Candidate | File(s) | Vendor models? | Measured numbers (source) | Pass vs criterion | Gaps |
|--------|-----------|---------|----------------|---------------------------|-------------------|------|
| SIM-10 | C (topology, B by analogy) | P-02 `lia_v2.cir`, 2 V amplitude, 25 phases | Op-amp yes, switch **no** | R = 1.272742 V, −0.039 % vs 2A/π (time-step error, 0.0005 % at 2 µs, P-05); phase error ≤ 0.23° vs p − d, 0.05° vs atan2 | Topology only. Would pass ±0.5 % and 0.2° | Not at 0.4 V pk; no TMUX1219/TMUX6136 vendor model; OPA2365 not used |
| SIM-11 | C (topology) | P-04 (amplitude 10 mV…3 V), P-03 (offset sweep), P-13 (V_OS) | Op-amp yes, switch no | Linear to 2.5 V: VX deviation ≤ 0.004 % from 10 mV to 2 V after fit, offset < 0.01 mV; clip at 2.75 V; V_OS appears as 2·V_OS (±0.16 µV) | Topology only. Would pass 0.1 % and 1 mV | Charge injection of the real switch (TMUX1219 −10 pC, 25× model) untested (DI-01 / R-04 of the PSpice register) |
| SIM-12 | all | SIM-2/SIM-3 (Python, ngspice), 20 pF | — | Median 56 dB at 20 pF (measurement_principles §2.7) | Not run at 50 pF | **Missing**: re-run at C_node = 50 pF ± 10 % |
| SIM-13 | (C-like) | P-09 `chain_ss.cir`, 15 mV | INA828, OPA192 yes; switch no | Front-end gain 11.073 V/V (−0.055 %), R −0.06 %, phase −0.13°; INA828 model CM range 2.00–3.00 V on 5 V | Partial; candidate values not used | **Missing**: drain-node sources at 50–250 mV, ±200 mV mismatch, K = 2 band-pass, INA333/LM7705 |
| SIM-14 | A (unity-gain SK) | P-14 `frontend_mc.cir` (1 % R, 5 % C), SIM-4 (Python, 0.1 %/1 %) | yes | P-14: phase σ 3.44°, gain σ 3.62 % at 1 %/5 %; SIM-4: σ 0.66°, 0.06 dB at 0.1 %/1 % | A: pass at 0.1 %/1 % (SIM-4) | **Missing** for the K = 2 band-pass (B, C) |
| SIM-15 | demodulator only | P-05 (3f, 7f), P-06 (467/567/83 Hz) | op-amp yes | VX follows 1/n within 0.01 dB; non-harmonic shifts ≤ 0.022 mV | Partial | Band-pass and τ = 0.5 s not included; 50 Hz, 500/550 Hz not run |
| SIM-16 | (A/B in-amp) | P-15 `chain_ss_P15.cir` `.NOISE` | yes | 12.68 nV/√Hz input-referred (INA828 G = 11, R_G dominated), 14.2 nV/√Hz with datasheet noise (DI-14) | Amplifier ≪ 730 nV/√Hz shot noise → pass for INA828 | INA333 not simulated (datasheet gives 50 nV/√Hz only at G = 100) |
| SIM-17 | all | P-13 (static 2·V_OS) | — | No drift simulation | — | Estimated in §4 instead |
| SIM-18 | all | — | — | — | — | **Missing** |
| SIM-19, 20 | all | — | — | — | — | Missing; not decision-relevant |
| Other | C | P-10 (reference/rail pickup), P-12 (driver impedance), P-16 (overload), P-17 (square wave) | yes | 1 mV V_REF ripple at f₀ → 0.637 mV DC if V_REF is **separate**; tracks to ≈ 0 if one shared node (DI-04); 10 Ω in series with demodulator input → −0.1 % | Supports one shared, buffered V_REF node | |

## 3. Disqualifiers Found

### 3.1 FE-B: TMUX6136 on ±5 V is at the edge of its rating (fix identified)

The datasheet requires 10 V ≤ (VDD − VSS) ≤ 33 V ([SCDS397B](https://www.ti.com/lit/ds/symlink/tmux6136.pdf) §5.4, note 1; *datasheet*). ±5 V rails give exactly 10 V, so any negative tolerance violates it. The PSpice design register already lists this as DI-01, Critical. **Fix:** supply VDD/VSS from the +7 V / −7 V intermediate rails (14 V), each through 10 Ω + 1 µF. The signal pins stay at ±2.4 V, and VIH = 2 V min keeps the 3.3 V references valid. On ±15 V, R_on is 120 Ω typ / 135 Ω max. At 14 V it will be higher (no table, ≤ 400 Ω by the 12 V-single table). In series with the op-amp +IN, this does not matter.

### 3.2 FE-C: INA333 first-stage headroom fails the ±200 mV mismatch (no fix within the current spec; *estimated*)

INA333 is a 3-op-amp in-amp with two internal 50 kΩ feedback resistors ([SBOS445C](https://www.ti.com/lit/ds/symlink/ina333.pdf), simplified schematic; G = 1 + 100 kΩ/R_G). The first-stage outputs are

$$
V_{A1,A2} = V_{IN\pm} \pm \frac{G-1}{2}\,V_{d}
$$

```latex
V_{A1,A2} = V_{IN\pm} \pm \frac{G-1}{2}\,V_{d}
```

At G = 10 that is V_IN ± 4.5·V_d. The lower internal output must stay above about V− + 0.05 V = −0.18 V (output swing 50 mV from the rail at 10 kΩ, SBOS445C §7.5; LM7705 V− = −0.232 V). The largest mismatch is then

$$
|V_d|_{\max} \approx \frac{V_{IN,\mathrm{low}} + 0.18\ \mathrm{V}}{4.5}
$$

```latex
|V_d|_{\max} \approx \frac{V_{IN,\mathrm{low}} + 0.18\ \mathrm{V}}{4.5}
```

This gives ≈ 51 mV for a drain at 50 mV and ≈ 96 mV for a drain at 250 mV, against the required ±200 mV (AN-12b). The input pins themselves are within range (−0.13 V). It is the internal nodes that clip. measurement_principles.md §2.15 item 4 does not consider this. A deeper V− does not help: the INA333 supply is limited to 5.5 V total, so V− ≥ −0.5 V on +5 V, giving |V_d| ≤ 0.11 V. Confirm with TI's in-amp common-mode calculator or SBOS445C Fig. 21/23 ("Common-Mode Range vs Output Voltage").

**Possible fixes (owner decision, then SIM-13-C):** (a) INA333 at G = 2 (R_G = 100 kΩ, first-stage swing 0.5·V_d) and an extra ×5 after the HPF. Noise at G = 2 is not tabulated and must be checked against the 10 % budget. (b) Tighten AN-12b to ≤ ±40 mV. Firmware can null the mismatch with the drain DACs (3.8 µV steps), but channel switching must then avoid transient overload. (c) A different in-amp. None was found in this research.

### 3.3 FE-A: availability (not a pass criterion, scored)

AD630ARZ: 0 stock at JLC/LCSC (all three listings), Mouser 111, DigiKey 53, ≈ USD 42 each, single source (ADI). The PSpice project's own sourcing rules exclude it (`simulations/design-context.md` §8). The orderable code "AD630JRZ" does not exist.

## 4. Estimates Used in Place of Missing Simulations

**SIM-17 (drift, *estimated* from typical datasheet values).** The demodulator op-amp drift appears ×2 at its output and is divided by the gain before it (G_pre). The post-filter op-amp drift is multiplied by its noise gain (1 + G_post) and divided by G_pre·G_post.

| Candidate | Demodulator | Post-filter | Referred to drain |
|-----------|-------------|-------------|-------------------|
| FE-A | AD630 drift **unknown** (datasheet unreadable here) | OPA2196 0.5 µV/°C × 4 / 60 = 0.033 µV/°C | docs estimate ≈ 0.15 µV/°C; unverified |
| FE-B | OPA2196 0.5 µV/°C × 2 / 40 = 0.025 µV/°C | 0.5 × 2.5 / 60 = 0.021 µV/°C | ≈ 0.05 µV/°C (sum) |
| FE-C | OPA2365 1 µV/°C × 2 / 40 = 0.05 µV/°C | 1 × 2.5 / 60 = 0.042 µV/°C | ≈ 0.09 µV/°C (sum); V_REF drift cancels if one node |

All are below 0.2 µV/°C at typical values. Maximum drift values were not extracted.

**SIM-16 (noise).** INA828 (7 nV/√Hz) adds 0.01 % noise power against 730 nV/√Hz. INA333 adds 0.5 % at 50 nV/√Hz and 1.9 % even at 100 nV/√Hz. Both are within the 10 % budget.

**FE-B transition region.** The demodulator op-amp +IN follows the signal up to 2.14 V pk at ADC full scale. OPA2196's region starts at (V+) − 3 V = 2.0 V ([SBOS869](https://www.ti.com/lit/ds/symlink/opa2196.pdf) §7.5), so only the top 7 % of full scale enters it. This is low risk, and SIM-11-B should report it.

## 5. Decision Matrix (provisional; to be copied into simulations/simulation-plan.md §7.4 after approval)

Weights unchanged. Scores 1–5.

| Criterion (weight) | FE-A | FE-B | FE-C | Evidence |
|--------------------|------|------|------|----------|
| First-pass success risk (×3) | 4: proven IC, as drawn; no vendor-model sim | 3: topology simulated (P-01…P-17); needs ±7 V switch supply (§3.1) | 2: topology simulated on 5 V, but in-amp headroom fails (§3.2), SIM-18 missing | §2, §3 |
| Accuracy (×2) | 4: AD630 0.05 % (B grade, snippet) | 4: P-02/P-04 ≤ 0.04 % (topology) | 4: same | P-02, P-04 |
| Baseline drift (×2) | 3: AD630 unknown | 5: ≈ 0.05 µV/°C | 4: ≈ 0.09 µV/°C | §4 |
| Noise (×1) | 5 | 5 | 4 | §4, P-15 |
| CMRR / interference (×2) | 3 | 3 | 3 | Same node topology; SIM-12 missing for all |
| Part availability (×2) | 1: AD630 LCSC 0, Mouser 111 | 2: TMUX6136 LCSC 150, Mouser 3516; no low-Q drop-in | 3: TMUX1219 ample; INA333 and OPA2365 stocked at LCSC only (OPA2388 is a second source); LM7705 LCSC 128 + MM 999 | D-18_research R1 |
| BOM cost (×1) | 1: ≈ +USD 84–107 for 2× AD630 | 3 | 5 | R1, §6 |
| Board area / rails (×1) | 2 | 3 | 5: −7 V/−5 V chain removed | schematic_overview §3 |
| Schematic change effort (×1) | 5 | 3 | 2 | schematic_review T03/T04 |
| **Weighted total (of 75)** | **47** | **51** | **50** | |

FE-B and FE-C are within 10 %. The rule then prefers FE-C only if SIM-18 passes and SIM-13 shows no clipping at ±200 mV. §3.2 predicts clipping, so the rule selects **FE-B**. Weight comment, not applied: "first-pass risk" and "availability" pull in opposite directions for FE-A. That is intended, but a JLC-assembly constraint could justify treating LCSC stock 0 as a disqualifier.

## 6. BOM, Rails and Power Delta vs the 2026-10-24 Netlist (FE-A as drawn)

| Change | FE-B | FE-C |
|--------|------|------|
| Remove | U5, U6 (AD630ARZ), R18, R19, R52, R53 | Same + U18 (LMR51430 IBB), L2, R35, R36, C37, C39, C41, C42, U19 (LT3094), R37, C40, C43, D2 |
| Add | TMUX6136PWR C2673380 (5.77); OPA2196IDGKR C2057920 (1.73); 4× 10.0 kΩ 0.1 % (demodulator); 4× 10.0 kΩ 0.1 % (band-pass gain); 2× 10 Ω + 2× 1 µF (switch supply from ±7 V) | 2× TMUX1219DCKR C2867958 (0.18); OPA2365AIDR C130011 ×3 (1.22, U3, U4, demodulator); INA333AIDGKR C19450 (1.22, replaces INA828); LM7705MMX C2070761 (0.59); REF3325AIDBZR C69039 (0.59); same resistors; **recommended:** V_REF buffer (INA333 REF pin needs < tens of Ω, SBOS445C §8; REF3325 AC output impedance unknown) |
| Change | U3/U4 band-pass to equal-component K = 2 | Same; U3, U4 → OPA2365 |
| Net cost per board (LCSC prices) | ≈ −USD 99 | ≈ −USD 114 (−107 AD630, −8.4 negative chain, +1.6 new parts) |
| Rails removed / added | None (TMUX6136 also loads ±7 V, µA) | −7 V, −5VA removed; VREF_2V5, −0.23 V added |
| Power (schematic_overview §6) | +5VA 37 mA, −5VA 13 mA (unchanged from §6) | +5VA **≈ 86 mA, not ≈ 60 mA**: OPA2365 I_Q is 4.6 mA **per amplifier** ([SBOS365G](https://www.ti.com/lit/ds/symlink/opa2365.pdf) §6.5), so 3 duals = 27.6 mA typ, against ≈ 10 mA assumed in §6 |

## 7. Effect on schematic_review.md Tasks

| Task | FE-B | FE-C |
|------|------|------|
| T03 Power | All-option steps 1–2 only; keep the IBB/LT3094 values; add the ±7 V feeds to TMUX6136. `T03.txt`: keep `[AB]` lines | Steps 1–4; `T03.txt`: remove `[AB]`, enable `[C]` |
| T04 Front end | FE-B variant; check file `T04_FEB.txt` | FE-C variant; `T04_FEC.txt` |
| T06 DAC sheet | Unchanged | U9, U10, U1 and drain sense lose −5VA → V− to GND (all signals 0.4–4 V; drain sense output near 0 V at low drain voltage, check) |
| T07 ADC | AIN1/AIN3 ← VMID | AIN1/AIN3 ← VREF_2V5 |

The check files are in `schematics/LIA-board/tools/checks/` (`T03.txt`, `T04_FEA.txt`, `T04_FEB.txt`, `T04_FEC.txt`, …), run with `tools/netquery.py`.

## 8. Residual Risks and Retiring Tests

| Risk | Candidate | Retiring test |
|------|-----------|---------------|
| TMUX6136 on ±7 V: R_on, charge injection and supply coupling not characterised at 14 V | B | SIM-10/11-B (below); LAB-9 (full chain vs SR860) |
| TMUX6136 single low-stock source at JLC (150) | B | Order the BOM quantity now, or consign from Mouser (3516) |
| Real switch charge injection (TMUX1219 −10 pC) | C | SIM-10/11-C with datasheet parameters |
| In-amp headroom (§3.2) | C | SIM-13-C; **new LAB-11**: step the drain mismatch 0 → ±200 mV with the drain DACs and record BPF_OUT and X |
| Power-up of LM7705 / REF3325 / INA333 | C | SIM-18-C if TI models exist; otherwise LAB-3 (rails and sequencing) extended with V_REF and V− ramps |
| System CMRR at 50 pF node capacitance | all | SIM-12 (Python Monte-Carlo update of SIM-2); LAB-6 |
| AD630 values unverified | A | Read the AD630 datasheet (analog.com unreachable here) |

## 9. Setups for the Missing Decision-Critical Simulations (to run in PSpice for TI)

Not run here, at the owner's request. Base everything on the existing `simulations/ti-pspice/circuits/` files and the runner `tools/run_sim.py`, with `.OPTIONS NUMDGT=8`, a 2 µs maximum step, and 20 periods averaged after settling (simulation-plan.md rules). Vendor models: download from each TI product page ("Design & development → Models"): INA333, OPA2365, REF3325, TMUX1219, TMUX6136, OPA2196. If TI offers no PSpice model for a switch, use `SPDT_PREC` with the datasheet parameters below and label the result *topology only*.

| Run | Base file | Changes | Pass |
|-----|-----------|---------|------|
| **SIM-13-C** headroom | `chain_ss.cir` | U1 → INA333 (R_G = 11 kΩ), V− = −0.232 V source, REF = VREF. Replace the sensor with two drain sources: DC 0.05 V and 0.25 V (+200 mV), swapped (−200 mV), and 0.15/0.15 V; 10 mV pk differential sine at 518 Hz. K = 2 band-pass (R = 9.31 kΩ, C = 33 nF, gain 10 k/10 k), OPA2365. `.STEP` the mismatch | VX within ±1 % of −38.2·v̂ scale at all three mismatches. Expected (§3.2): failure at ±200 mV. Repeat with R_G = 100 kΩ (G = 2) to test fix (a) |
| **SIM-10/11-C** | `lia_v3_fast.cir` | OPAx192 → OPA2365; `SPDT_PREC` RON = 5, QINJ = 10p, CS = CD = 23p, VTH 1.49 V; Vampl LIST 1m 10m 0.1 0.4 2.1 | SIM-10/11 criteria |
| **SIM-10/11-B** | `lia_v3_fast.cir` with ±5 V op-amp supply, REF = 0 | OPAx192 → OPA2196; `SPDT_PREC` RON = 400, QINJ = 0.7p, CS = CD = 5.5p; Vampl to 2.14 V | SIM-10/11 criteria; report the 2.0–2.14 V transition-region error |
| **SIM-18-C** | new | Ramp +5VA (5 ms) with LM7705 and REF3325 models, in both orders against the references | No latch-up; recovery < 1 s |
| **SIM-12** (all) | SIM-2 Python | C_node = 50 pF ± 10 %, R_D 0.1 %, ≥ 200 runs | Median ≥ 48 dB |

## 10. Contradictions Found (reported before any change to the docs)

1. measurement_principles §2.15 item 4 and schematic_overview §4.9 say INA333 with LM7705 covers the ±200 mV mismatch. §3.2 above says it does not, at G = 10.
2. schematic_overview §4.9 specifies TMUX6136 "±5 V". The datasheet minimum is 10 V differential, with no margin (§3.1).
3. schematic_overview §6 FE-C +5VA ≈ 60 mA assumes OPA2365 ≈ 5 mA per dual. The datasheet gives 4.6 mA per amplifier (≈ 86 mA total).
4. Resolved on 2026-10-28: simulation-plan.md §7.3 now points SIM-D1 to `simulations/ti-pspice/archive/2026-10-26_lia_sanity_ost_sweep/` (index C-07).
5. The simulation baseline `simulations/design-context.md` has a different baseline from the board docs: single supply only, 517 Hz, in-amp G = 11, τ = 0.1 s, square-wave excitation, and the AD630 excluded. Its results are therefore not candidate-exact.
6. (Resolved 2026-10-28 by the repository reorganisation: board docs now in `schematics/LIA-board/docs/`, tools in `schematics/LIA-board/tools/`, prompt in `docs/prompts/`, decisions in `docs/decisions/`.)
7. Minor: OPA2196 slew rate is 7.5 V/µs in the docs and 5.5 V/µs on the TI product page (unresolved, irrelevant to the result).
