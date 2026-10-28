# Claude Code Prompt — Front-End Decision (D-18) and Pin Verification (D-20)

Paste everything below the line into Claude Code, run from the repository root. Expected runtime: 20–60 min. It changes only `schematics/LIA-board/docs/` and `simulations/` docs; it never touches the KiCad files or firmware.

---

You are helping me close design decision **D-18** (analog front end of the GMOS LIA board) and verify **D-20** (MCU pin/timer facts) before I edit the schematic and layout by hand. The decision is critical because the board must work on the first spin. Be conservative and evidence-driven; every number you use must come from a simulation file in this repo, a datasheet, or a cited web source.

## 0. Read first (do not skip)
1. `schematics/LIA-board/docs/README.md`, `schematics/LIA-board/docs/measurement_principles.md` (§2.6–2.16), `schematics/LIA-board/docs/requirements.md` (DC-*, AN-*, FW-*), `schematics/LIA-board/docs/schematic_overview.md` (§3, §4.8, §4.9, §5, §6), `simulations/simulation-plan.md` (all of §7), `schematics/LIA-board/docs/schematic_review.md` (§1, T00, T03, T04), `schematics/LIA-board/docs/firmware.md` (§F.2).
2. Summarise in ≤ 15 lines: the three candidates FE-A/FE-B/FE-C, the pass criteria of SIM-10…SIM-20 and the decision rule in simulation-plan.md §7.4. Show me the summary and continue without waiting.

## 1. Inventory my simulations
1. List every file under `simulations/` (and any `*.cir`, `*.asc`, `*.net`, `*.opj`, `*.dat`, `*.csv`, `*.txt`, `*.png` elsewhere that looks like simulation output; ask me only if you find nothing).
2. For each simulation: tool, models used (vendor or generic — open the netlist/model includes to check), what was swept, what was measured.
3. Map each one to a SIM-ID in simulation-plan.md §7.2. Produce a table: SIM-ID | candidate | file(s) | vendor models? | measured numbers | pass/fail against the criterion | gaps.
4. Where raw data exists (`.csv`, `.txt`, `.raw` exported to text), compute the numbers with a Python script in `simulations/ti-pspice/docs/sim-results/scripts/` — averages over an **integer number of reference periods after settling**, never `max()`. Save the script; record numbers, not impressions.
5. If a result was obtained with a generic model (ideal switch, ideal op-amp), label it "topology only" — it cannot pass a decision-relevant criterion.

## 2. Research (use Haiku subagents; re-run until sourced)
Launch research as subagents with `model: haiku`, one question group per agent, in parallel. For each agent require: a source URL for every claim (datasheet PDF, manufacturer page, distributor page), the access date, and an explicit "NOT FOUND" instead of a guess. When an agent returns unsourced, contradictory or "NOT FOUND" items, **re-run it** with a narrower question or a different source (manufacturer site → distributor page → app note → forum as last resort) up to 3 times. After 3 failures record the item as unresolved and say what local check closes it.

