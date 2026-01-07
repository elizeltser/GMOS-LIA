import serial
import time
import subprocess
from pathlib import Path

def flash():
    # Build absolute path to the ELF from this file's location
    repo_root = Path(__file__).resolve().parents[3]
    elf = repo_root / "Firmware" / "STM" / "build" / "Debug" / "GMOS_ST.elf"

    if not elf.exists():
        raise FileNotFoundError(f"ELF file not found at {elf}")

    subprocess.run([
        "STM32_Programmer_CLI",
        "-c", "port=SWD",
        "-w", str(elf),
        "-v",
        "-rst"
    ], check=True)

def reset():
    subprocess.run([
        "STM32_Programmer_CLI",
        "-c", "port=SWD",
        "-rst"
    ], check=True)

def hreset():
    subprocess.run([
        "STM32_Programmer_CLI",
        "-c", "port=SWD",
        "-hardRst"
    ], check=True)


class STM32:
    def __init__(self, port):
        #flash()
        self.ser = serial.Serial(port, baudrate=115200, timeout=1)

    def reset(self):
        hreset()
        time.sleep(2)  # Wait for the device to reboot

    def sync_start(self):
        response = self.ser.write(('GMOS-ST Ready?\r\n').encode())
        response = self.ser.readline().decode().strip()
        return response
    
    def send_command(self, command):
        self.ser.write(('C' + command + 'E').encode())
        response = self.ser.readline().decode().strip()
        return response

    def send_query(self, command):
        self.ser.write(('Q' + command + 'E').encode())
        response = self.ser.readline().decode().strip()
        return response

    def close(self):
        self.ser.close()