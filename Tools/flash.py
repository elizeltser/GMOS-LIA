import subprocess

def flash():
    subprocess.run([
        "STM32_Programmer_CLI",
        "-c", "port=SWD",
        "-w", "Firmware/STM/build/GMOS_ST.elf",
        "-v",
        "-rst"
    ], check=True)
