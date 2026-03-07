"""
Keysight DSO9104A Oscilloscope wrapper.
"""

from . import ATEBase


class DSO9104A(ATEBase):
    def __init__(self, tag: str = 'Scope', rm=None) -> None:
        super().__init__(tag, rm)

    # Add scope-specific commands as needed
    # For now, basic implementation