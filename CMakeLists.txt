cmake_minimum_required(VERSION 3.21)

project(GMOS_ROOT NONE)  # NONE = no compiler here, firmware handles that

enable_testing()

# STM32 firmware
add_subdirectory(Firmware/STM)

