/* ad5696.h - Minimal AD5696 4-channel DAC driver
 *
 * Provides a small, blocking SPI-based driver that mirrors the public
 * API shape used by the MCP4725 driver (Init, WriteRaw, SetVoltage_mV,
 * Pulse, Read, Reset, ConnectivityTest). This implementation caches the
 * last written values for each channel and uses basic 24-bit SPI frames
 * (cmd/addr/data) common to many AD56xx family parts. Verify the exact
 * command encodings for your AD5696 variant and adjust the command
 * macros below if needed.
 */

#ifndef __AD5696_H
#define __AD5696_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f3xx_hal.h"

#define AD5696_DEFAULT_VREF_MV 2500U

/* Base 7-bit I2C address for AD5696 devices (top bits). Compute device
   address with AD5696_ADDR(A1,A0) where A1 and A0 are pin states (0/1). */
#ifndef AD5696_I2C_BASE
#define AD5696_I2C_BASE 0x44U
#endif
#define AD5696_ADDR(A1,A0) ((uint8_t)(AD5696_I2C_BASE | (((A1) & 1U) << 1) | ((A0) & 1U)))

/* Command codes (generic/typical) - adjust as needed for exact part */
#define AD5696_CMD_NOP          0x0U
#define AD5696_CMD_WRITE_UPDATE 0x3U
#define AD5696_CMD_SOFT_RESET   0x6U

/* 4 channels: 0..3 */
typedef struct {
  I2C_HandleTypeDef *hi2c; /* I2C peripheral used for transfers */
  uint8_t addr;            /* 7-bit I2C address */
  GPIO_TypeDef *reset_port; /* optional hardware reset pin (may be NULL) */
  uint16_t reset_pin;
  GPIO_TypeDef *ldac_port;  /* optional LDAC pin (may be NULL) */
  uint16_t ldac_pin;
  uint32_t vref_mv;        /* reference voltage in mV */
  uint16_t last_value[4];  /* cached last written 16-bit values */
} AD5696_HandleTypeDef;

/* Initialize driver instance (I2C handle, address, reset pin and LDAC pin may be provided).
   - `hi2c`: HAL I2C handle
   - `address`: 7-bit I2C address of the device
   - `reset_port`, `reset_pin`: optional hardware reset pin (pass NULL/0 to ignore)
   - `ldac_port`, `ldac_pin`: optional LDAC pin (pass NULL/0 to ignore)
*/
HAL_StatusTypeDef AD5696_Init(AD5696_HandleTypeDef *dev,
                              I2C_HandleTypeDef *hi2c,
                              uint8_t address,
                              GPIO_TypeDef *reset_port, uint16_t reset_pin,
                              GPIO_TypeDef *ldac_port, uint16_t ldac_pin);

/* Write raw 16-bit value (0..65535) to a single channel (0..3) */
HAL_StatusTypeDef AD5696_WriteRaw(AD5696_HandleTypeDef *dev, uint8_t channel, uint16_t value);

/* Set output by millivolts (converts to 16-bit with provided vref; default AD5696_DEFAULT_VREF_MV) */
HAL_StatusTypeDef AD5696_SetVoltage_mV(AD5696_HandleTypeDef *dev, uint8_t channel, uint32_t millivolts);

/* Produce a short blocking pulse on a channel: write `value`, wait `pulse_ms`, restore previous value */
HAL_StatusTypeDef AD5696_Pulse(AD5696_HandleTypeDef *dev, uint8_t channel, uint16_t value, uint32_t pulse_ms);

/* Read (cached) DAC value for channel */
HAL_StatusTypeDef AD5696_Read(AD5696_HandleTypeDef *dev, uint8_t channel, uint16_t *dac_value);

/* Soft reset (best-effort) */
HAL_StatusTypeDef AD5696_Reset(AD5696_HandleTypeDef *dev);

/* Connectivity test: returns 1 if the I2C is connected correctly, 0 otherwise */
int AD5696_ConnectivityTest(AD5696_HandleTypeDef *dev);

/* Quick demo helper (not called automatically) - can be used by tests */
void AD5696_Demo(AD5696_HandleTypeDef *dev, UART_HandleTypeDef *huart);

#ifdef __cplusplus
}
#endif

#endif /* __AD5696_H */
