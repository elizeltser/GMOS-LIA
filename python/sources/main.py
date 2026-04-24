import argparse
import logging
import os
import re
import sys

# Add python/sources/ to path so ATE and setups are importable as top-level packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyvisa
import setups
from setups import SetupBase
from plotting import LIAPhaseZeroPlotCompiler, LIAPlotCompiler, PlotCompiler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _idn(resource: pyvisa.resources.Resource, timeout_ms: int = 2000) -> str:
    orig = resource.timeout
    try:
        resource.timeout = timeout_ms
        idn = resource.query("*IDN?").strip()
        return idn if idn else "(empty response)"
    except Exception:
        return "(no response)"
    finally:
        resource.timeout = orig


def _parse_resource(resource_str: str) -> tuple:
    """Return (interface, info_dict) parsed from a VISA resource string."""
    m = re.match(r'^([A-Za-z]+)', resource_str)
    iface = m.group(1).upper() if m else "UNKNOWN"
    parts = resource_str.split("::")
    info: dict = {}

    if iface == "GPIB":
        # GPIB[board]::primary[::secondary]::INSTR
        info["board"] = parts[0]
        info["address"] = parts[1] if len(parts) > 1 else "?"
    elif iface == "TCPIP":
        # TCPIP[board]::host[::lan_device]::INSTR
        info["host"] = parts[1] if len(parts) > 1 else "?"
        lan = parts[2] if len(parts) > 2 and parts[2] != "INSTR" else None
        if lan:
            info["lan_device"] = lan
    elif iface == "USB":
        # USB[board]::manuf_id::model_code::serial[::iface_num]::INSTR
        info["manuf_id"] = parts[1] if len(parts) > 1 else "?"
        info["model_code"] = parts[2] if len(parts) > 2 else "?"
        info["serial"] = parts[3] if len(parts) > 3 else "?"
    elif iface in ("ASRL", "COM"):
        info["port"] = parts[0]

    return iface, info


_SERIAL_IFACES = {"ASRL", "COM"}

# GPIB primary addresses known to hang with no response — skip during discovery
_GPIB_SKIP_ADDRS = {14, 16}


def list_devices(include_serial: bool = False) -> None:
    rm = pyvisa.ResourceManager()
    try:
        all_resources = rm.list_resources()

        # Filter out serial/tty ports unless explicitly requested
        resources_no_serial = [r for r in all_resources
                               if include_serial or _parse_resource(r)[0] not in _SERIAL_IFACES]
        skipped_serial = len(all_resources) - len(resources_no_serial)

        # Filter out GPIB addresses known to hang with no response
        def _is_skipped_gpib(r: str) -> bool:
            iface, info = _parse_resource(r)
            if iface != "GPIB":
                return False
            try:
                return int(info.get("address", -1)) in _GPIB_SKIP_ADDRS
            except ValueError:
                return False

        resources = [r for r in resources_no_serial if not _is_skipped_gpib(r)]
        skipped_gpib = len(resources_no_serial) - len(resources)

        if not resources:
            print("No VISA resources found (instrument interfaces).")
            if skipped_serial:
                print(f"  ({skipped_serial} serial/tty port(s) hidden)")
            return

        # Group by interface type
        groups: dict = {}
        for r in resources:
            iface, info = _parse_resource(r)
            groups.setdefault(iface, []).append((r, info))

        print(f"\n{'=' * 50}")
        print(f"  VISA Device Discovery  ({len(resources)} resource(s) found)")
        print(f"{'=' * 50}")

        for iface in sorted(groups):
            print(f"\n[{iface}]")
            for resource_str, info in groups[iface]:
                print(f"  {resource_str}")
                if iface == "GPIB":
                    print(f"    Board   : {info['board']}   Primary address: {info['address']}")
                elif iface == "TCPIP":
                    line = f"    Host    : {info['host']}"
                    if info.get("lan_device"):
                        line += f"   LAN device: {info['lan_device']}"
                    print(line)
                elif iface == "USB":
                    print(f"    Manuf   : {info['manuf_id']}   Model: {info['model_code']}   Serial: {info['serial']}")
                elif iface in _SERIAL_IFACES:
                    print(f"    Port    : {info['port']}")
                if iface not in _SERIAL_IFACES:
                    try:
                        with rm.open_resource(resource_str) as res:
                            idn = _idn(res)
                        print(f"    IDN     : {idn}")
                    except Exception as e:
                        print(f"    IDN     : (could not open — {e})")

        if skipped_serial:
            print(f"\n  ({skipped_serial} serial/tty port(s) hidden)")
        if skipped_gpib:
            addrs = ", ".join(str(a) for a in sorted(_GPIB_SKIP_ADDRS))
            print(f"  ({skipped_gpib} GPIB address(es) skipped — known non-responsive: {addrs})")
        print()
    finally:
        rm.close()


def main():
    parser = argparse.ArgumentParser(description="GMOS LIA Experiment Runner")
    parser.add_argument("--experiment", "-e", help="Experiment name")
    parser.add_argument("--config", "-c", help="Config file path")
    parser.add_argument("--list_devices", action="store_true",
                        help="List all available VISA resources and exit")
    parser.add_argument("--scu", default="SCU1",
                        help="SCU device tag to be used for IV sweep (default: SCU1)")
    parser.add_argument("--output-name", metavar="NAME",
                        help="Custom result filename stem (no extension); omit for auto date-stamped name")
    parser.add_argument("--compile-2d-plot", metavar="CSV",
                        help="Path to a result .csv file to compile into a 2D plot")
    parser.add_argument("--compile-lia-plot", metavar="CSV",
                        help="Path to a LIA result .csv file to compile X and R plots")
    parser.add_argument("--compile-lia-phase-zero-plot", metavar="CSV",
                        help="Path to a LIA phase_zero .csv file to compile I_SCU1, I_SCU2, Theta plots")
    parser.add_argument("--x-scale", choices=["linear", "log"], default="linear",
                        help="X-axis scale (default: linear)")
    parser.add_argument("--y-scale", choices=["linear", "log"], default="linear",
                        help="Y-axis scale (default: linear)")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    if args.compile_2d_plot:
        compiler = PlotCompiler(args.compile_2d_plot, x_scale=args.x_scale, y_scale=args.y_scale)
        out_path = compiler.compile()
        print(f"Plot saved to: {out_path}")
        return

    if args.compile_lia_plot:
        compiler = LIAPlotCompiler(args.compile_lia_plot)
        out_path = compiler.compile()
        print(f"Plot saved to: {out_path}")
        return

    if args.compile_lia_phase_zero_plot:
        compiler = LIAPhaseZeroPlotCompiler(args.compile_lia_phase_zero_plot)
        out_path = compiler.compile()
        print(f"Plot saved to: {out_path}")
        return

    if not args.experiment:
        parser.error("--experiment / -e is required unless --list_devices or --compile-2d-plot is used")

    logger.info(f"Starting experiment: {args.experiment}")

    experiment: SetupBase | None = None
    if args.experiment == "IV-voltage-lin":
        experiment = setups.IVSweep(scale="linear", scu_tag=args.scu, mode="voltage", output_name=args.output_name)
        experiment.run()
    elif args.experiment == "IV-voltage-log":
        experiment = setups.IVSweep(scale="log", scu_tag=args.scu, mode="voltage", output_name=args.output_name)
        experiment.run()
    elif args.experiment == "lia":
        experiment = setups.LIAMeasurementSetup(output_name=args.output_name, mode="phase_zero")
        experiment.run()
    else:
        logger.error(f"Unknown experiment: {args.experiment}")
        sys.exit(1)


if __name__ == "__main__":
    main()
