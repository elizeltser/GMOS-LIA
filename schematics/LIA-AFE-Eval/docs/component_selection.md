# LIA-AFE-Eval — Component Selection

Parts for each schematic sheet, chosen to meet [requirements.md](requirements.md). Circuit values follow the LIA-Readout FE-B design ([schematic_overview.md](../../LIA-Readout/docs/schematic_overview.md) §3–§4.9) unless this file says otherwise. Stock and unit prices are JLCPCB/LCSC, checked 2026-10-29. Quantities are per board.

Rules applied: thin-film 0.1 % resistors wherever a ratio or a DC level matters; the drain path uses ±10 ppm/°C parts (AN-4a); C0G capacitors in signal paths are ±5 % for the first build and are reworked to ±1 % later (E-5); one manufacturer family for every resistor pair whose ratio sets a gain, so their drifts track.

## C.1 Stock Risks

| Part | Stock | Needed per board | Action |
|------|-------|------------------|--------|
| DAC80508ZRTET (C2863226) | 140 | 1 | Order or reserve early; USD 22.18, the most expensive part |
| TMUX6136PWR (C2673380) | 145 | 2 | Order or reserve early |
| TMUX1109RSVR (C2673348) | 209 | 2 | TSSOP version (TMUX1109PWR) has 1 piece left, so the UQFN-16 (1.8 × 2.6 mm, 0.4 mm pitch) version is used (E-6). Hard to rework by hand |
| DC3-2.54-26PAL (C5156669) | 91 | 1 | Fallback: straight 2 × 13 pin header C2894974 (3375 in stock, not keyed) |

## C.2 Power (sheet Power)

| Function | Part | LCSC | Stock | Qty | Notes |
|----------|------|------|-------|-----|-------|
| Input terminal (+V, GND, −V) | Kangnex WJ500V-5.08-03P | C72334 | 167 970 | 1 | 5.08 mm screw terminal |
| Reverse-polarity protection | B5819W (MDD) | C64885 | 738 935 | 2 | Series diode in each input. ≈ 0.4 V drop at the load current, leaves ≥ 2.6 V LDO headroom at ±8 V in |
| +5VA, +5VP | ADP7118ACPZN5.0-R7 | C659349 | 2745 | 2 | As LIA-Readout DC-4, DC-4b; C_OUT ≥ 2.2 µF X7R, C_IN 1 µF + 100 nF |
| −5VA | LT3094EMSE#PBF | C498217 | 405 | 1 | As LIA-Readout; R_SET 49.9 kΩ 0.1 % (C705780), C_SET 4.7 µF, C_OUT 10 µF |
| Rail clamps | B5819W (MDD) | C64885 | — | 2 | +5VA → GND and GND → −5VA (LIA-Readout DC-4a) |
| TMUX6136 supply filter | 10 Ω + 1 µF X7R per supply pin | — | — | 4 + 4 | From the protected ±9 V input (DC-3) |

## C.3 Connectors and Test Points (sheet Connectors)

| Function | Part | LCSC | Stock | Qty | Notes |
|----------|------|------|-------|-----|-------|
| X, Y outputs | BAT WIRELESS BWSMA-KE-Z001 | C496549 | 125 773 | 2 | SMA, through-hole, vertical. 100 Ω series resistor at each output |
| NUCLEO control header | ZHOURI DC3-2.54-26PAL | C5156669 | 91 | 1 | Keyed 2 × 13 IDC box header, right angle. Pinout: requirements IF-5 |
| Signal test loops | Keystone 5000 (red) | C5199900 | 23 991 | ≈ 25 | LU-1 |
| GND test loops | Keystone 5001 (black) | C238122 | 6122 | ≈ 6 | One next to each group |
| Sensor socket | BOOMELE DIP-40 socket, 15.24 mm rows | C2332 | 8820 | 1 | Footprint also fits a DIP-40 ZIF socket (e.g. 3M Textool 240-1280-00-0602J, Mouser/DigiKey, hand-soldered) if frequent sensor changes need it |
| Mounting | M3 holes, 4 corners | — | — | 4 | LU-2 |

## C.4 Bias DAC (sheet DAC)

| Function | Part | LCSC | Stock | Qty | Notes |
|----------|------|------|-------|-----|-------|
| 8-channel 16-bit DAC | DAC80508ZRTET | C2863226 | 140 | 1 | AVDD = +5VA, VIO = NUCLEO 3.3 V (E-4). Channel use as LIA-Readout §4.6.1 |

## C.5 Excitation (sheet Excitation)

Values as LIA-Readout §4.5 (two MFB stages, `GATE_A`, `GATE_B`).

| Function | Part | LCSC | Stock | Qty | Notes |
|----------|------|------|-------|-----|-------|
| Op-amp | OPA2196IDGKR | C2057920 | 759 | 1 | Both stages |
| R_in 120 kΩ 0.1 % | Yageo RT0603BRD07120KL | C705720 | 136 384 | 2 | |
| R_fb, R_3 1.00 kΩ 0.1 % | RESI PTFR0603B1K00N9 (±10 ppm) | C394536 | 187 487 | 4 | Same family as R_in is not available at 120 kΩ; gain −1/120 is calibrated |
| C_X 47 nF C0G ±5 % | Murata GRM31M5C1H473JA01L (1206) | C21812 | 66 867 | 2 | Rework to ±1 % later (E-5): TORCH CC1206CG50V473FN (C54916732) |
| C_fb 22 nF C0G ±5 % | Murata GRM21B5C1H223JA01L (0805) | C77069 | 62 750 | 2 | Rework to ±1 %: Murata GCM21B5C1H223FA16L (C1864305) |
| DC filter, output series | 10 kΩ / 1 µF, 100 Ω | — | — | 2 each | General purpose |

