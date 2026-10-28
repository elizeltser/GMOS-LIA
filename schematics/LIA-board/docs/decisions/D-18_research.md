# D-18 — Research Results (R1 Availability, R2 Datasheets, R3 Topology)

Collected 2026-10-28 for [D-18_frontend.md](D-18_frontend.md). Tags: *datasheet* = read from the PDF text (`pdftotext` of `ti.com/lit/ds/symlink/<part>.pdf`); *product page* = TI product-page parametric table; *distributor* = pcbpart MCP tools (JLC/LCSC, Mouser, DigiKey). All accessed 2026-10-28. LCSC prices have no stated currency in the tool output (USD assumed); Mouser/DigiKey prices are USD.

## R1 Availability and Price

Sources: pcbpart `jlc_get_part`, `jlc_stock_check`, `jlc_find_alternatives`, `mouser_get_part`, `digikey_get_part` (2026-10-28). Lifecycle = Mouser/DigiKey lifecycle field. Every part below is made by **one manufacturer only** (single-source). All are JLC **extended** parts.

| Part | Used in | LCSC # | LCSC stock | Mouser | DigiKey | Price @10 | Second source / alternative |
|------|---------|--------|-----------:|-------:|--------:|-----------|-----------------------------|
| AD630ARZ (SOIC-20) | FE-A ×2 | C495335 / C88061 / C2838067 | **0** | 111 | 53 | LCSC 53.51 (@1); Mouser 41.90; DigiKey 42.79 | None (ADI only). `AD630JRZ` does not exist in any catalog (7 queries) |
| TMUX6136PWR | FE-B ×1 | C2673380 | **150** | 3516 | 1978 | LCSC 5.77; Mouser 5.16 | No drop-in with equal charge injection. TMUX6236PWR C37405251 (pinout verified, EN on pin 14, **78 pC**), ADG1636BRUZ C655247 (pinout verified, 130 pC, 243 pF), ADG1436YRUZ (Mouser 267, pinout not verified) |
| TMUX1219DCKR | FE-C ×2 | C2867958 | 2774 | 53528 | 32664 | LCSC 0.177; Mouser 0.20 | SN74LVC1G3157 C38663 (pinout not verified, R_on 6 Ω) |
| TMUX1136DGSR | FE-C alt. | C2673301 | 7 | 6140 | 5046 | LCSC 2.33; Mouser 2.57 | TMUX1136DQAR C1849390 (USON, not drop-in) |
| OPA2196IDGKR | FE-A/B | C2057920 | 759 | 4450 | 6122 | LCSC 1.73; Mouser 2.68 | **OPA2192IDGKR C2876419** (stock 23636, pinout verified vs TI DGK order), OPA2197IDGKR C2867268 (10679) |
| OPA2365AIDR | FE-C ×3 | C130011 | 4037 | **57** | **0** | LCSC 1.22; Mouser 3.45 | **OPA2388IDR C1517414** (zero-crossover, zero-drift, 5 V/µs, LCSC 13701, Mouser 2988, pinout verified) |
| INA828IDR | FE-A/B | C544342 | 7429 | **0** | **0** | LCSC 1.36 | INA821IDR C2060822 (13322, pinout not verified) |
| INA333AIDGKR | FE-C | C19450 | 3075 | **0** | **0** | LCSC 1.22 | None drop-in found (INA128 is not a 5 V part) |
| LM7705MMX/NOPB | FE-C | C2070761 | 128 | 11459 | 2797 | LCSC 0.59; Mouser 0.71 | **LM7705MM/NOPB C129980** (999, identical pinout); LM7705MME C2070717 |
| REF3325AIDBZR | FE-C | C69039 | 23671 | 1026 | 11033 | LCSC 0.59; Mouser 1.48 | REF5025AIDR C11341 (SOIC-8, not drop-in) |
| ADP7118ACPZN5.0-R7 | all ×2 | C659349 | 2765 | 33 | 319 | LCSC 1.88 | — |
| ADP7118ACPZN3.3-R7 | all | C659348 | 508 | 557 | 2341 | LCSC 1.68 | — |
| LT3094EMSE#PBF | FE-A/B | C498217 | 383 | 5387 | 1038 | LCSC 7.36; DigiKey 7.80 | `#TRPBF` C670494 (same die, 6128) |
| LMR51430XFDDCR | all (+ IBB in A/B) | C5219260 | 7078 | 1440 | 4786 | LCSC 1.01 | LMR51430YFDDCR C5219261 (1.1 MHz variant) |

