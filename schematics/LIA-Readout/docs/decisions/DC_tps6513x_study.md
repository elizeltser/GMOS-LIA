# DC Section Study: one TPS6513x instead of two LMR51430 (v3, 2026-10-28)

**Scope.** This study looks at replacing U15 (+7 V buck) and U18 (−7 V inverting buck-boost, IBB) with one dual-output converter. Both are LMR51430XFDDCR today. The LDOs stay as they are: ADP7118 ×4 (U14, U16, U17, and U22 on the isolated side) and LT3094. Board sources: [schematic_overview.md](../schematic_overview.md) §3 and §6, [requirements.md](../requirements.md) R.1 (DC-1…DC-7), [README.md](../README.md) §9.

**Conventions.** Open questions are numbered OQ-n. "Q1" always means the transistor designator. Prices are JLCPCB unit prices in USD checked on 2026-10-28, unless a distributor is named.

## 0. Part identity

TI makes no "TPS95131". The part that matches (one IC giving a positive and a negative rail) is the **TPS6513x** family (SLVS493E): a boost plus an inverting buck-boost in a VQFN-24 4×4 package. It comes in two versions with the same pinout and footprint:

| Part | Switch limit | JLC (LCSC, stock, price) | Mouser |
|------|--------------|--------------------------|--------|
| **TPS65130RGER** (proposed baseline) | 0.8 A | C54989, 9573 pcs, $1.98 | 3601 pcs, $4.17 |
| TPS65131RGER (drop-in alternate) | 2 A | C87663, 1941 pcs, $2.88 | 26 pcs, $4.68 |

The TPS65130 is enough here, and the lower limit means less peak current in the inductor and diode during start-up and faults. The check is in §1. Confirm with OQ-1.

## 1. Key facts and design numbers (SLVS493E)

| Item | Value | Consequence |
|------|-------|-------------|
| Input range | **2.7–5.5 V** recommended, 6 V abs max (VIN, INN) | It cannot run from `VIN` = 12 V (DC-1). It needs a 5 V source: USB-C at its default 5 V without PD, or a 5 V lab supply. It also needs input overvoltage protection (§2.1) |
| VPOS range | VIN + 0.5 V … 15 V | +7 V is fine. +6 V is exactly at the limit when VBUS = 5.5 V (OQ-7) |
| VNEG range | −2 … −15 V | −7 V is fine |
| Clock | **one oscillator shared by both outputs**: 1.25 / 1.38 / 1.50 MHz (min/typ/max), no SYNC input | The two rails cannot beat against each other |
| Power-save | PSP (boost) and PSN (inverter) LOW = PWM | Tie **PSP = PSN = GND** (DC-7) |
| Inverter at light load | goes **DCM** even with PSN = GND. Minimum duty 12.5 % | Needs a minimum load. See the calculation below |
| Rectifiers | 2 external Schottky diodes | Reuse **B5819W** (40 V, 1 A), already on the BOM as D1/D2/D4/D7 |
| Load disconnect | BSW drives an optional PMOS that sits in the boost path only | Reuse **AO3407A**. It does not limit inrush into the VIN/INN/INP capacitors (§2.1) |
| Inductors | 3.3–6.8 µH recommended | 2 × 4.7 µH FNR4030S4R7MT (C167874, 162k pcs, $0.05, Isat 3.2 A) |
| Divider | VPOS = 1.213 V·(1 + R1/R2). VNEG = −1.213 V·R3/R4, with R4 returned to VREF | Example: R1 = 1 MΩ with R2 = 210 kΩ gives +6.99 V. R3 = 1 MΩ with R4 = 174 kΩ gives −6.97 V |
| Enable pins | recommended ≤ 5.5 V, abs max VIN + 0.3 V | Tie ENP/ENN to VIN through 10 kΩ, or drive them from the current-class logic (OQ-4) |

