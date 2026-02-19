/* ad5696.c - Minimal AD5696 4-channel DAC driver
 *
 * Implements a small, blocking SPI-based driver.
 * This implementation caches last
 * written values and performs simple 24-bit SPI transactions.
 *
 * NOTE: Verify the exact AD5696 command encodings for your part and
 * adjust AD5696_CMD_* if necessary. This driver focuses on a safe,
 * easy-to-use API for testing and development.
 */

#include "ad5696.h"
#include <string.h>

/* Helper: toggle LDAC if configured: active low pulse */
static inline void ad5696_ldac_pulse(AD5696_HandleTypeDef *dev)
{
  HAL_GPIO_WritePin(dev->ldac_port, dev->ldac_pin, GPIO_PIN_RESET);
  HAL_Delay(1);
  HAL_GPIO_WritePin(dev->ldac_port, dev->ldac_pin, GPIO_PIN_SET);
}

HAL_StatusTypeDef AD5696_Init(AD5696_HandleTypeDef *dev,
                              I2C_HandleTypeDef *hi2c,
                              uint8_t address,
                              GPIO_TypeDef *reset_port, uint16_t reset_pin,
                              GPIO_TypeDef *ldac_port, uint16_t ldac_pin)
{
  if (dev == NULL || hi2c == NULL)
  {
    return HAL_ERROR;
  }
  /*if (dev->ldac_port == NULL)
  {
    return HAL_ERROR;
  }
  if (dev->reset_port == NULL)
  {
    return HAL_ERROR;
  }*/
  dev->hi2c = hi2c;
  dev->addr = address & 0x7FU; /* ensure 7-bit */
  dev->reset_port = reset_port;
  dev->reset_pin = reset_pin;
  dev->ldac_port = ldac_port;
  dev->ldac_pin = ldac_pin;
  dev->vref_mv = AD5696_DEFAULT_VREF_MV;
  for (int i = 0; i < 4; ++i)
  {
    dev->last_value[i] = 0;
  }


  HAL_GPIO_WritePin(dev->reset_port, dev->reset_pin, GPIO_PIN_SET);
  HAL_Delay(1000);
  
  /* Ensure LDAC idle (high) */
  HAL_GPIO_WritePin(dev->ldac_port, dev->ldac_pin, GPIO_PIN_SET);
  return HAL_OK;
}

HAL_StatusTypeDef AD5696_WriteRaw(AD5696_HandleTypeDef *dev, uint8_t channel, uint16_t raw_value)
{
  if (!dev || channel > 3) 
  {
    return HAL_ERROR;
  }

  /* Build 3-byte I2C payload: [cmd_chan] [MSB] [LSB]
     cmd_chan packs command in upper nibble and channel in lower nibble. */
  uint8_t tx[3];
  tx[0] = (uint8_t)((AD5696_CMD_WRITE_UPDATE << 4) | (channel & 0x0FU));
  tx[1] = (uint8_t)((raw_value >> 8) & 0xFFU);
  tx[2] = (uint8_t)(raw_value & 0xFFU);

  HAL_StatusTypeDef st = HAL_I2C_Master_Transmit(dev->hi2c, (uint16_t)(dev->addr << 1), tx, 3, HAL_MAX_DELAY);
  if (st == HAL_OK)
  {
    dev->last_value[channel] = raw_value;
  }
  return st;
}

HAL_StatusTypeDef AD5696_SetVoltage_mV(AD5696_HandleTypeDef *dev, uint8_t channel, uint32_t millivolts)
{
  if (!dev || dev->vref_mv == 0)
  {
    return HAL_ERROR;
  }

  uint64_t tmp = (uint64_t)millivolts * 65535U;
  uint16_t raw = (uint16_t)(tmp / dev->vref_mv);

  return AD5696_WriteRaw(dev, channel, raw);
}

HAL_StatusTypeDef AD5696_Pulse(AD5696_HandleTypeDef *dev, uint8_t channel, uint16_t value, uint32_t pulse_ms)
{
  if (!dev) return HAL_ERROR;
  if (channel > 3) return HAL_ERROR;

  uint16_t prev = dev->last_value[channel];
  HAL_StatusTypeDef st = AD5696_WriteRaw(dev, channel, value);
  if (st != HAL_OK) return st;
  if (pulse_ms) HAL_Delay(pulse_ms);
  return AD5696_WriteRaw(dev, channel, prev);
}

HAL_StatusTypeDef AD5696_Read(AD5696_HandleTypeDef *dev, uint8_t channel, uint16_t *dac_value)
{
  if (!dev || !dac_value) return HAL_ERROR;
  if (channel > 3) return HAL_ERROR;
  *dac_value = dev->last_value[channel];
  return HAL_OK;
}

HAL_StatusTypeDef AD5696_Reset(AD5696_HandleTypeDef *dev)
{
  if (!dev) return HAL_ERROR;

  if (dev->reset_port == NULL || dev->reset_pin == 0) {
    /* No dedicated reset pin; return HAL_ERROR to indicate no hardware reset available */
    return HAL_ERROR;
  }

  /* Toggle reset: assume active low */
  HAL_GPIO_WritePin(dev->reset_port, dev->reset_pin, GPIO_PIN_RESET);
  HAL_Delay(5);
  HAL_GPIO_WritePin(dev->reset_port, dev->reset_pin, GPIO_PIN_SET);
  HAL_Delay(1);
  return HAL_OK;
}

int AD5696_ConnectivityTest(AD5696_HandleTypeDef *dev)
{
  if (dev == NULL || dev->hi2c == NULL)
  {
    return 0;
  }
  /* Use HAL_I2C_IsDeviceReady to check for ACK */
  return (HAL_I2C_IsDeviceReady(dev->hi2c, (uint16_t)(dev->addr << 1), 3, 50) == HAL_OK) ? 1 : 0;
}

void AD5696_Demo(AD5696_HandleTypeDef *dev, UART_HandleTypeDef *huart)
{
  if (!dev || !huart) return;
  HAL_UART_Transmit(huart, (uint8_t *)"AD5696 Demo\r\n", 12, HAL_MAX_DELAY);
  int ok = AD5696_ConnectivityTest(dev);
  if (ok) HAL_UART_Transmit(huart, (uint8_t *)"AD5696 OK\r\n", 11, HAL_MAX_DELAY);
  else HAL_UART_Transmit(huart, (uint8_t *)"AD5696 FAIL\r\n", 13, HAL_MAX_DELAY);
}
