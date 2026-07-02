"""
HP 6624A Power Supply wrapper.
"""

from .ate_base import ATEBase


class HP6624A(ATEBase):
    def __init__(self, tag: str = 'PSU', rm=None) -> None:
        super().__init__(tag, rm)

    def set_voltage(self, channel, voltage):
        """Set voltage level for channel (1-4)"""
        self.write(f'VSET {channel},{voltage}')

    def set_current(self, channel, current):
        """Set current level for channel (1-4)"""
        self.write(f'ISET {channel},{current}')

    def enable_output(self, channel):
        """Enable output for channel"""
        self.write(f'OUT {channel},1')

    def disable_output(self, channel):
        """Disable output for channel"""
        self.write(f'OUT {channel},0')

    def set_overvoltage_protection(self, channel, voltage):
        """Set OVP trip point"""
        self.write(f'OVSET {channel},{voltage}')

    def enable_ocp(self, channel):
        """Enable overcurrent protection"""
        self.write(f'OCP {channel},1')

    def disable_ocp(self, channel):
        """Disable overcurrent protection"""
        self.write(f'OCP {channel},0')

    def reset_ocp_ovp(self, channel):
        """Reset output disabled by OCP or OVP"""
        self.write(f'OCRST {channel}')

    def get_output_voltage(self, channel):
        """Query measured output voltage"""
        return float(self.query(f'VOUT? {channel}'))

    def get_output_current(self, channel):
        """Query measured output current"""
        return float(self.query(f'IOUT? {channel}'))

    def get_programmed_voltage(self, channel):
        """Query programmed voltage"""
        return float(self.query(f'VSET? {channel}'))

    def get_programmed_current(self, channel):
        """Query programmed current"""
        return float(self.query(f'ISET? {channel}'))

    def get_status(self, channel):
        """Get status byte"""
        return int(self.query(f'STS? {channel}'))

    def get_error(self):
        """Get error code"""
        return self.query('ERR?')