## R2 Datasheet Parameters

| Part / parameter | Value | Doc, section | Note |
|------------------|-------|--------------|------|
| **TMUX6136** supply | **10 V ≤ (VDD − VSS) ≤ 33 V**; dual ±5…±16.5 V; single 10–16.5 V | [SCDS397B](https://www.ti.com/lit/ds/symlink/tmux6136.pdf) §5.4 + note (1) | *datasheet*. ±5 V rails give exactly 10 V: **any negative rail tolerance is out of rating** |
| TMUX6136 logic | VIH 2 V min, VIL 0.8 V max | SCDS397B §5.5/5.7 | 3.3 V logic OK |
| TMUX6136 R_on / Q_inj | 120 Ω typ, 135 Ω max (±15 V); −0.4 pC (±15 V), −0.7 pC (12 V) | SCDS397B §5.5, §5.7 | No ±5 V table exists |
| **TMUX1219** (5 V ±10 %) | R_on ≤ 5 Ω; ΔR_on 0.4 Ω; VIH 1.49 V min; VIL 0.87 V max; Q_C **−10 pC**; C_on 23 pF | [SCDS409A](https://www.ti.com/lit/ds/symlink/tmux1219.pdf) §6.5 | *datasheet*. 3.3 V logic OK |
| TMUX1219 pinout (DCK) | 1 SEL, 2 VDD, 3 GND, 4 S1, 5 D, 6 S2; SEL low = S1 | SCDS409A Pin Functions | Matches schematic_overview §4.9 |
| TMUX1136 | 1.08–5.5 V; R_on ≈ 2 Ω; Q −6 pC; C_on 20 pF | product page | Not read from datasheet |
| **OPA2196** transition region | **(V+) − 3 V < V_CM < (V+) − 1.5 V** | [SBOS869](https://www.ti.com/lit/ds/symlink/opa2196.pdf) §7.5 (l. "See Common-Mode Voltage Range") | *datasheet*; confirms docs §2.15 |
| OPA2196 V_OS / drift | ±25 µV typ, ±100 µV max; ±0.5 µV/°C typ | SBOS869 §7.5, Features | |
| OPA2196 slew | 5.5 V/µs (product page) vs 7.5 V/µs (JLC listing) | — | Datasheet value lost in text extraction. Docs use 7.5 V/µs: **unresolved**, either is ≫ needed |
| **OPA2365** | 2.2–5.5 V; V_OS 100 µV typ / 200 µV max; V_CM (V−)−0.1 to (V+)+0.1 V; **zero-crossover, no transition region**; 25 V/µs; 4.5 nV/√Hz @100 kHz | [SBOS365G](https://www.ti.com/lit/ds/symlink/opa2365.pdf) §6.5, §7.3 | *datasheet* |
| **INA333** | V_CM (V−)+0.1 to (V+)−0.1 V (at V_O = 0 V); e_NI 50 nV/√Hz **at G = 100 only**; i_N 100 fA/√Hz; G = 1 + 100 kΩ/R_G; CMRR ≥ 100 dB (G ≥ 10) | [SBOS445C](https://www.ti.com/lit/ds/symlink/ina333.pdf) §7.5 | *datasheet*. Noise at G = 10 not tabulated (higher than 50 nV/√Hz) |
| **INA828** | V_CM (V−)+2 V to (V+)−2 V; e_NI 7 nV/√Hz; CMRR ≥ 110 dB (G = 10) | [SBOS792A](https://www.ti.com/lit/ds/symlink/ina828.pdf) §6.5 | On ±5 V: −3…+3 V, drains (0–0.45 V) OK. On single 5 V: 2–3 V only (also seen in PSpice P-09) |
| **LM7705** | V_OUT −0.232 V ±5 %; 26 mA; 4 mVpp ripple; supply 3.23–5.48 V (VDD wrt VOUT) | [LM7705 datasheet](https://www.ti.com/lit/ds/symlink/lm7705.pdf) §7 | *datasheet* |
| **REF3325** | ±5 mA; load reg. 20 ppm/mA max (−40…85 °C); C_L 0.1–10 µF; 70 µVpp (0.1–10 Hz); 30 ppm/°C max | [SBOS392I](https://www.ti.com/lit/ds/symlink/ref3312.pdf) §6.5 | *datasheet*. AC output impedance at 518 Hz not tabulated |
| AD630 | Gain ±1/±2 at 0.05 % (B grade), 2 MHz, 45 V/µs | search snippet only | **Unresolved**: analog.com unreachable from this network (HTTP 000, 3 attempts) |

## R3 Topology Evidence

| Source | Topology | Supply | Error sources reported | Status |
|--------|----------|--------|------------------------|--------|
| L. Orozco, [Synchronous Detectors Facilitate Precision Low-Level Measurements](https://www.analog.com/en/resources/analog-dialogue/articles/synchronous-detectors-facilitate-precision.html), Analog Dialogue 48-11, 2014 | ADG619 SPDT sets amplifier gain +1/−1 (Fig. 4), RC filter, ADA4077 output amp | ±5 V (snippet) | 1/f noise and offset drift of the post-demodulator amplifier (ADA4077: 0.55 µV/°C) | Full text **not read** (site unreachable); from search snippets |
| J. Williams, [40 nVp-p Noise, 0.05 µV/°C Drift, Chopped FET Amplifier](https://xdevs.com/doc/Linear/Documentation/LTMag-V16N01-11-FETAmp-Williams.pdf), LT Magazine V16N01, 2006 | Chopper with synchronous switch demodulation | — | Chopping frequency chosen unrelated to mains (925 Hz) | Snippet |
| Gabal et al., A Low-Voltage Single-Supply Analog Lock-in Amplifier…, RFID SysTech 2010 ([TIB record](https://www.tib.eu/en/search/id/vde:453282012)) | In-amp → polarity-reversing switch mixer → LPF | **3 V single supply** | Not in abstract | Abstract only |
| LT AN9, TI SLOA024 | — | — | — | **NOT FOUND** (1 search each) |
| Project PDFs (`../app_notes/slyt164.pdf`, `../app_notes/snva856b.pdf`) | Oscillators; inverting buck-boost | — | Not relevant to the demodulator | Checked locally |

**Conclusion R3.** The switch demodulator is a published, standard topology (ADI ADG619 example; the AD630 has the same internal structure). No published note with the exact single-supply V_REF = 2.5 V variant was found. The strongest evidence for that variant is this project's own PSpice work (P-01…P-17, single 5 V, V_REF 2.5 V; see D-18_frontend.md §2).

## Unresolved Items and the Check That Closes Each

| Item | Attempts | Local check |
|------|----------|-------------|
| AD630 datasheet values (input range at ±5 V, nonlinearity) | analog.com ×3 (timeout) | Download the AD630 PDF on another network |
| OPA2196 slew rate (5.5 vs 7.5 V/µs) | product page, JLC, PDF text | Read SBOS869 §7.5 in a PDF viewer |
| INA333 noise at G = 10 | datasheet table only at G = 100 | SBOS445C noise-vs-gain figure, or PSpice `.NOISE` with the INA333 TI model |
| REF3325 output impedance at 518 Hz | datasheet (not tabulated) | PSpice with the REF3325 TI model, or bench: inject 1 mA at 518 Hz |
| ADG1436YRUZ (TSSOP) pinout as TMUX6136 second source | JLC (only LFCSP) | ADG1436 datasheet pin table |
| ADI Analog Dialogue 48-11 full text, LT AN9, TI SLOA024 | 6 / 1 / 1 | Read on another network |
