"""
ATE (Automated Test Equipment) wrappers for GPIB devices.
"""

from .ate_base import ATEBase
from .b2962a import B2962A, SourceMode, SourceFunction, MeasurementFunction
from .dso9104a import DSO9104A
from .hp6624a import HP6624A
from .hp8116a import HP8116A, TriggerMode, TriggerSlope, WaveformType, PhaseMode
from .sr860 import SR860, Sensitivity, TimeConstant, FilterSlope, InputSource, InputCoupling

# Aliases
LIA = SR860
SCU = B2962A
PSU = HP6624A
SG = HP8116A
Scope = DSO9104A

__all__ = [
    'LIA',
    'SCU',
    'PSU',
    'SG',
    'Scope',
    'SourceMode',
    'SourceFunction',
    'MeasurementFunction',
    'TriggerMode',
    'TriggerSlope',
    'WaveformType',
    'PhaseMode',
    'Sensitivity',
    'TimeConstant',
    'FilterSlope',
    'InputSource',
    'InputCoupling',
    ]