/* mcp4726.h - MCP4725 basic driver (fast write, DC and pulse helpers)
 *
 * Simple, blocking driver using STM32 HAL I2C.
 */
#ifndef __MCP4726_H
#define __MCP4726_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f3xx_hal.h"

#define MCP4725_DEFAULT_VREF_MV 3300U
#define MCP4725_ADDR_000  0x60U
#define MCP4725_ADDR_001  0x61U
#define MCP4725_ADDR_010  0x62U
#define MCP4725_ADDR_011  0x63U
#define MCP4725_ADDR_100  0x64U
#define MCP4725_ADDR_101  0x65U
#define MCP4725_ADDR_110  0x66U
#define MCP4725_ADDR_111  0x67U

/* Additional helpers */
#define MCP4725_SOFT_RESET_CMD 0x06U  /* Software reset command (General Call or device) */

typedef struct {
  I2C_HandleTypeDef *hi2c; /* HAL I2C handle */
  uint8_t addr;            /* 7-bit I2C address (0x60 / 0x61) */
  uint16_t last_value;     /* last 12-bit value written (0..4095) */
} MCP4725_HandleTypeDef;

/* Initialize driver instance */
HAL_StatusTypeDef MCP4725_Init(MCP4725_HandleTypeDef *dev, I2C_HandleTypeDef *hi2c, uint8_t address);

/* Write raw 12-bit value (0..4095) immediately (fast mode) */
HAL_StatusTypeDef MCP4725_WriteRaw(MCP4725_HandleTypeDef *dev, uint16_t value);

/* Set output by millivolts (converts to 12-bit with provided vref, default use MCP4725_DEFAULT_VREF_MV) */
HAL_StatusTypeDef MCP4725_SetVoltage_mV(MCP4725_HandleTypeDef *dev, uint32_t millivolts, uint32_t vref_mv);

/* Produce a short blocking pulse: write `value`, wait `pulse_ms`, restore previous value */
HAL_StatusTypeDef MCP4725_Pulse(MCP4725_HandleTypeDef *dev, uint16_t value, uint32_t pulse_ms);

/* Status and parsing helpers for 5-byte reads. The MCP4725 returns five bytes on a read; the
   first status byte (buf[0]) contains RDY (D7), POR (D6) and the current power-down bits (D3:D2).
   The EEPROM upper status and data appear in buf[3] and buf[4]. */

/* Status bit masks (first status byte: buf[0]) */
#define MCP4725_STATUS_PD_MASK   0x0CU /* D3:D2 */
#define MCP4725_STATUS_PD_SHIFT  2
#define MCP4725_STATUS_POR_MASK  0x40U /* D6 */
#define MCP4725_STATUS_RDY_MASK  0x80U /* D7 */

/* EEPROM status masks (buf[3]) */
#define MCP4725_EEPROM_PD_MASK   0xC0U /* D7:D6 */
#define MCP4725_EEPROM_PD_SHIFT  6

/* Power-down modes (PD1:PD0) */
typedef enum {
  MCP4725_PD_NORMAL = 0,
  MCP4725_PD_1K     = 1,
  MCP4725_PD_100K   = 2,
  MCP4725_PD_500K   = 3
} MCP4725_PDMode_t;

/* POR (power-on reset) state */
typedef enum {
  MCP4725_POR_OFF = 0,
  MCP4725_POR_ON  = 1
} MCP4725_PORState_t;

/* RDY/BSY state */
typedef enum {
  MCP4725_RDY_BUSY  = 0,
  MCP4725_RDY_READY = 1
} MCP4725_RDYState_t;

/* Read and parse device registers (reads 5 bytes and fills provided outputs).
   Any output pointer may be NULL if the caller does not need that value.
   - dac_value: current DAC register (12-bit, 0..4095)
   - eeprom_value_raw14: raw 14-bit EEPROM/status value as reported by device
   - pd_current: current power-down mode (from status byte)
   - pd_eeprom: power-down mode stored in EEPROM/status area
   - por: POR flag (optional)
   - rdy: RDY/BSY flag (optional)
*/
HAL_StatusTypeDef MCP4725_Read(MCP4725_HandleTypeDef *dev,
                               uint16_t *dac_value,
                               uint16_t *eeprom_value_raw14,
                               MCP4725_PDMode_t *pd_current,
                               MCP4725_PDMode_t *pd_eeprom,
                               MCP4725_PORState_t *por,
                               MCP4725_RDYState_t *rdy);

/* Send a software reset (0x06) to the device (attempts general-call then device address)
   Returns HAL_OK on success
*/
HAL_StatusTypeDef MCP4725_Reset(MCP4725_HandleTypeDef *dev);

/* Connectivity test helper: returns 1 if ACK received (device ready), 0 otherwise */
int MCP4725_ConnectivityTest(MCP4725_HandleTypeDef *dev);

/* Move existing MCP4725 demo/initialization code here so it can be called later if needed.
   This function is not called at startup per request.
*/
static void MCP4725_Demo(MCP4725_HandleTypeDef *dev, UART_HandleTypeDef *huart);

#ifdef __cplusplus
}
#endif

#endif /* __MCP4726_H */
