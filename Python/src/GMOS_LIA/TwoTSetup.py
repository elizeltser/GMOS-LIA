from pyvisa import ResourceManager
from GMOS_LIA.hp_6624a import PSU


def esd_prot(test_func):
    def wrapper(*args, **kwargs):
        raise NotImplementedError
        #rm = ResourceManager()
#
        #psu = PSU(rm, 'GPIB0::14::INSRT')
        #psu.enable_setup()
        #result = test_func(*args, **kwargs)
        #psu.disable_setup()
        #return result
    return wrapper


@esd_prot
def simple_sweep():
    
    devices = {}
    yield devices
