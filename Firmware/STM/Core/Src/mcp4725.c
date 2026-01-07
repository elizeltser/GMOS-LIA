/* mcp4725.c - Minimal MCP4725 driver implementation
 * Uses fast write (2-byte) to set DAC output.
 */
#include "mcp4726.h"
#include <stdio.h>
#include <string.h>

HAL_StatusTypeDef MCP4725_Init(MCP4725_HandleTypeDef *dev, I2C_HandleTypeDef *hi2c, uint8_t address)
{
  if (dev == NULL || hi2c == NULL)
  {
    return HAL_ERROR;
  }
  dev->hi2c = hi2c;
  dev->addr = address & 0x7F; /* ensure 7-bit */
  dev->last_value = 0;
  return HAL_OK;
}

HAL_StatusTypeDef MCP4725_WriteRaw(MCP4725_HandleTypeDef *dev, uint16_t value)
// MCP4725_setValue(&myMCP4725, value, MCP4725_FAST_MODE, MCP4725_POWER_DOWN_OFF);
//  MCP4725_writeComand(_MCP4725, value, mode, powerType);
/*
			buffer[0] = mode | (powerType << 4)  | highByte(value);
			buffer[1] = lowByte(value);
		
			I2C_Stat = HAL_I2C_Master_Transmit(_MCP4725->hi2c, _MCP4725->_i2cAddress, buffer, 2, 1000);
      */
{
  if (dev == NULL || dev->hi2c == NULL)
  {
    return HAL_ERROR;
  }
  if (value > 4095U) value = 4095U; /* clamp to 12-bit */

  uint8_t tx[2];
  tx[0] = (uint8_t)(value / 256);
  tx[1] = (uint8_t)(value % 256);

  HAL_StatusTypeDef st = HAL_I2C_Master_Transmit(dev->hi2c, (uint16_t)(dev->addr << 1), tx, 2, HAL_MAX_DELAY);
  if (st == HAL_OK)
  {
    dev->last_value = value;
  }
  return st;
}

HAL_StatusTypeDef MCP4725_SetVoltage_mV(MCP4725_HandleTypeDef *dev, uint32_t millivolts, uint32_t vref_mv)
{
  if (dev == NULL || vref_mv == 0)
  {
    return HAL_ERROR;
  }

  uint64_t tmp = (uint64_t)millivolts * 4095U;
  uint16_t raw = (uint16_t)((tmp + (vref_mv/2)) / vref_mv); /* rounded */
  if (raw > 4095U)
  {
    raw = 4095U;
  }
  return MCP4725_WriteRaw(dev, raw);
}

HAL_StatusTypeDef MCP4725_Pulse(MCP4725_HandleTypeDef *dev, uint16_t value, uint32_t pulse_ms)
{
  if (dev == NULL) return HAL_ERROR;

  uint16_t prev = dev->last_value;
  HAL_StatusTypeDef st = MCP4725_WriteRaw(dev, value);
  if (st != HAL_OK)
  {
    return st;
  }

  if (pulse_ms)
  {
    HAL_Delay(pulse_ms);
    st = MCP4725_WriteRaw(dev, prev);
  }

  return st;
}

/* Read 5 bytes from device and parse values into caller-provided outputs.
   Any pointer may be NULL if not needed.
*/
HAL_StatusTypeDef MCP4725_Read(MCP4725_HandleTypeDef *dev,
                               uint16_t *dac_value,
                               uint16_t *eeprom_value_raw14,
                               MCP4725_PDMode_t *pd_current,
                               MCP4725_PDMode_t *pd_eeprom,
                               MCP4725_PORState_t *por,
                               MCP4725_RDYState_t *rdy)
{
  if (dev == NULL || dev->hi2c == NULL)
  {
    return HAL_ERROR;
  }
  uint8_t buf[6];
  HAL_StatusTypeDef st = HAL_I2C_Master_Receive(dev->hi2c, (uint16_t)(dev->addr << 1), buf, 6, HAL_MAX_DELAY);
  if (st != HAL_OK)
  {
    return st;
  }

  /* Status byte (buf[0]) */
  uint8_t b0 = buf[1];
  uint8_t pd_cur = (uint8_t)((b0 & MCP4725_STATUS_PD_MASK) >> MCP4725_STATUS_PD_SHIFT);
  if (pd_current)
  {
    *pd_current = (MCP4725_PDMode_t)pd_cur;
  }
  if (por)
  {
    *por = (b0 & MCP4725_STATUS_POR_MASK) ? MCP4725_POR_ON : MCP4725_POR_OFF;
  }
  if (rdy)
  {
    *rdy = (b0 & MCP4725_STATUS_RDY_MASK) ? MCP4725_RDY_READY : MCP4725_RDY_BUSY;
  }

  /* Current DAC value: buf[2] (MSB D11..D4), buf[3] (upper nibble D3..D0 << 4) */
  if (dac_value)
  {
    *dac_value = (uint16_t)(((uint16_t)buf[2] << 4) | ((uint16_t)buf[3] >> 4)) & 0x0FFFU;
  }

  /* EEPROM raw 14-bit value: buf[4] lower 6 bits + buf[5] => 14 bits */
  uint16_t e14 = (uint16_t)((((uint16_t)(buf[4] & 0x3FU)) << 8) | (uint16_t)buf[5]) & 0x3FFFU;
  if (eeprom_value_raw14)
  {
    *eeprom_value_raw14 = e14;
  }
  /* EEPROM power-down bits are typically stored in buf[4] upper two bits (D7:D6) */
  uint8_t pd_e = (uint8_t)((buf[4] & MCP4725_EEPROM_PD_MASK) >> MCP4725_EEPROM_PD_SHIFT);
  if (pd_eeprom)
  {
    *pd_eeprom = (MCP4725_PDMode_t)pd_e;
  }
  return HAL_OK;
}