**Load and input current.** The loads come from §6, FE-A, with 1.5× margin: +7 V = 21 + 44 + 69 = 134 mA and −7 V = 20 mA. Output power is 0.94 W on +7 V and 0.14 W on −7 V. I assumed efficiencies of 0.85 for the boost and 0.65 for the inverter, because the inverter runs in DCM with forced PWM. That gives P_in ≈ 1.11 + 0.22 = **1.32 W, which is 0.26 A at 5.0 V and 0.30 A at 4.4 V**. If the 300 Ω heaters are confirmed (README §9.2 item 2), +5VP goes from 21 to 42 mA and the input becomes 0.30 A at 5.0 V and 0.34 A at 4.4 V.

**Switch-limit check for the TPS65130.** The TPS65130 switch limit is 0.7 / 0.8 / 0.9 A (min/typ/max) for both switches (SLVS493E). The worst-case boost input current is about 0.34 A plus half the ripple. At nominal values the ripple is ΔI = V_in·D/(L·f) = 4.4·0.37/(4.7 µH·1.38 MHz) ≈ 0.25 A, so the peak is about 0.47 A. At the tolerance corner (L − 20 %, f = 1.25 MHz) ΔI ≈ 0.35 A and the peak is about 0.51 A. Both are below the 0.7 A minimum.

**Duty cycles.**
- Boost: D = 1 − V_in/V_out = 0.29 at 5.0 V and 0.37 at 4.4 V. The datasheet (§7.3.1) says the boost always runs in continuous current mode, because an internal switch lets current flow back to the input. So it has no light-load duty problem, and only the inverter goes DCM.
- Inverter, DCM: I_out = (D·V_in)² / (2·L·f·|V_out|), so D = √(2·L·f·|V_out|·I_out) / V_in. At 20 mA, D = 0.27. At the real FE-A load of about 13 mA, D = 0.22. D reaches the 12.5 % minimum at **I_out ≈ 4.3 mA (V_in = 5.0 V), or 5.2 mA at 5.5 V**, with nominal L and f. At the tolerance corner (L − 20 % = 3.76 µH, f = 1.25 MHz, V_in = 5.5 V) the threshold is (0.125·5.5)²/(2·3.76 µH·1.25 MHz·7 V) ≈ **7.2 mA**. Including the diode drop (|V_out| + V_f ≈ 7.4 V) and losses, it is about 5–7 mA. Below that the controller has to skip pulses, which can put sub-harmonic energy into 377–711 Hz and breaks DC-7. This happens in start-up while the op-amps are still unpowered, in standby, and with FE-B.
  - **Fix:** a **820 Ω preload** on −7 V (8.5 mA, 60 mW, 0805 rated 0.125 W). That covers the tolerance corner with margin. Using 6.8 µH instead of 4.7 µH only lowers the nominal threshold to 3.0 mA, so the preload is still needed.
  - **First-spin test:** FFT of −7 V and −5VA at minimum load (OQ-9).

## 2. Implementation paths

