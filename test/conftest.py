import pytest
from pyvisa import ResourceManager
from pyvisa_mock.base.register import register_resource
from mock_devices import MockLIA, MockSMU

@pytest.fixture(scope="session")
def resource_manager():
    register_resource("MOCK0::LIA::INSTR", MockLIA())
    register_resource("MOCK0::SMU::INSTR", MockSMU())
    register_resource("MOCK1::SMU::INSTR", MockSMU())
    rm = ResourceManager(visa_library="@mock")
    yield rm
    rm.close()