# D-20 — MCU Pin and Trigger Verification (STM32U575RGT6)

Evidence from the local STM32CubeMX database, not from web pages. Answers the gate in [firmware.md §F.2.1](../firmware.md#f21-pin-and-trigger-verification-gate-do-first).

| Item | Value |
|------|-------|
| Tool | STM32CubeMX 6.16.1 (`/opt/STM32CubeMX`, from `.installationinformation`: `APP_VER 6.16.1`) |
| MCU file | `/opt/STM32CubeMX/db/mcu/STM32U575RGTx.xml` (DB file dated 2025-12-09, `DBVersion="V3.0"`, package LQFP64) |
| GPIO AF file | `/opt/STM32CubeMX/db/mcu/IP/GPIO-STM32U5x_gpio_v1_0_Modes.xml` (selected by the MCU file line 1081: `IP … Name="GPIO" Version="STM32U5x_gpio_v1_0"`) |
| Timer modes file | `/opt/STM32CubeMX/db/mcu/IP/TIM1_8U5-gptimer2_v4_x_Cube_Modes.xml` (TIM2 and TIM8 both use `TIM1_8U5 / gptimer2_v4_x_Cube`, MCU file lines 809, 875) |
| HAL / CMSIS | `~/STM32Cube/Repository/STM32Cube_FW_U5_V1.8.0/Drivers/` |
| Date | 2026-10-28 |

## Results

| # | Question | Answer | Evidence (file : line) | Status |
|---|----------|--------|------------------------|--------|
| 1 | Is PA1 SPI1_SCK? | **Yes, AF5.** PA1 (pin 15) lists `SPI1_SCK`; PA6 (pin 22) `SPI1_MISO` AF5, PA7 (pin 23) `SPI1_MOSI` AF5. The schematic as drawn (PA1/PA6/PA7) is valid; no move to PB3 is needed. (PB3 and PA5 are also SPI1_SCK AF5, for reference.) | MCU file `<Pin Name="PA1" Position="15">` … `Signal Name="SPI1_SCK"`; GPIO file l. 1593 `GPIO_AF5_SPI1` (PA1), l. 2194 (PA6), l. 2257 (PA7); PB3 l. 3039, PA5 l. 2122 | Verified |
| 2 | TIM8_CH1 on PC6, TIM8_CH2 on PC7: AF? | **AF3** (`GPIO_AF3_TIM8`) on both. The third-party "AF1" claim is wrong. TIM3_CH1/CH2 are also on PC6/PC7 at AF2 (fallback). | MCU file PC6 pos. 37, PC7 pos. 38 list `TIM8_CH1` / `TIM8_CH2`; GPIO file l. 4151 (PC6 TIM8_CH1 AF3), l. 4224 (PC7 TIM8_CH2 AF3), l. 4146 / 4219 (TIM3 AF2) | Verified |
| 3 | TIM2 internal trigger for TIM8 TRGO | **ITR5** (`TIM_TS_ITR5`, SMCR.TS = 0b01001). | Timer modes file l. 6650: `Mode Name="TriggerSource_ITR5" … RemoveCondition="($IpNumber=8)"`. CubeMX removes each ITRn from the timer that is its own source (ITR0 removed for TIM1, l. 6609; ITR1 for TIM2, l. 6617; ITR2 for TIM3; ITR3 for TIM4; ITR4 for TIM5; ITR5 for TIM8; ITR6 for TIM15). So ITR5 = TIM8. HAL `stm32u5xx_hal_tim.h` l. 1085 defines `TIM_TS_ITR5 = TS_0 \| TS_3`. | **Inferred from the DB pattern** (no explicit label in the DB). Confirm once in the CubeMX GUI (TIM2 → Slave Mode → Trigger Source list shows ITR5 with TIM8) or RM0456 table "TIMx internal trigger connection" |
| 4a | DAC1 trigger for TIM2_TRGO | **TSEL = 2** (`DAC_CR_TSEL1_1`); HAL `DAC_TRIGGER_T2_TRGO`, LL `LL_DAC_TRIG_EXT_TIM2_TRGO`. | `stm32u5xx_hal_dac.h` l. 216; `stm32u5xx_ll_dac.h` l. 291; `stm32u575xx.h` l. 5215/5219 (TSEL1 at bit 2, `TSEL1_1 = 0x2 << 2`) | Verified |
| 4b | PA4 = DAC1_OUT1, PA5 = DAC1_OUT2 | **Yes** (PA4 pin 20, PA5 pin 21). | MCU file `<Pin Name="PA4" Position="20">` `DAC1_OUT1`; `<Pin Name="PA5" Position="21">` `DAC1_OUT2` | Verified |
| 5 | USART2 PA2 TX / PA3 RX | **Yes, AF7** (`GPIO_AF7_USART2`) on both. | MCU file PA2 pos. 16 `USART2_TX`, PA3 pos. 17 `USART2_RX`; GPIO file l. 1974 (PA2), l. 2036 (PA3) | Verified |

## Consequences

- D-20 can be closed: **PA1 stays SPI1_SCK**, no schematic change for SPI.
- TIM8 references on PC6/PC7 with AF3 are confirmed; TIM2 slave trigger = ITR5 needs one click-check in the GUI before code is generated.
- The F.2.1 fallback rows (PB3 for SCK, TIM3 on PC6/PC7) remain valid as fallbacks.

## Reproduce

```bash
DB="<CubeMX install>/db/mcu"   # here: /opt/STM32CubeMX/db/mcu
grep -n -A25 '<Pin Name="PA1"' $DB/STM32U575RGTx.xml | sed '/<\/Pin>/q'
grep -n -B2 -A3 'PinSignal Name="TIM8_CH1"' $DB/IP/GPIO-STM32U5x_gpio_v1_0_Modes.xml
grep -n 'TriggerSource_ITR' $DB/IP/TIM1_8U5-gptimer2_v4_x_Cube_Modes.xml
```
