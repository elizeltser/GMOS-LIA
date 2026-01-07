import pytest
from pyvisa import ResourceManager
from GMOS_LIA.hp_6624a import PSU
from GMOS_LIA.keysight_b2962a import SMU
from GMOS_LIA.stanford_research_sr860 import LIA
from pathlib import Path
import re
import csv
from _csv import Writer
from typing import Generator
from GMOS_LIA.stm32 import STM32, reset, hreset

import pytest
import sys
import os

@pytest.fixture(autouse=False)
def reset_stm32_per_test():
    """
    This fixture runs automatically before every single test.
    """
    print("\n[Hardware] Resetting STM32...")
    try:
        reset()
    except Exception as e:
        pytest.fail(f"Failed to reset STM32 via CLI: {e}")
    yield
    
@pytest.fixture(scope="session")
def resource_manager():
    rm = ResourceManager()
    yield rm
    rm.close()

    
def get_resource(resource_manager, address: str):
    return resource_manager.open_resource(address)

    
@pytest.fixture(scope="class", autouse=False)
def esd_protection(resource_manager):
    psu = PSU(get_resource(resource_manager, 'GPIB0::14::INSTR'))
    psu.enable_setup()
    yield
    psu.disable_setup()

@pytest.fixture(scope="class", autouse=False)
def power_supply(resource_manager):
    psu = PSU(get_resource(resource_manager, 'GPIB0::14::INSTR'))
    psu.enable_setup(start_power=True)
    yield
    psu.disable_setup()

@pytest.fixture(scope="class")
def stm32_device() -> Generator[STM32, None, None]:
    stm32 = STM32(port='COM5')
    #response = stm32.sync_start()
    #assert response == 'Expected message received', "STM32 not ready, are you sure it's connected?"
    yield stm32
    stm32.close()

    
@pytest.fixture(scope="function")
def result_file(request) -> Generator[Writer, None, None]:
    test_name = request.node.originalname
    result_file_dir =  Path.cwd() / "Results" / test_name
    result_file_dir.mkdir(parents=True, exist_ok=True)

    # Regex pattern: matches "testname.csv" or "testname_1.csv", "testname_2.csv", etc.
    p = re.compile(rf"{re.escape(test_name)}(?:_(\d+))?\.csv")
    existing_files = list(result_file_dir.glob("*.csv"))
    indices = []

    # Find all matching files and extract their indices
    for f in existing_files:
        m = p.fullmatch(f.name)
        if m:
            idx_str = m.group(1)
            if idx_str is None:
                indices.append(0)  # base file without number treated as 0
            else:
                indices.append(int(idx_str))

    # Determine the next available index
    next_idx = max(indices, default=-1) + 1
    if next_idx == 0:
        result_file_name = f"{test_name}.csv"
    else:
        result_file_name = f"{test_name}_{next_idx}.csv"

    result_file_path = result_file_dir / result_file_name

    # Open CSV file for writing
    with result_file_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(['Parameters', request.node.nodeid])
        yield writer  # Provide CSV writer to the test

    # Post-test cleanup: remove file if only header + parameters row
    row_count = sum(1 for _ in result_file_path.open("r", newline=""))
    if row_count == 2:
        result_file_path.unlink()

@pytest.fixture(scope="class")
def devices(resource_manager) -> Generator[dict, None, None]:
    
    devices_address = {"LIA"           : 'TCPIP::132.68.54.149::INSTR',
                        "Drain SMU"     : 'GPIB0::22::INSTR',
                        "Heater SMU"    : 'GPIB0::23::INSTR'}
    
    lia = LIA(get_resource(resource_manager, devices_address["LIA"]))
    heater = SMU(get_resource(resource_manager, devices_address["Heater SMU"]))
    drain = SMU(get_resource(resource_manager, devices_address["Drain SMU"]))
    devices = dict(LIA=lia, Heater=heater, Drain=drain)
    yield devices
    for device in devices.values():
        device.set_off()
