"""Interactive REPL for ad-hoc bench control of the GMOS test setup."""

import cmd
import logging
import shlex

import pyvisa

import ATE

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATEFMT = "%H:%M:%S"


class GMOSRepl(cmd.Cmd):
    intro = "GMOS REPL — type help or ? to list commands."
    prompt = "gmos> "

    def __init__(self, rm: pyvisa.ResourceManager) -> None:
        super().__init__()
        self.rm = rm
        self.scu1: ATE.SCU | None = None
        self.scu2: ATE.SCU | None = None
        self.psu: ATE.PSU | None = None

    # ---- lazy openers ---------------------------------------------------

    def _get_scu(self, tag: str):
        attr = "scu1" if tag == "SCU1" else "scu2"
        existing = getattr(self, attr)
        if existing is not None:
            return existing
        scu = ATE.SCU(tag, rm=self.rm)
        scu.__enter__()
        setattr(self, attr, scu)
        logger.info(f"Opened {tag}")
        return scu

    def _get_psu(self):
        if self.psu is not None:
            return self.psu
        psu = ATE.PSU('PSU', rm=self.rm)
        psu.__enter__()
        self.psu = psu
        logger.info("Opened PSU")
        return psu

    # ---- argument parsing ----------------------------------------------

    @staticmethod
    def _split(arg: str) -> list[str]:
        try:
            return shlex.split(arg)
        except ValueError as e:
            logger.warning(f"could not parse arguments: {e}")
            return []

    # ---- shared SCU dispatch -------------------------------------------

    def _scu_cmd(self, tag: str, arg: str) -> None:
        parts = self._split(arg)
        if not parts:
            logger.warning(f"{tag}: missing subcommand (voltage <V> | on | off)")
            return
        sub = parts[0].lower()
        try:
            scu = self._get_scu(tag)
            if sub == "voltage":
                if len(parts) != 2:
                    logger.warning(f"{tag} voltage: expected exactly one numeric argument")
                    return
                v = float(parts[1])
                scu.set_source_function(ATE.SourceFunction.VOLTAGE, 10e-6, channel=1)
                scu.set_voltage(v, channel=1)
                logger.info(f"{tag} voltage set to {v} V (compliance 10 µA)")
            elif sub == "on":
                scu.enable_output(channel=1)
                logger.info(f"{tag} output enabled")
            elif sub == "off":
                scu.disable_output(channel=1)
                logger.info(f"{tag} output disabled")
            else:
                logger.warning(f"{tag}: unknown subcommand {sub!r} (voltage <V> | on | off)")
        except Exception:
            logger.error(f"{tag} {sub} failed", exc_info=True)

    # ---- commands -------------------------------------------------------

    def do_scu1(self, arg: str) -> None:
        """scu1 voltage <V> | scu1 on | scu1 off"""
        self._scu_cmd("SCU1", arg)

    def do_scu2(self, arg: str) -> None:
        """scu2 voltage <V> | scu2 on | scu2 off"""
        self._scu_cmd("SCU2", arg)

    def do_protection(self, arg: str) -> None:
        """protection on|off — toggle PSU ch2 (ESD, 5V/0.7A) and ch4 (fan, 7V/1.5A)."""
        parts = self._split(arg)
        if len(parts) != 1 or parts[0].lower() not in ("on", "off"):
            logger.warning("protection: expected 'on' or 'off'")
            return
        state = parts[0].lower()
        try:
            psu = self._get_psu()
            if state == "on":
                psu.set_voltage(2, 5.0)
                psu.set_current(2, 0.7)
                psu.set_voltage(4, 7.0)
                psu.set_current(4, 1.5)
                psu.enable_output(2)
                psu.enable_output(4)
                logger.info("PSU protection on (ch2 ESD 5V/0.7A, ch4 fan 7V/1.5A)")
            else:
                psu.disable_output(2)
                psu.disable_output(4)
                logger.info("PSU protection off (ch2, ch4 disabled)")
        except Exception:
            logger.error(f"protection {state} failed", exc_info=True)

    def do_status(self, arg: str) -> None:
        """status — read SCU1/SCU2 voltage and current, and PSU ch2/ch4 voltage and current."""
        lines = ["--- status ---"]
        for tag in ("SCU1", "SCU2"):
            try:
                scu = self._get_scu(tag)
                v = scu.get_voltage(channel=1)
                i = scu.measure_current(channel=1)
                lines.append(f"{tag}: V={v:.6g} V   I={i:.6g} A")
            except Exception:
                logger.error(f"{tag} status read failed", exc_info=True)
                lines.append(f"{tag}: <error>")
        try:
            psu = self._get_psu()
            for ch, label in ((2, "ESD"), (4, "fan")):
                try:
                    v = psu.get_output_voltage(ch)
                    i = psu.get_output_current(ch)
                    lines.append(f"PSU ch{ch} ({label}): V={v:.6g} V   I={i:.6g} A")
                except Exception:
                    logger.error(f"PSU ch{ch} status read failed", exc_info=True)
                    lines.append(f"PSU ch{ch} ({label}): <error>")
        except Exception:
            logger.error("PSU status read failed", exc_info=True)
            lines.append("PSU: <error>")
        print("\n".join(lines))

    def do_quit(self, arg: str) -> bool:
        """quit — reset and close all opened instruments, then exit."""
        self._close_all()
        return True

    def do_exit(self, arg: str) -> bool:
        """exit — alias for quit."""
        return self.do_quit(arg)

    def do_EOF(self, arg: str) -> bool:
        """Ctrl-D — exit cleanly."""
        print()
        return self.do_quit(arg)

    # ---- teardown -------------------------------------------------------

    def _close_all(self) -> None:
        for attr in ("scu1", "scu2", "psu"):
            inst = getattr(self, attr)
            if inst is None:
                continue
            try:
                inst.__exit__(None, None, None)
                logger.info(f"Closed {attr}")
            except Exception:
                logger.error(f"failed to close {attr}", exc_info=True)
            finally:
                setattr(self, attr, None)


def run_repl(log_path: str | None = None) -> None:
    # Don't propagate REPL log records to the root logger's console handler —
    # REPL logging is file-only, and only when --log is set.
    prev_propagate = logger.propagate
    logger.propagate = False

    file_handler: logging.Handler | None = None
    if log_path:
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.info(f"REPL logging to {log_path}")

    rm = pyvisa.ResourceManager()
    try:
        GMOSRepl(rm).cmdloop()
    finally:
        rm.close()
        if file_handler is not None:
            logger.removeHandler(file_handler)
            file_handler.close()
        logger.propagate = prev_propagate
