/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "mcp4726.h"
#include "stm32f3xx_hal.h"
#include "stm32f3xx_hal_adc.h"
#include "stm32f3xx_hal_adc_ex.h"
#include "stm32f3xx_hal_def.h"
#include <stdio.h>
#include <string.h>

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;

I2C_HandleTypeDef hi2c1;

UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
uint8_t adc_conv_complete_flag = 0;
MCP4725_HandleTypeDef gate1A;
MCP4725_HandleTypeDef gate2B;
MCP4725_HandleTypeDef gate4B;
MCP4725_HandleTypeDef gate5A;
MCP4725_HandleTypeDef heater1A;
MCP4725_HandleTypeDef heater2B;
MCP4725_HandleTypeDef heater4B;
MCP4725_HandleTypeDef heater5A;

volatile uint16_t adc_buffer[4];
volatile uint16_t *p_heater_1A_V = adc_buffer;
volatile uint16_t *p_heater_1A_I = adc_buffer + 1;
volatile uint16_t *p_heater_5A_I = adc_buffer + 2;
volatile uint16_t *p_heater_5A_V = adc_buffer + 3;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_I2C1_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_ADC1_Init(void);
/* USER CODE BEGIN PFP */
static void I2C_ScanAndPrint(void);
static void UART_WaitForString(const char *target);
static void UART_ReceiveAndProcess(void);

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_I2C1_Init();
  MX_USART2_UART_Init();
  MX_ADC1_Init();
  /* USER CODE BEGIN 2 */
  /* Initialize MCP4725 devices */
  MCP4725_Init(&gate1A, &hi2c1, MCP4725_ADDR_000);
  MCP4725_Init(&gate2B, &hi2c1, MCP4725_ADDR_001);
  MCP4725_Init(&gate4B, &hi2c1, MCP4725_ADDR_010);
  MCP4725_Init(&gate5A, &hi2c1, MCP4725_ADDR_011);
  MCP4725_Init(&heater1A, &hi2c1, MCP4725_ADDR_100);
  MCP4725_Init(&heater2B, &hi2c1, MCP4725_ADDR_101);
  MCP4725_Init(&heater4B, &hi2c1, MCP4725_ADDR_110);
  MCP4725_Init(&heater5A, &hi2c1, MCP4725_ADDR_111);
  
  if (HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_ADC_Start_DMA(&hadc1, (uint32_t *)adc_buffer, 4) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  int voltage_mv = 0;
  HAL_StatusTypeDef res;
  char buf[64];
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */

    res = MCP4725_SetVoltage_mV(&heater1A, 0, MCP4725_DEFAULT_VREF_MV);
    HAL_Delay(1000);
    res = MCP4725_SetVoltage_mV(&heater1A, 2500, MCP4725_DEFAULT_VREF_MV);
    for (volatile int i = 0; i < 1000; ++i)
    {
      while (adc_conv_complete_flag != 1) {}
      
      adc_conv_complete_flag = 0;
      
      int n = snprintf(buf, sizeof(buf), "H1A V: %u | I: %u\r\n", *p_heater_1A_V, *p_heater_1A_I);
      if (n > 0) HAL_UART_Transmit(&huart2, (uint8_t *)buf, (uint16_t)n, HAL_MAX_DELAY);
  }
    
    /* Main loop: wait for and process incoming UART messages */
    //UART_ReceiveAndProcess();
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSE;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USART2|RCC_PERIPHCLK_I2C1;
  PeriphClkInit.Usart2ClockSelection = RCC_USART2CLKSOURCE_PCLK1;
  PeriphClkInit.I2c1ClockSelection = RCC_I2C1CLKSOURCE_SYSCLK;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_MultiModeTypeDef multimode = {0};
  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Common config
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode = ADC_SCAN_ENABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 4;
  hadc1.Init.DMAContinuousRequests = ENABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SEQ_CONV;
  hadc1.Init.LowPowerAutoWait = DISABLE;
  hadc1.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure the ADC multi-mode
  */
  multimode.Mode = ADC_MODE_INDEPENDENT;
  if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_1;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.SamplingTime = ADC_SAMPLETIME_19CYCLES_5;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_2;
  sConfig.Rank = ADC_REGULAR_RANK_2;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_6;
  sConfig.Rank = ADC_REGULAR_RANK_3;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_7;
  sConfig.Rank = ADC_REGULAR_RANK_4;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.Timing = 0x00201D2B;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Analogue filter
  */
  if (HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Digital filter
  */
  if (HAL_I2CEx_ConfigDigitalFilter(&hi2c1, 0) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA1_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA1_Channel1_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : LD2_Pin */
  GPIO_InitStruct.Pin = LD2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* I2C scanner: scan 7-bit addresses 0x01..0x7E and print responders */
static void I2C_ScanAndPrint(void)
{
  char buf[64];
  for (uint8_t addr = 0x01; addr <= 0x7E; ++addr) {
    if (HAL_I2C_IsDeviceReady(&hi2c1, (uint16_t)(addr << 1), 1, 10) == HAL_OK) {
      int n = snprintf(buf, sizeof(buf), "I2C device at 0x%02X\r\n", addr);
      if (n > 0) HAL_UART_Transmit(&huart2, (uint8_t *)buf, (uint16_t)n, HAL_MAX_DELAY);
    }
  }
}

/* Wait for an exact string from UART (blocking). Handles partial/incorrect input and continues listening
   until the full `target` string is received. */
static void UART_WaitForString(const char *target)
{
  size_t len = strlen(target);
  size_t pos = 0;
  uint8_t c;

  while (pos < len) {
    if (HAL_UART_Receive(&huart2, &c, 1, HAL_MAX_DELAY) != HAL_OK) {
      continue;
    }
    if (c == (uint8_t)target[pos]) {
      pos++;
    } else {
      if (c == (uint8_t)target[0]) {
        pos = 1;
      } else {
        pos = 0;
      }
    }
  }

  const char ok_msg[] = "Expected message received\r\n";
  HAL_UART_Transmit(&huart2, (uint8_t *)ok_msg, sizeof(ok_msg) - 1, HAL_MAX_DELAY);
}

/* Simple UART receiver with timeout: waits indefinitely for first byte, then expects CRLF within UART_RX_TIMEOUT_MS milliseconds. */
static void UART_ReceiveAndProcess(void)
{
  uint8_t buf[128];
  size_t idx = 0;
  uint8_t c;

  /* Wait indefinitely for first byte of a message */
  if (HAL_UART_Receive(&huart2, &c, 1, HAL_MAX_DELAY) != HAL_OK) {
    return;
  }
  buf[idx++] = c;
  if (idx >= sizeof(buf) - 1) idx = 0;

  uint32_t start = HAL_GetTick();

  /* Read remaining bytes, but if CRLF isn't received within UART_RX_TIMEOUT_MS, abort */
  while (1) {
    if (HAL_UART_Receive(&huart2, &c, 1, 100) == HAL_OK) {
      buf[idx++] = c;
      if (idx >= sizeof(buf) - 1) {
        /* buffer overflow - reset to avoid OOB */
        idx = 0;
      }
      if (idx >= 2 && buf[idx - 1] == 'E') {
        break;
      }
      /* reset timeout after successful reception of a byte */
      start = HAL_GetTick();
    } else {
      /* no byte received within 100 ms; check overall timeout */
      if ((HAL_GetTick() - start) >= UART_RX_TIMEOUT_MS) {
        /* Abort message reception and notify host */
        HAL_UART_Transmit(&huart2, (uint8_t *)"TIMEOUT\r\n", 9, HAL_MAX_DELAY);
        return;
      }
      /* otherwise, loop and keep waiting */
    }
  }

  if (idx < 2) return; /* must have at least CRLF */

  /* Null-terminate before CRLF */
  buf[idx - 1] = '\0';

  /* Type is first byte, payload follows */
  char type = (char)buf[0];
  char *payload = (char *)&buf[1];

  if (type == 'Q') {
    if (strcmp(payload, "version") == 0)
    {
      char resp[64];
      int n = snprintf(resp, sizeof(resp), "%s\r\n", FIRMWARE_VERSION);
      if (n > 0) HAL_UART_Transmit(&huart2, (uint8_t *)resp, (uint16_t)n, HAL_MAX_DELAY);
    }
    else
    {
      HAL_UART_Transmit(&huart2, (uint8_t *)"ERR\r\n", 5, HAL_MAX_DELAY);
    }
  }
  else if (type == 'C')
  {
    if (strcmp(payload, "PING") == 0)
    {
      HAL_UART_Transmit(&huart2, (uint8_t *)"PONG\r\n", 6, HAL_MAX_DELAY);
    }
    else if (strcmp(payload, "I2C_SCAN") == 0)
    {
      I2C_ScanAndPrint();
    }
    else
    {
      HAL_UART_Transmit(&huart2, (uint8_t *)"OK\r\n", 4, HAL_MAX_DELAY);
    }
  }
  else
  {
    HAL_UART_Transmit(&huart2, (uint8_t *)"ERR\r\n", 5, HAL_MAX_DELAY);
  }
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
 	if(hadc->Instance==ADC1)
    {
        /* Set flag to indicate that ADC conversion is complete */
        adc_conv_complete_flag = 1;
    }
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