Question groups:
- **R1 Availability and price (today's date):** AD630JRZ/ARZ, TMUX6136PWR, TMUX1219DCKR, OPA2196IDGKR, OPA2365AIDR, INA828IDR, INA333AIDGKR, LM7705MM, REF3325AIDBZR, ADP7118 fixed versions, LT3094 / the inverting buck-boost used in the netlist. For each: JLCPCB/LCSC stock and part number (basic/extended), Mouser and DigiKey stock, unit price @10, one second-source or pin-compatible alternative. Use the `pcbpart` MCP tools if available (jlc_search, jlc_stock_check, mouser_get_part, digikey_get_part) before the web.
- **R2 Datasheet parameters that decide the matrix:** for TMUX6136, TMUX1219: R_on, R_on flatness, charge injection, C_on, leakage, logic thresholds at 3.3 V, supply range. For OPA2196, OPA2365: input common-mode range, input transition region (OPA2196 is expected at ≈ 2.0–3.5 V on a 5 V rail — confirm), V_os and drift, noise at 500 Hz, output swing to the rails. INA828 vs INA333: noise at 500 Hz with the drain source impedance (330 kΩ ∥ node), input range vs rails, CMRR at 500 Hz. LM7705: output voltage and load capability. REF3325: noise, load regulation, drive capability (it drives every V_REF node — is a buffer needed?). AD630: gain error, linearity, available supply range.
- **R3 Topology evidence:** published app notes or papers that use a CMOS-switch synchronous demodulator of the form in measurement_principles.md §2.16 (e.g. ADI Analog Dialogue on synchronous detectors, LT AN9, TI SLOA024 or newer TI references, lock-in literature in the project PDFs `schematics/LIA-board/docs/` / project files). What error sources do they report, and do any of them match the single-supply V_REF approach?

Write all research results into `schematics/LIA-board/docs/decisions/D-18_research.md` (tables, one source per row, access date).

## 3. Verify MCU facts (D-20) from local ST data — no web guessing
STM32CubeMX is installed on this machine. Find its database (`<CubeMX install>/db/mcu/`): the files `STM32U575R(G-I)Tx.xml` (or the `STM32U575RGTx` equivalent) and `IP/GPIO-STM32U5*_Modes.xml`; also `IP/TIM*` / `IP/DAC*` mode files if present. Use `grep`/a short Python XML parser to answer:
1. Is **PA1** able to be **SPI1_SCK** on STM32U575RGT6? Which AF? If not: is **PB3** SPI1_SCK, and are PA6/PA7 SPI1_MISO/MOSI?
2. AF number for **TIM8_CH1 on PC6** and **TIM8_CH2 on PC7** (expected AF3; a third-party page says AF1 — resolve).
3. **TIM2 internal trigger** selection that corresponds to **TIM8 TRGO** (the ITRx index) on STM32U5.
4. **DAC1 trigger** selection value for **TIM2_TRGO**, and confirm **PA4 = DAC1_OUT1**, **PA5 = DAC1_OUT2**.
5. **USART2**: PA2 = TX, PA3 = RX, AF number.
If the DB cannot be found, generate a CubeMX `.ioc` check list for me to click through instead and stop this section.
Write the answers (with the DB file path + XML line as evidence) to `schematics/LIA-board/docs/decisions/D-20_pins.md`. Update `schematics/LIA-board/docs/firmware.md §F.2.1` and `schematics/LIA-board/docs/schematic_overview.md §5` ONLY where the evidence changes the text; mark each change `(verified CubeMX DB <version>, <date>)`.

## 4. Gap analysis and missing simulations
For each SIM-10…SIM-20 and each still-viable candidate, mark: done / partially done / missing. For missing **decision-critical** ones (SIM-10, 11, 13, 17, 18 for the switch candidates; SIM-12 for all), write a ready-to-run netlist or step-by-step setup for my simulator (detect it from my files: PSpice/LTspice/ngspice), with vendor model file names and where to download them. If ngspice is installed and vendor models are present locally, run them yourself and record results; otherwise give me the setup and stop that item. Do not substitute generic models silently.

## 5. Fill the matrix and recommend
1. Fill `simulations/simulation-plan.md` §7.3 (one row per simulation actually run, with numbers and file paths) and §7.4 (scores 1–5 with a one-line justification and an evidence link per cell). Keep the weights and decision rule unchanged; if you think a weight is wrong, say so separately — do not change it.
2. Apply the decision rule. Write `schematics/LIA-board/docs/decisions/D-18_frontend.md` with:
   - Recommendation (FE-A / FE-B / FE-C) and confidence (high / medium / low), and what result would flip it.
   - Disqualifiers found, with evidence.
   - Residual risks and the bench test that retires each (link to preliminary_lab_test_results.md LAB-* items or propose new ones).
   - Exact BOM delta vs the 2026-10-24 netlist (parts added/removed, LCSC part numbers, unit price), rails removed/added, power-budget change (schematic_overview §6).
   - Which schematic_review.md tasks change (T03, T04 variant, T06…), which check file applies (`schematics/LIA-board/tools/checks/T04_FEA|FEB|FEC.txt`), and which `[AB]`/`[C]` lines of `T03.txt` to enable.
3. If the evidence is insufficient to decide, say so plainly, list the minimum extra simulations/measurements needed, and give a provisional ranking.

## 6. Update the docs consistently (only after §5)
- `schematics/LIA-board/docs/README.md` decision log: D-18 status ("recommended: …, pending owner approval"), D-20 status.
- `schematics/LIA-board/docs/schematic_review.md` §1 and T00: point to the decision files; do not mark D-18 closed — I approve it.
- Run a link check over `schematics/LIA-board/docs/**/*.md` (relative links and `#anchors` resolve) and fix broken ones.
- Show me `git diff --stat` and a 10-line summary. Do not commit.

## Rules
- Never edit the KiCad files in `schematics/LIA-board/` files, the `.ioc`, or firmware sources in this task.
- Every equation you add to a doc is followed by its LaTeX source in a code block.
- Cite sources as `[Title](URL)` (markdown link) with access date; distinguish *measured*, *simulated*, *datasheet*, *estimated*.
- Prefer common, cheap, in-stock parts; flag single-source parts.
- If something contradicts the docs, stop and tell me before changing the docs.