| Path | Input | Conversion | Change from P0 |
|------|-------|------------|----------------|
| **P0** (as drawn) | USB-C PD 12 V (STUSB4500, Q1, D7, D8) + lab 11–15 V (J4, D4) | LMR51430 buck → +7 V. LMR51430 IBB → −7 V | — |
| **P1** (the user's proposal) | USB-C **5 V, no PD**: 2 × 5.1 kΩ Rd on CC1/CC2, TVS on VBUS, a Schottky from VBUS to the OR node (the old D7 role), then the eFuse/OVP (§2.1). Optional 5 V lab input on J4 through its own Schottky into the same OR node | **TPS65130** → +7 V and −7 V, plus the 820 Ω preload | Removes STUSB4500, 2 × LMR51430 and Q1. D7 stays as the VBUS blocking diode. Adds TPS65130, 2 rectifier diodes, eFuse, TVS |
| **P2** | PD 12 V (as drawn) | one LMR51430 → +7 V. **LTC3260** inverting charge pump → −7 V, followed by the LT3094 | Removes U18 and L2. Adds LTC3260 |
| **P3** | External bench supply ±9 V on a 3-pole terminal block. No switcher on the board | LDOs only | Removes all PD and switcher parts |
| **P4** (hybrid) | P1, plus the P3 bench ±9 V input selected by 0 Ω links in front of the LDO inputs | P1 or P3 | P1 + terminal block + links |
| **P5** (new) | PD 12 V (as drawn) | one LMR51430 → +7 V. **Diode-capacitor charge pump on the buck SW node** → about −10.5 V unregulated at 20 mA → LT3094 → −5VA | Removes U18 and L2. Adds 2 × B5819W + 1 flying capacitor |
| P6 (not costed) | PD 12 V | two bucks with SYNC inputs, both clocked from one MCU timer | Parts not selected |

### 2.1 Input protection for P1 and P4 (needed for the 6 V abs max)

- **Overvoltage.** Hot-plug ringing on ceramic input capacitors can approach 2 × VBUS. A 9–12 V bench supply wired to J4 by mistake would destroy the TPS6513x. Its HBM ESD rating is ±1 kV.
- **Inrush.** A Type-C sink may show at most 10 µF of bulk capacitance on VBUS (cSnkBulk). The TPS6513x VIN, INN and INP capacitors alone are ≥ 9.4 µF. The BSW PMOS sits only in the boost path, so it cannot limit that inrush.
- **Fix:** put one **TPS2595x eFuse with the 5.7 V OVP clamp** (WSON-8 2×2, adjustable dV/dt and current limit, 20 V abs max) at the diode-OR node, ahead of **all** converter input capacitance.
  - **Back-feed (DC-1, Type-C sink rule).** Each input reaches the OR node through its own Schottky: VBUS through D7 (B5819W, kept from P0) and J4 through D4. A lab supply on J4 then cannot drive the USB connector's VBUS, and USB cannot drive J4. The TPS2595 cannot do this job itself, because it has no reverse blocking.
  - **TVS placement.** The TVS sits on the connector side of D7 (VBUS), so it sees only USB. A mis-wired 12 V bench supply on J4 meets only D4 and the eFuse, which clamps at 5.7 V and survives up to 20 V. No TVS conducts continuously.
  - **TVS choice.** SMAJ5.0A (C2925443, $0.04, JLC preferred) has V_RWM 5.0 V and leaks about 800 µA at 5 V, more near 5.5 V. Prefer an **SMAJ6.0A** or a 5.5–6 V USB TVS (OQ-5). Its clamp voltage (about 9–10 V) is above the TPS6513x's 6 V abs max. The eFuse and its downstream capacitors do the real protecting. The TVS only absorbs ESD and surge energy at the connector.
  - **Cost of the diodes.** The Schottky drop (about 0.3–0.4 V) leaves 4.6 V at 5.0 V VBUS and 4.0 V at the 4.4 V corner. Both are inside the 2.7–5.5 V range. The input current at 4.0 V rises to about 0.33 A, still within the 0.7 A minimum switch limit after the ripple.
    - JLC stocks TPS259540, 259541, 259570 and 259571 at $0.59–0.85. Which suffix has the 5.7 V clamp is still to be read from the datasheet's device-options table (OQ-5).
  - The eFuse also solves the inrush problem, and it makes the optional BSW PMOS unnecessary.
  - In an OVP event the clamp holds VIN at 5.7 V. That is above the 5.5 V recommended maximum but below the 6 V abs max. It is a fault state, not an operating point.

### 2.2 P5 in more detail

- **How it works.** Under FPWM the LMR51430 SW node swings 0 → VIN at 500 kHz at all loads. A series capacitor (1 µF, 25 V) and two B5819W diodes make an inverting pump of about −(VIN − 2·V_f).
  - At VIN = 12 V with V_f ≈ 0.35 V, the no-load value is −11.3 V. At 20 mA, subtracting an estimated 0.5–1 V drop across the pump's output impedance (to be measured, OQ-14), it is about **−10.5 V**.
  - Over VIN = 11–15 V it is about −10 to −14 V, inside the LT3094's 20 V input range.
  - LT3094 dissipation is about 6 V × 20 mA = 0.12 W. P0 dissipates 2 V × 20 mA, so the extra is about 0.08 W.
- **What it does well.** It has the same single clock as P1 and no IBB. It keeps DC-1, DC-2 (+7 V buck), DG-9 and the 11–15 V lab input.
- **Costs and risks.**
  - The −rail is unregulated and depends on the buck load.
  - The pump draws edge current from the SW node, so the buck output ripple must be re-checked.
  - The −rail exists only while the buck runs, so +7 V and −7 V start and stop together.
  - The pump ripple (about 100 mV pk-pk, to be verified) is rejected by the LT3094 PSRR, which is about 74 dB at 1 MHz and higher at 500 kHz.
- **Under FE-C** P5 reduces to P0 without U18.

### 2.3 P6 (single external clock)

Two bucks with a SYNC input, both clocked from one MCU timer, put every spur at a known frequency. That frequency can be placed away from k·f_MOD (§4) and from 377–711 Hz products. This also solves the beat problem while keeping the PD input. Part selection and costing have not been done (the LMR51430 has no SYNC pin), so P6 is not graded.

### 2.4 Effect of D-18

If **D-18 = FE-C** (single supply), the −7 V rail goes away:
- P0, P2 and P5 all become "PD + one buck".
- P1 becomes a 5 V boost: the TPS6513x with ENN = GND, or a single-output boost.
- The main advantage of the TPS6513x, one IC for two rails, disappears.

§6.2 gives the FE-C ranking.

## 3. Cost and availability

Everything below covers the power stage only, including the input connector protection and J4. The USB-C connector and the LDOs are common to all paths. LT3094 (C670494, 6128 pcs, $7.41) is in every FE-A/FE-B path.

"Extended types" counts each unique JLC extended part: ICs, inductors, and eFuse/TVS where not basic or preferred. Each one carries a $3 setup fee per order.

| Path | Main parts | Power-stage BOM | Extended types |
|------|------------|-----------------|----------------|
| P0 | STUSB4500QTR C2678061 (4838 pcs, $2.83; Mouser 13k); 2 × LMR51430XFDDCR C5219260 (7030 pcs, $1.22); 2 × 8.2 µH; Q1, D7, D8, J4 + D4, about 8 power caps | ≈ $6.4 | 3 (STUSB4500, LMR51430, inductor) |
| P1 | TPS65130 C54989 ($1.98); 2 × 4.7 µH ($0.05); 4 × B5819W (2 rectifiers, D7, D4); TPS2595x ($0.6–0.85); SMAJ6.0A-class TVS (≈ $0.04); 820 Ω preload; J4; about 12 caps | ≈ $3.9 | 3 (TPS65130, inductor, eFuse) |
| P2 | P0 minus one LMR51430 and one inductor, plus LTC3260EMSE#TRPBF C684387 (2446 pcs, $9.58) and its caps | ≈ $14.8 | 4 |
| P3 | 3-pole terminal block, 2 Schottky diodes, 2 TVS | ≈ $0.6 (the lab already has a bench supply) | 0–1 |
| P4 | P1 + P3 + 0 Ω links | ≈ $4.5 | 3 |
| P5 | P0 minus one LMR51430 and one inductor, plus 2 × B5819W and 1 cap | ≈ $5.2 | 3 |

An alternative negative LDO is the TPS7A3001 (C33835, 8161 pcs, $2.02, 15 µVrms against 0.8 µVrms for the LT3094). It is not proposed without a −5VA noise budget (OQ-12). In P2, using the LTC3260's own LDO instead of the LT3094 would bring the cost down to about +$2 over P0. Its LDO noise is tens of µVrms, though, so that option is not recommended.

## 4. Noise

Four mechanisms matter for a 377–711 Hz lock-in:

- **(a) Bursts or pulse skipping** that put energy into the band (DC-7).
- **(b) Beat between two free-running converters.** |f₁ − f₂| and the harmonic products n·f₁ − m·f₂ can land anywhere from 0 to about 110 kHz (the LMR51430 500 kHz option spans about 450–560 kHz). A beat reaches the band only through a nonlinearity: op-amp or in-amp RF rectification, LDO nonlinearity, or sampling by the ADS1220 or the MCU ADC/DAC. The risk is real, but it is not certain.
- **(c) Switching ripple that survives the LDOs** and reaches a sampler or a rectifying input.
- **(d) The input source and ground.** Charger noise matters here, and so does the PC ground: powering from a PC USB port, or a laptop PD port in P0, ties board GND to PC GND and bypasses the ISO6721 isolation (DG-4).

LDO PSRR, from the datasheets:
- ADP7118: 88 dB at 10 kHz, 68 dB at 100 kHz, 50 dB at 1 MHz (VIN 7 V, VOUT 5 V). At 450–560 kHz it is about 55 dB, interpolated from those points rather than read from the plot.
- LT3094: 74 dB at 1 MHz.

| Path | (a) | (b) | (c) | (d) | Mitigation effort | Noise grade |
|------|-----|-----|-----|-----|-------------------|-------------|
| P0 | FPWM ✓ | **two clocks, no SYNC pin** | about 55 dB at 500 kHz. The IBB has pulsating input **and** output current, and the IC ground sits at −7 V, so layout is critical | PD charger. PC ground if a laptop port is used | Medium-hard. The beat can only be filtered, not designed out | **B−** |
| P1 | PSP = PSN = GND ✓. Inverter DCM needs the preload (§1) | none between the converters (one clock) | 1.38 MHz is 2.8× higher than 500 kHz, so an LC post-filter for the same attenuation is 8× smaller. The inverter is still a buck-boost with pulsating currents, but its IC ground stays at GND | A 5 V charger has more absolute ripple than PD 12 V. LDO PSRR at 100/120 Hz is about 90 dB. PC-ground risk is the same as P0 | Easy-medium | **B+** |
| P2 | LTC3260 MODE must select the fixed 500 kHz clock (no Burst Mode) | two clocks. The LTC3260 RT pin can move its frequency away from the buck and from k·f_MOD | no inductor on the −rail, low ripple | as P0 | Medium | **B** |
| P3 | none | none | only the bench supply's mains ripple, ≥ 90 dB PSRR at 100 Hz | bench supply is usually floating | Trivial | **A** |
| P4 | stand-alone: as P1 | as P1 | as P1 | as P1 | The bench bypass allows an A/B noise measurement on the first spin, and A-grade noise on the bench | **B+** stand-alone (A on the bench) |
| P5 | FPWM ✓ (the pump relies on it) | **none (one clock)** | +7 V as P0 (about 55 dB). −rail: pump ripple × LT3094 (> 74 dB) | as P0 | Easy-medium | **B+** |

**Post-filter (P1, P4).** A ferrite bead has only about 1 µH and little loss at 1 MHz. With 10 µF it resonates near 50 kHz with high Q. Use a 2.2 µH inductor with 10 µF instead.
- The resonance is f_LC = 34 kHz (ideal 64 dB at 1.38 MHz).
- Realistically, a 10 µF ceramic loses about half its capacitance to DC bias at 7 V, and capacitor ESL limits the high-frequency attenuation, so expect about **45–55 dB**. Use a 25 V X7R 1206 to keep the DC-bias loss down.
- Damp it with **0.47 Ω + 22 µF** across the output. Z₀ = √(L/C) is 0.47 Ω at the nominal 10 µF. At about 5 µF effective (DC bias) it is 0.66 Ω, and f_LC ≈ 48 kHz. Middlebrook's optimum for n = C_d/C ≈ 2.2 is R ≈ 0.86·Z₀. That gives 0.40 Ω at nominal values and 0.57 Ω when both capacitors lose half their value, so 0.47 Ω sits between the two cases.
- Take the converter feedback before the LC.
- Check that f_LC is not near a converter beat or the P5 pump frequency (OQ-10).

**Aliasing (P0, P1, P5).**
- The ADS1220 modulator runs at f_MOD = 256 kHz in normal mode and 512 kHz in turbo mode. Its internal 4.096 MHz oscillator has roughly ±2 % tolerance (not verified here). The TPS6513x range of 1.25–1.50 MHz contains 5 × 256 kHz = 1.28 MHz. The LMR51430 at about 500 kHz is near 2 × 256 kHz.
- A converter near a multiple of f_MOD aliases to near DC.
- The inputs X_OUT/Y_OUT sit behind 100 Ω + 10 nF (T07) and carry very little ripple. The likelier path is the AVDD (+5VA) supply rejection. Neither is verified (OQ-13).
- P6 avoids the problem by placing the clock away from k·f_MOD.

## 5. Board area

The estimate is the component courtyard plus 0.5 mm spacing, on one basis for all paths: power stage, input protection, and the lab terminal (J4) where the path has one. USB-C connector and LDOs are excluded.

| Path | Parts | Estimate | Area grade |
|------|-------|----------|------------|
| P0 | PD block: STUSB4500 QFN-24 + 12 passives + Q1/D7/D8 (≈ 220 mm²). 2 × (SOT-23-6 + 4×4 inductor + 4 caps + divider) (≈ 220). J4 2-pole 5.08 mm + D4 (≈ 105) | ≈ 545 mm² | C+ |
| P1 | TPS65130 + 2 × 4×4 inductors + 2 SOD-123 + ≈ 12 caps + 5 R + preload (≈ 230). eFuse + 3 passives + SMA TVS + D7 SOD-123 (≈ 50). J4 + diode (≈ 105) | ≈ 385 mm² (≈ 280 without J4) | B+ |
| P2 | PD 220 + buck 110 + LTC3260 MSOP-16 with 6 caps (≈ 70) + J4 105 | ≈ 505 mm² | B− |
| P3 | 3-pole terminal block + 2 diodes + 2 TVS | ≈ 165 mm² | A |
| P4 | P1 without J4 (280) + P3 (165) + 3 links (≈ 10) | ≈ 455 mm² | B |
| P5 | PD 220 + buck 110 + pump (2 SOD-123 + 1 × 0805, ≈ 25) + J4 105 | ≈ 460 mm² | B |

Area grade bands: A ≤ 200 mm², A− ≤ 300, B+ ≤ 400, B ≤ 475, B− ≤ 525, C+ ≤ 600.

## 6. Grades

### 6.1 FE-A / FE-B (±5 V)

The overall grade uses the user's three criteria: **noise 50 %, availability & cost 25 %, board area 25 %**. Points: A = 4.0, A− = 3.7, B+ = 3.3, B = 3.0, B− = 2.7, C+ = 2.3, C = 2.0. Bands: A ≥ 3.85, A− ≥ 3.5, B+ ≥ 3.15, B ≥ 2.85, B− ≥ 2.5.

The availability & cost grade uses the power-stage BOM, with stock as a tie-break: A ≤ $1, A− ≤ $4.5, B+ ≤ $5.5, B ≤ $7, B− ≤ $10, C > $10. It drops one step if a main IC has fewer than 500 pcs at two distributors.

"Requirement fit" is not part of the score. It is shown separately because it is a decision, not a quality.

| Path | Availability & cost | Noise & mitigation | Area | Score | Overall | Requirement fit |
|------|---------------------|--------------------|------|-------|---------|-----------------|
| P0 (as drawn) | B (≈ $6.4, all deep stock) | B− | C+ | 2.68 | **B−** | A: meets DC-1, DC-2, DG-9 |
| **P1** (TPS65130, USB 5 V) | A− (≈ $3.9, TPS65130 deep stock at JLC and Mouser) | B+ | B+ | 3.40 | **B+** | C: changes DC-1, DC-2, DG-9, D-10, D-14, and needs a new input-protection / current-class requirement |
| P2 (PD + buck + LTC3260) | C (≈ $14.8) | B | B− | 2.68 | **B−** | A |
| P3 (bench ±9 V only) | A | A | A | 4.00 | **A**, lab-only | D: not stand-alone. Loses DC-1 and the USB input |
| P4 (P1 + bench bypass), stand-alone | A− (≈ $4.5) | B+ | B | 3.33 | **B+** | B: stand-alone on USB 5 V, A-grade noise on the bench |
| **P5** (PD + buck + SW-node pump) | B+ (≈ $5.2) | B+ | B | 3.23 | **B+** | A: no requirement change |

**Reading the table.**
- P1 and P5 score about the same. P1 wins on cost and area. P5 wins on requirement fit and keeps the 12 V source, which is cleaner.
- If the 5 V USB input is acceptable (OQ-3, OQ-4), take **P1 with TPS65130**. For the first spin, take **P4**, so the board can be measured once on its own converter and once on the bench supply.
- If the 12 V PD input must stay, take **P5**. It is the smallest change to the drawn schematic: delete **U18, L2, C37 (boot), C39, R35, R36** and add 2 diodes and 1 flying capacitor (1 µF, 25 V). This list was checked against the netlist. Keep C41 and C42: they sit on `-7V` and become the pump reservoir and LT3094 input capacitors. C38 is a VIN–GND bulk capacitor shared with U15, so it stays as well.
- P3 is the noise reference. It is not a stand-alone design.

### 6.2 FE-C (single supply, no −rail)

Rough estimate, on the §5 basis (J4 included):

| Path | Becomes | Cost | Noise | Area | Score | Overall |
|------|---------|------|-------|------|-------|---------|
| P0 / P2 / P5 | PD 12 V + one LMR51430 | B+ (≈ $5.0) | B+ (one clock, no IBB) | B (≈ 435 mm²) | 3.23 | **B+** |
| P1 | USB 5 V + TPS65130 (ENN = GND) or a single-output boost | A− (≈ $3.5) | B+ | B+ (≈ 330 mm²) | 3.40 | **B+**. The dual IC is not needed |
| P3 | bench +7…9 V into the LDOs | A | A | A | 4.00 | **A**, lab-only |

## 7. Open questions for the DC implementation

1. **OQ-1, part.** Did "TPS95131" mean the TPS6513x? Should the baseline be the TPS65130 (0.7 A min limit, 0.51 A worst-case peak, deep stock) with the TPS65131 as alternate? Decide before T03.
2. **OQ-2, D-18 first.** FE-A/B or FE-C? FE-C removes the −rail and most of the TPS6513x advantage (§2.4).
3. **OQ-3, requirement changes for P1/P4.**
   - DC-1: 12 V PDO, "must not start on 5 V", 11–15 V lab input.
   - DC-2: "+7 V buck", "IBB".
   - DG-9: PD configuration over I²C.
   - D-10 and D-14: SMAJ18A, the AO3407A role, the B5819W uses.
   - New: an input OVP/inrush requirement, and a requirement on the source current class (OQ-4).
   - All of these are in [requirements.md](../requirements.md) and [README.md](../README.md) §9.
4. **OQ-4, source current class.** The board never enumerates on USB: there are no data lines and the PC link is the FTDI UART. A Type-C port that advertises only "Default USB Power" therefore allows 100 mA (one unit load, USB 2.0), but the board draws 0.26–0.34 A. Options:
   - (a) Require a source that advertises 1.5 A or 3 A, or a dedicated charger or power bank, and label the connector.
   - (b) Sense the CC voltage with a comparator (vRd thresholds about 0.66 V and 1.23 V) and hold ENP/ENN low on a Default-only source.
   - (c) Leave it unchecked. Most chargers and power banks tolerate it, but a PC or hub port may limit or trip.
5. **OQ-5, input protection.** Which TPS2595x suffix has the 5.7 V OVP clamp (device-options table)? Choose the current limit (≈ 0.6 A) and the dV/dt capacitor so that inrush meets cSnkBulk / USB inrush. Check the **maximum** clamp voltage in the device-options table against the TPS6513x 6 V abs max. Put the eFuse after the D7/D4 OR node and ahead of **all** converter capacitors. TVS: SMAJ6.0A or a 5.5–6 V USB TVS on VBUS (connector side of D7).
6. **OQ-6, lab input.**
   - P1: keep J4 as a 5 V input through a Schottky diode (4.6 V at the TPS6513x, which is fine).
   - P4: a ±9 V bench bypass. Diode-OR at the LDO inputs would work: the bench +9 V would only push the boost into OVP shutdown, which is not a fault. Links are proposed instead because they are simpler: no OVP restart cycling, no diode drop, and a clear measurement state.
7. **OQ-7, rail voltages.** Keep ±7 V or go to ±6 V?
   - +3V3_D LDO dissipation is (7 − 3.3) V × 69 mA = 0.26 W at +7 V and 0.19 W at +6 V.
   - +6 V is exactly at the TPS6513x VPOS ≥ VIN + 0.5 V limit when VBUS = 5.5 V. Keep +7 V for P1 and P4.
   - Report: [schematic_overview.md](../schematic_overview.md) §3.3 gives +3V3_D = 0.31 W. That does not match (7 − 3.3) × 69 mA.
8. **OQ-8, sequencing.** ENP/ENN order. How the op-amps and the AD630 behave with one rail missing. LT3094 EN/PG. ADP7118 EN tied to its input.
9. **OQ-9, light-load behaviour.** Inverter minimum load (820 Ω preload) at the tolerance corner. First-spin FFT of −7 V, −5VA and +5VA from 0 to 2 kHz at minimum and nominal load.
10. **OQ-10, post-filter.** 2.2 µH + 10 µF (25 V X7R) + 0.47 Ω/22 µF damping after each TPS6513x output, with feedback taken before the filter. Confirm about 45–55 dB at 1.38 MHz by measurement.
11. **OQ-11, layout.** Keep the boost diode loop and the inverter hot loop at the input edge, away from DRN_A/B and the in-amp (AN-10, AN-23). Wide PGND under the IC.
12. **OQ-12, negative LDO.** Keep the LT3094 ($7.41, 0.8 µVrms) or use the TPS7A3001 ($2.02, 15 µVrms)? This needs the −5VA noise budget at f₀.
13. **OQ-13, aliasing.** Which ADS1220 mode (normal or turbo) and which clock (internal or external)? Converter ripple at AVDD and at AIN near k·f_MOD.
14. **OQ-14, P5 pump.** Measure the pump output impedance and ripple. Check that the pump's SW edge load does not raise the +7 V ripple beyond DC-3.
15. **OQ-15, optional optimisation in P1.** Run ADP7118-3.3 directly from the eFuse output instead of +7 V. That moves 69 mA off the boost. The load still comes from the 5 V input, now through the LDO (0.35 W instead of 0.57 W through the boost), so the input power drops by about 0.22 W (17 %): from 0.26 A to about 0.22 A at 5 V. It moves +3V3_D, and therefore VDDA (the DAC/ADC reference, D-D), onto the noisier 5 V input. The user asked to keep the other regulators unchanged, so this is not proposed.
16. **OQ-16, stock.** Buy spare TPS6513x and eFuses with the first order.

## 8. Documentation disagreements to report (not resolved here)

1. [design-context.md](../../../../simulations/design-context.md) §2 says "Single rail, 0 V to 5 V, for every part" and that the supply circuitry is not decided. The board docs keep ±5 V as the FE-A/FE-B options.
2. [schematic_overview.md](../schematic_overview.md) §3.3 gives the +3V3_D LDO dissipation as 0.31 W. (7 − 3.3) V × 69 mA = 0.26 W (OQ-7).
3. The schematic has four ADP7118s (U14, U16, U17, U22). §3.2 lists three. U22, the isolated-side 3.3 V LDO, is the adjustable part with SENSE tied to VOUT, so it would give about 1.2 V (netlist 2026-10-28: U22 value `ADP7118ACPZN` with no voltage suffix, U22.1 and U22.2 both on `/DC/3V3_iso`).