/* Attempt a software reset. The MCP4725 supports a software reset via the
   general-call address (0x00) with data 0x06; some systems may also accept
   the command sent to the device address. Try general-call first, fall back
   to device address if ACK not received.
*/
HAL_StatusTypeDef MCP4725_Reset(MCP4725_HandleTypeDef *dev)
{
  if (dev == NULL || dev->hi2c == NULL) return HAL_ERROR;
  uint8_t cmd = (uint8_t)MCP4725_SOFT_RESET_CMD;
  HAL_StatusTypeDef st = HAL_I2C_Master_Transmit(dev->hi2c, (uint16_t)0x00U, &cmd, 1, HAL_MAX_DELAY);
  if (st == HAL_OK)
  {
    return HAL_OK;
  }
  /* fallback: send to device address */
  return HAL_I2C_Master_Transmit(dev->hi2c, (uint16_t)(dev->addr << 1), &cmd, 1, HAL_MAX_DELAY);
}

/* Connectivity test: returns 1 if device ACKs (ready), 0 otherwise.
   Uses HAL_I2C_IsDeviceReady (which checks for ACK) to implement a simple
   connectivity check. This mirrors the user's request to write/check ACK.
*/
int MCP4725_ConnectivityTest(MCP4725_HandleTypeDef *dev)
{
  if (dev == NULL || dev->hi2c == NULL)
  {
    return 0;
  }
  /* 3 trials, 100 ms timeout per trial */
  return (HAL_I2C_IsDeviceReady(dev->hi2c, (uint16_t)(dev->addr << 1), 3, 100) == HAL_OK) ? 1 : 0;
}

/* Move existing MCP4725 demo/initialization code here so it can be called later if needed.
   This function is not called at startup per request. */
static void MCP4725_Demo(MCP4725_HandleTypeDef *dev, UART_HandleTypeDef *huart)
{
  uint8_t msg2[] = "MCP4725 DAC Test\r\n";

  HAL_UART_Transmit(huart, msg2, sizeof(msg2) - 1, HAL_MAX_DELAY);

  int ok = MCP4725_ConnectivityTest(dev); // 1 == OK, 0 == fail
  if (ok) {
    HAL_UART_Transmit(huart, (uint8_t *)"DAC Read OK\r\n", 14, HAL_MAX_DELAY);
  } else {
    HAL_UART_Transmit(huart, (uint8_t *)"DAC Read FAIL\r\n", 16, HAL_MAX_DELAY);
    while (1) {};
  }

  MCP4725_Reset(dev); // attempt software reset
  uint16_t dac = 0;
  uint16_t eeprom14 = 0;
  MCP4725_PDMode_t pd_cur = MCP4725_PD_NORMAL;
  MCP4725_PDMode_t pd_eeprom = MCP4725_PD_NORMAL;
  MCP4725_PORState_t por = MCP4725_POR_OFF;
  MCP4725_RDYState_t rdy = MCP4725_RDY_BUSY;

  if (MCP4725_Read(dev, &dac, &eeprom14, &pd_cur, &pd_eeprom, &por, &rdy) == HAL_OK) {
    char dbg[128];
    int n = snprintf(dbg, sizeof(dbg), "dac=%u, eeprom14=%u, pd_cur=%u, pd_eeprom=%u, POR=%u, RDY=%u\r\n",
                     (unsigned)dac, (unsigned)eeprom14, (unsigned)pd_cur, (unsigned)pd_eeprom, (unsigned)por, (unsigned)rdy);
    if (n > 0) HAL_UART_Transmit(huart, (uint8_t *)dbg, (uint16_t)n, HAL_MAX_DELAY);
  }

  /* Example short pulses (blocking): */
  /* dac1: brief full-scale pulse */
  MCP4725_Pulse(dev, 4095U, 50U); /* 50 ms pulse to Vref */
  /* dac2: brief 0V pulse */
  MCP4725_Pulse(dev, 0U, 20U);    /* 20 ms pulse to 0V */
}