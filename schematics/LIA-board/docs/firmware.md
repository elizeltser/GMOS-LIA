# GMOS LIA Board — Firmware

Implementation specification for the STM32U575 firmware, written so that Claude Code (or a person) can generate and extend the code from an STM32CubeMX project. Requirements: [requirements.md R.4](requirements.md#r4-firmware) (FW-x). Principles: [measurement_principles.md §2.12](measurement_principles.md#212-excitation-and-reference-generation). Hardware: [schematic_overview.md §5](schematic_overview.md#5-digital-section).

**Status:** F.1–F.9 specify the excitation and reference module (FW-1…FW-10) in detail. Other modules (FW-11…FW-16) are outlined in F.10 and will be detailed later.

**Verification tags.** `VERIFY-CUBEMX` = confirm in STM32CubeMX for STM32U575RGTx before generating code (pin alternate functions, internal trigger names). `VERIFY-RM` = confirm in RM0456 / DS13737. Claude Code must not hard-code a value marked with a tag without confirming it from the generated code or the reference manual.

---

## F.1 Scope and Assumptions

- Toolchain: STM32CubeMX (STM32CubeU5 package), STM32CubeIDE or CMake + arm-none-eabi-gcc. Code generated with **HAL** drivers; LL may be used in user code for register-level timer setup.
- All application code goes into `USER CODE BEGIN/END` sections or separate files under `Core/Src/app/`, `Core/Inc/app/`, so CubeMX regeneration does not overwrite it.
- Clocks: 16 MHz external CMOS oscillator on PH0, HSE in **bypass, digital mode** (`VERIFY-CUBEMX`: RCC "HSE: Crystal/Ceramic Resonator" vs "BYPASS Clock Source"; on U5 the digital-bypass option corresponds to the HSEEXT bit, LL constant `LL_RCC_HSE_DIGITAL_MODE`). PLL1 → SYSCLK = 160 MHz, AHB/APB1/APB2 prescalers = 1 → **timer kernel clocks = 160 MHz** (f_TIM). Voltage scaling range 1.

## F.2 CubeMX Configuration

### F.2.1 Pin and Trigger Verification Gate (do first)

Before generating code, open the `.ioc` in CubeMX and confirm, recording the result in this section and in the commit message. Without the GUI, the same data is in the local CubeMX install: the MCU file `db/mcu/STM32U575R(G-I)Tx.xml` (pin list, signals) and the GPIO IP file `db/mcu/IP/GPIO-STM32U5*_Modes.xml` (alternate-function numbers) — Claude Code can `grep` these. The timer internal-trigger names (ITRx ↔ source timer) are shown in CubeMX's TIM2 "Slave Mode Controller → Trigger Source" list and in RM0456 (TIMx internal trigger connection tables).

| Item | Expected | Fallback if not available |
|------|----------|---------------------------|
| DAC1_OUT1 / DAC1_OUT2 | PA4 / PA5 | — (fixed by silicon) |
| Reference timer outputs | TIM8_CH1 on PC6, TIM8_CH2 on PC7 (`VERIFY-CUBEMX`; expected AF3 as on STM32L4/L5; a third-party U5 summary claims AF1 for TIM8 channels — CubeMX decides) | Another timer with two output-compare channels on free pins (e.g. TIM3_CH1/CH2), same method; or DMA-to-GPIO (F.9) |
| Sample timer slave input from the reference timer | TIM2 slave mode **Trigger**, trigger source = the ITRx entry CubeMX labels with **TIM8** (`VERIFY-CUBEMX`) | Make the sample timer the master (TIM8 slave of TIM2, ITRx labelled TIM2), or use TIM15/TIM1 as sample timer if it offers a TIM8 trigger input; last resort F.9 |
| DAC trigger | `DAC_TRIGGER_T2_TRGO` exists for DAC1 (confirmed in the U5 HAL header) | `DAC_TRIGGER_T8_TRGO`, `T15`, `T1`, `T4`–`T7` also exist |
| SPI clock pin | **PA1 as SPI1_SCK is unconfirmed.** Sibling families (STM32L4+/L5) have SPI1_SCK on PA1 (AF5); the only STM32U5 pinout reachable during research (third-party, incomplete: it also omits PC6/PC7) lists SPI1_SCK on PA5/PB3 only. Three research attempts could not reach DS13737 | If PA1 is not SPI1_SCK: PA5 is taken (DAC1_OUT2) → use PB3 (SPI1_SCK) with PA6/PA7 (SPI1 pins can be mixed), `VERIFY-CUBEMX`; **this changes the schematic** |
| USART2 | PA2 TX, PA3 RX | — |
| I²C1 | PB6 SCL, PB7 SDA | — |
| ADC1 inputs | PC0–PC3 = ADC1_IN1…IN4 | — |

### F.2.2 Peripheral Settings (excitation module)

**DAC1 channel 1 (PA4, EXC_DAC)**

| Setting | Value |
|---------|-------|
| Mode | Normal mode, connected to external pin only |
| Output buffer | Enabled |
| Sample and hold | Disabled |
| Trigger | Timer 2 Trigger Out event (`DAC_TRIGGER_T2_TRGO`) |
| High frequency interface mode | **Automatic** or "Above 80 MHz" (`DAC_HIGH_FREQUENCY_INTERFACE_MODE_ABOVE_80MHZ` / `_AUTOMATIC`); required because HCLK = 160 MHz |
| User trimming | Factory |
| DMA | GPDMA1 channel, request DAC1_CH1, memory → peripheral, **linked-list mode, circular** |
| Data alignment | 12-bit right (DHR12R1) |

**DAC1 channel 2 (PA5, CAL_DAC, optional FW-9):** same settings, same trigger (T2_TRGO), own GPDMA channel; leave disabled if the calibration tone is not fitted.

**GPDMA1 channel for DAC1 CH1**

| Setting | Value |
|---------|-------|
| Mode | Linked-list, **circular** (queue with one node that links to itself; `HAL_DMAEx_List_SetCircularMode`) |
| Direction | Memory to peripheral |
| Source | `exc_table[]`, increment on, **half-word** |
| Destination | DAC1->DHR12R1, increment off, **word** (U5 pitfall: DAC DMA destination must be word-sized; source may stay half-word — reported on the ST community for STM32U5) |
| Request | DAC1_CH1 |
| Priority | High |

**TIM2 (sample timer, 32-bit)**

| Setting | Value |
|---------|-------|
| Clock source | Internal (160 MHz) |
| Prescaler | 0 |
| Counter period (ARR) | 2412 (default; computed at run time, F.3) |
| Auto-reload preload | Enable |
| Slave mode | **Trigger mode**, trigger source = ITRx labelled TIM8 (`VERIFY-CUBEMX`) |
| Master output (TRGO) | Update event |
| Channels | None |

**TIM8 (reference timer, 16-bit, master)**

| Setting | Value |
|---------|-------|
| Clock source | Internal (160 MHz) |
| Prescaler | 3 |
| Counter period (ARR) | 38607 (default; = 16·(ARR_TIM2 + 1) − 1) |
| Auto-reload preload | Enable |
| Channel 1 | Output Compare CH1, mode **Toggle on match**, pulse (CCR1) = 0, polarity high, output pin PC6 (REF_X) |
| Channel 2 | Output Compare CH2, mode **Toggle on match**, pulse (CCR2) = 19304 (= (ARR + 1)/2), polarity high, pin PC7 (REF_Y) |
| Master output (TRGO) | **Enable** (counter enable starts TIM2) |
| Master/slave mode | Enable (MSM bit) so TIM8 waits for its own slave sync — recommended for exact simultaneity |
| Break / dead time | Disabled; **MOE must be set** for TIM8 outputs (`HAL_TIM_OC_Start` sets it on advanced timers in the L4 HAL; verify in `stm32u5xx_hal_tim.c`, else call `__HAL_TIM_MOE_ENABLE`) |
| GPIO | Push-pull, speed low (edges ≈ ns are not needed; lower speed reduces coupling into the analog section), initial state low |

### F.2.3 Other Peripherals (outline)

| Peripheral | Use | Settings |
|------------|-----|----------|
| SPI (instance per F.2.1) | DAC80508 (mode 1), ADS1220 (mode 1) | 8-bit, ≤ 4 MHz, software NSS (3 GPIO CS) |
| USART2 | PC link via ISO6721 | 921 600 baud 8N1, DMA RX circular + idle line, DMA TX |
| I²C1 | STUSB4500, TMP117, SHT40 | 100/400 kHz |
| ADC1 | PC0 IHTR_A, PC1 IHTR_B, PC2 DSENSE_A, PC3 DSENSE_B | 14-bit, scan, oversampling ×16, triggered at ≈ 1 kHz, DMA |
| GPIO | ch_sel_0…3, mux_en (out, low at reset), DAC_CS/ADC_CS (out, high), ADC_DRDY (EXTI falling) | |

## F.3 Timing Math

| Quantity | Formula | Default |
|----------|---------|---------|
| Samples per period | N = 128 (power of 2; table index wraps with `& (N−1)`) | 128 |
| Sample timer | ARR_s = round(f_TIM/(N·f₀)) − 1 | 2412 |
| Actual frequency | f₀ = f_TIM/(N·(ARR_s + 1)) | 518.03 Hz |
| Reference timer | PSC_r = 3, ARR_r = (N/2)·(ARR_s + 1)/(PSC_r + 1) − 1 = 16·(ARR_s + 1) − 1 | 38607 |
| Reference CCR | CCR1 = 0, CCR2 = (ARR_r + 1)/2 | 0, 19304 |
| Range | ARR_s ≤ 4095 keeps ARR_r ≤ 65535 → f₀ ≥ 305 Hz; upper limit by band-pass ≈ 700 Hz | |
| Resolution | Δf ≈ f₀/(ARR_s + 1) | ≈ 0.21 Hz at 518 Hz |

The identity (ARR_r + 1)(PSC_r + 1) = (N/2)(ARR_s + 1) must hold **exactly** (integer arithmetic, assert it). In toggle mode a channel output changes once per reference-timer period, so the reference period is 2·(ARR_r + 1)·(PSC_r + 1)/f_TIM = N/f_s, and CH2 toggles half a timer period (= N/4 samples, 90°) after CH1 (`VERIFY-RM`: toggle-mode behaviour; confirm on the scope, F.8).

$$
f_0 = \frac{f_{\mathrm{TIM}}}{N\,(ARR_s+1)}, \qquad (ARR_r+1)(PSC_r+1) = \frac{N}{2}\,(ARR_s+1)
$$

```latex
f_0 = \frac{f_{\mathrm{TIM}}}{N\,(ARR_s+1)}, \qquad (ARR_r+1)(PSC_r+1) = \frac{N}{2}\,(ARR_s+1)
```

**Sine table.** `uint16_t exc_table[N]` (aligned to 4 bytes, placed in SRAM reachable by GPDMA1):

$$
\mathrm{code}[n] = \mathrm{round}\!\left(C_0 + A\,\sin\!\left(\frac{2\pi\,((n + n_\phi) \bmod N)}{N}\right)\right), \qquad A = \frac{4095}{V_{DDA}}\cdot\frac{120\cdot V_{gate,pp}}{2}
$$

```latex
\mathrm{code}[n] = \mathrm{round}\!\left(C_0 + A\,\sin\!\left(\frac{2\pi\,((n + n_\phi) \bmod N)}{N}\right)\right), \qquad A = \frac{4095}{V_{DDA}}\cdot\frac{120\cdot V_{gate,pp}}{2}
```

with C₀ = 2048 (mid-scale ≈ 1.65 V), n_φ the phase index (FW-6). Clamp so that every code lies within the DAC buffer's linear output range (`VERIFY-RM`, DS13737 DAC characteristics; until verified, keep codes within 250…3845, i.e. ≈ 0.2–3.1 V). Default gate 5 mVpp → DAC 0.6 Vpp → A ≈ 372 codes. Maximum 20 mVpp → 2.4 Vpp → A ≈ 1489 codes (within the clamp).

The gate DC level depends on C₀ through the MFB stage (V_G = 1.0083·V_DC − V_EXC,DC/120); the gate-DC firmware ([§4.5](schematic_overview.md#45-excitation-sheet-analogexcitation)) uses the actual C₀·V_DDA/4095.

## F.4 Module Design

Files: `Core/Inc/app/exc.h`, `Core/Src/app/exc.c`, host-testable math in `Core/Src/app/exc_math.c` (no HAL includes).

```c
/* exc.h */
typedef struct {
    float    f_req_hz;      /* requested frequency            */
    float    f_act_hz;      /* actual frequency after rounding */
    float    gate_vpp;      /* gate amplitude, V peak-peak     */
    uint8_t  phase_idx;     /* 0..N-1, 360/N deg per step      */
    uint32_t arr_s, arr_r, psc_r, ccr2;
    bool     running;
    bool     tone_on;       /* DAC1 CH2 calibration tone       */
    float    tone_vpp;
} exc_cfg_t;

HAL_StatusTypeDef exc_init(void);                     /* links handles, builds default table */
HAL_StatusTypeDef exc_start(void);                    /* FW-7 start sequence                  */
HAL_StatusTypeDef exc_stop(void);                     /* DAC to mid-scale, refs low           */
HAL_StatusTypeDef exc_set_frequency(float f_hz);      /* FW-4, FW-8: stop, reconfigure, start */
HAL_StatusTypeDef exc_set_amplitude(float gate_vpp);  /* FW-5                                 */
HAL_StatusTypeDef exc_set_phase(uint8_t idx);         /* FW-6                                 */
HAL_StatusTypeDef exc_set_tone(bool on, float vpp);   /* FW-9                                 */
const exc_cfg_t  *exc_get_cfg(void);                  /* FW-10 reporting                      */

/* exc_math.h (pure functions, unit-tested on the host) */
uint32_t exc_calc_arr_s(float f_tim, uint32_t n, float f_hz);
float    exc_actual_freq(float f_tim, uint32_t n, uint32_t arr_s);
void     exc_calc_ref(uint32_t n, uint32_t arr_s, uint32_t *psc_r, uint32_t *arr_r, uint32_t *ccr2);
void     exc_build_table(uint16_t *tab, uint32_t n, float vdda, float gate_vpp,
                         uint8_t phase_idx, uint16_t c0, uint16_t lo, uint16_t hi);
```

State machine: `STOPPED → (exc_start) → RUNNING → (exc_stop) → STOPPED`. All `set_*` functions that change timing or the table call `exc_stop()` first and `exc_start()` afterwards if the module was running, then raise a "settling" flag consumed by the acquisition module (X/Y invalid for 3.5 s, FW-8).

## F.5 Start / Stop Sequences

**exc_start()** (FW-3, FW-7):

1. Preconditions: rails good, VDDA valid, gate DC DAC channels written, `exc_table` built.
2. Make sure both timers are disabled and counters are zero: `__HAL_TIM_DISABLE`, `__HAL_TIM_SET_COUNTER(&htim2, 0)`, `__HAL_TIM_SET_COUNTER(&htim8, 0)`.
3. Write ARR/PSC/CCR from `exc_cfg_t`; generate an update event (`EGR.UG`) on both timers so the preloaded values take effect, then clear the update flags.
4. Start DAC1 CH1 with DMA in circular linked-list mode (`HAL_DAC_Start_DMA` with the linked-list queue linked to the DMA handle as generated by CubeMX; if CubeMX generates a standard-mode channel, rebuild with `HAL_DMAEx_List_*` and start with `HAL_DMAEx_List_Start`, since plain `HAL_DMA_Start` does not run the circular list on U5). The DAC outputs `exc_table[0]` on the first trigger.
5. Arm TIM2 (`HAL_TIM_Base_Start(&htim2)`): in trigger slave mode it does not count until TIM8 starts.
6. Configure TIM8 CH1/CH2 forced inactive, then toggle mode (so both references start low), enable the outputs (`HAL_TIM_OC_Start` for CH1 and CH2; MOE set).
7. Start TIM8 counter (`__HAL_TIM_ENABLE(&htim8)`): its TRGO (enable) starts TIM2 in the same clock cycle → sample 0 and the first reference edge coincide.

**exc_stop():** disable TIM8 counter, disable TIM2 counter, stop the DMA (`HAL_DAC_Stop_DMA`), write DHR12R1 = C₀ (gate returns to its DC level), force both TIM8 outputs inactive (low).

## F.6 Frequency, Amplitude, Phase, Tone

- **Frequency** (`exc_set_frequency`): compute ARR_s, ARR_r, PSC_r, CCR2 with `exc_math`; reject f₀ outside 305–700 Hz; stop → write → start; report f_act.
- **Amplitude** (`exc_set_amplitude`): rebuild the table into `exc_table` while stopped (simple, preferred), or into a second buffer and switch the linked-list node at the DMA transfer-complete interrupt (period boundary) for glitch-free updates while running.
- **Phase** (`exc_set_phase`): rebuild the table with the new n_φ (rotates the sine relative to the references by 360°/N per step).
- **Tone** (`exc_set_tone`, FW-9): DAC1 CH2 uses the same TIM2 trigger and its own table (same N, independent amplitude, centred at mid-scale); started/stopped together with CH1.

## F.7 UART Commands (excitation subset, FW-10)

| Command | Action / reply |
|---------|----------------|
| `EXC?` | `EXC f_req f_act gate_vpp phase_idx running tone_on tone_vpp` |
| `EXC FREQ <Hz>` | Set frequency, reply with f_act |
| `EXC AMP <mVpp>` | Set gate amplitude (0.5–20) |
| `EXC PHASE <0..127>` | Set phase index |
| `EXC RUN` / `EXC STOP` | Start / stop |
| `EXC TONE <on/off> <mVpp>` | Calibration tone |
| `EXC REGS?` | Dump TIM2 ARR, TIM8 PSC/ARR/CCR1/CCR2, DMA status, DAC CR (for verification) |

## F.8 Verification (bench, LAB-4)

1. `EXC REGS?` matches F.3 for 518, 305, 700 Hz.
2. Scope CH1 = PA4 (DAC), CH2 = PC6, CH3 = PC7: sine period = reference period; PC7 lags PC6 by 90.0° ± 0.1°; PC6 rising edge at the sine's upward zero crossing (± one sample, 2.8°).
3. Frequency counter on PC6: f_act ± 50 ppm.
4. Run for 1 h: no drift between the sine and PC6 (persistence mode).
5. Gate nets (after U1): 5.00 mVpp ± 1 %, THD ≤ 0.3 % (scope FFT or SR860).
6. Change frequency/amplitude/phase 100 times via UART: no lock-up, references always coherent.
7. Host unit tests for `exc_math` (ARR rounding, the integer identity, table clamping, phase rotation).

## F.9 Fallback: References by DMA to GPIO

If no usable ITR connection exists between the sample timer and a timer with two output pins on free pins, generate the references from the **same** sample-timer event with a second GPDMA channel writing a 128-entry pattern to `GPIOx->BSRR` (bit set/reset words for the two reference pins), triggered by the TIM2 update request. Both DMA channels are driven by one timer, so coherence is exact; jitter is a few bus cycles (tens of ns, ≈ 0.01° at 518 Hz). Pins can then be any free GPIO of one port.

## F.10 Other Modules (outline, FW-11…FW-16)

| Module | File | Content |
|--------|------|---------|
| DAC80508 driver | `dac80508.c` | SPI frames, gain/ref config, channel write, broadcast zero |
| Bias control | `bias.c` | Gate DC A/B (ch4/ch5), heaters (ch0/ch1), drain coarse/fine (ch2/3, ch6/7) with V_SUP = 1.1·V_c − 0.1·V_f |
| Pixel selection | `mux.c` | Sequence FW-12, settling flags |
| ADS1220 driver | `ads1220.c` | Config (AIN0−AIN1 / AIN2−AIN3, gain 1, PGA bypass, 20–1000 SPS, internal ref), DRDY ISR |
| Housekeeping ADC | `hk_adc.c` | PC0–PC3, oversampling, scaling to I_heater and V_drain |
| Protocol | `proto.c` | ASCII commands, binary frames, CRC-16 |
| Calibration | `cal.c` | Zero offset, dummy-load check, tone gain/phase, X/Y rotation and sign |