## C.6 Sensor, Drain Bias, Heaters (sheet Sensor)

All resistors in the drain path are thin film, 0.1 %, ±10 ppm/°C (AN-4a).

| Function | Part | LCSC | Stock | Qty | Notes |
|----------|------|------|-------|-----|-------|
| Pixel selection | TMUX1109RSVR | C2673348 | 209 | 2 | E-6 |
| R_D 330 kΩ | Yageo RT0603BRB07330KL (±10 ppm) | C860332 | 2194 | 2 | Matched pair from one reel |
| Drain supply op-amp | OPA2196IDGKR | C2057920 | 759 | 1 | Difference amplifier, both sides |
| R_F 10.0 kΩ | RESI PTFR0603B10K0N9 (±10 ppm) | C394535 | 231 492 | 2 | Same family as R_G (ratio k) |
| R_G 100 kΩ | RESI PTFR0603B100KN9 (±10 ppm) | C394537 | 91 075 | 2 | |
| Output filter 1 kΩ | RESI PTFR0603B1K00N9 (±10 ppm) | C394536 | 187 487 | 2 | In series with R_D; + 10 µF X7R to GND |
| R_CAL 18.0 kΩ | RESI PTFR0603B18K0N9 (±10 ppm) | C2692864 | 2749 | 2 | Calibration position |
| Drain-sense op-amp | OPA2196IDGKR | C2057920 | 759 | 1 | Gain 8, both sides |
| Drain-sense R_F 7.15 kΩ | RESI PTFR0402B7K15N9 (±10 ppm, 0402) | C2829140 | 2198 | 2 | Only ±10 ppm option is 0402 |
| Drain-sense R_G 1.02 kΩ | RESI PTFR0402B1K02N9 (±10 ppm, 0402) | C2693048 | 5392 | 2 | Same family as R_F |
| Drain-sense output RC | 10 kΩ + 1 µF | — | — | 2 | Also limits current into the NUCLEO ADC pin |
| Heater driver op-amp | OPA2196IDGKR | C2057920 | 759 | 1 | On +5VP |
| Heater gain resistors 49.9 kΩ 0.1 % | Yageo RT0603BRD0749K9L | C705780 | 209 908 | 4 | Replaces the non-standard 50 kΩ of LIA-Readout; gain stays exactly 2 |
| Heater shunt 15 Ω 0.1 % | Yageo RT0603BRD0715RL | C705727 | 11 292 | 2 | |
| Heater current sense | INA190A1IDDFR | C1852068 | 3438 | 2 | VS = NUCLEO 3.3 V, so the output cannot exceed the ADC range; output RC 1 kΩ / 100 nF |
| Dummy heater 1.00 kΩ 0.1 % | Yageo RT0805BRD071KL (0805, 0.125 W) | C110774 | 328 710 | 2 | Calibration position, bank B |

## C.7 Front End (sheet Front_End)

| Function | Part | LCSC | Stock | Qty | Notes |
|----------|------|------|-------|-----|-------|
| In-amp | INA828IDR | C544342 | 6997 | 1 | G = 10 (AN-8) |
| R_G 5.62 kΩ 0.1 % | Yageo RT0603BRD075K62L | C705789 | 19 143 | 1 | G = 9.90 |
| Band-pass op-amp | OPA2196IDGKR | C2057920 | 759 | 1 | HPF + LPF |
| Band-pass R 9.31 kΩ 0.1 % | Viking ARG03BTC9311 | C2686441 | 4800 | 4 | |
| Band-pass gain resistors 10.0 kΩ 0.1 % | RESI PTFR0603B10K0N9 | C394535 | 231 492 | 4 | K = 2 |
| Band-pass C 33 nF C0G ±5 % | TDK C2012C0G1H333JT000N (0805) | C76628 | 30 312 | 4 | No ±1 % 33 nF C0G is in stock anywhere at LCSC (all 0 on 2026-10-29). Rework later (E-5) |

## C.8 Demodulator (sheet DEMODULATOR, used twice)

Parts per instance. One TMUX6136 per channel, the second switch of the chip is unused (E-7).

| Function | Part | LCSC | Stock | Qty per sheet | Notes |
|----------|------|------|-------|---------------|-------|
| Switch | TMUX6136PWR | C2673380 | 145 | 1 | Supply per DC-3 |
| Op-amp | OPA2196IDGKR | C2057920 | 759 | 1 | Section A: ±1 demodulator; section B: post-filter |
| R_i, R_f 10.0 kΩ 0.1 % | RESI PTFR0603B10K0N9 | C394535 | 231 492 | 2 | Gain ±1 |
| Post-filter R_IN 200 kΩ 0.1 % | Yageo RT0603BRD07200KL | C728585 | 229 605 | 1 | |
| Post-filter R_F 301 kΩ 0.1 % | Yageo RT0603BRD07301KL | C861309 | 12 527 | 1 | Same family as R_IN |
| Post-filter C_F 1.5 µF film ±20 % | Rubycon 16MU155MA23216 (1206, acrylic) | C3776792 | 1813 | 1 | τ = 0.45 s instead of 0.50 s; a parallel footprint (DNP) for 150 nF restores 1.65 µF at rework |
| +IN divider (VMID/2.5) | As LIA-Readout §4.9 FE-B | — | — | — | VMID divider from +5VA on the Front_End sheet |
| Output series | 100 Ω | — | — | 1 | To SMA and header |

## C.9 General Parts

Decoupling (100 nF X7R 0603 at every supply pin, 10 µF X7R per rail and sheet), pull-downs and non-critical resistors are JLCPCB basic parts, chosen at schematic entry.
