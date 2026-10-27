"""Run a PSpice simulation headless and collect text (CSDF) results.

The OrCAD/PSpice-for-TI `pspice.exe -r` batch mode simulates correctly but
keeps its window open afterwards. This script watches the .out file for the
"Total job time" line and then closes only the process it started.

pspice.exe is single-instance. If any PSpice window is already open, a new
launch hands its job over and exits without simulating. The script therefore
runs one simulation at a time (lock file sim-runs/.pspice.lock) and waits
until no other pspice.exe is running. It never closes a PSpice it did not start.

It never touches the Capture-generated files. It copies the profile's .cir into
sim-runs/<name>/, makes every relative .LIB/.INC path absolute, and swaps the
binary .PROBE64 directives for .PROBE/CSDF so results land in a text .csd file.

Usage (from the project root):
    python tools/run_sim.py LIA/lia_sanity
    python tools/run_sim.py differential-amplifier/frequency_analysis --probe "V([HPF])" "V([VSAMPLE])"
    python tools/run_sim.py LIA/lia_sanity --name lia_short --analysis ".TRAN 0 0.2 0 SKIPBP"
    python tools/run_sim.py LIA/lia_sanity --extra ".PARAM f=1k" --timeout 900
    python tools/run_sim.py path/to/custom.cir     # any .cir with absolute or cir-relative paths

<design>/<profile> resolves to ti-pspice-PSpiceFiles/<design>/<profile>/<profile>.cir,
which Capture writes the first time the profile is simulated from the GUI.

Exit code 0 means the job concluded with no ERROR lines in the .out file.
"""

import argparse
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSPICE = r"C:\Cadence\PSpiceTI\tools\bin\pspice.exe"
PSPICE_FILES = os.path.join(ROOT, "ti-pspice-PSpiceFiles")
RUNS = os.path.join(ROOT, "sim-runs")
LOCK = os.path.join(RUNS, ".pspice.lock")

_PATH_DIRECTIVE = re.compile(r'^(\s*\.(?:LIB|INC)\s+")([^"]+)(".*)$', re.IGNORECASE)


def resolve_cir(target):
    if target.lower().endswith(".cir") and os.path.isfile(target):
        return os.path.abspath(target)
    design, _, profile = target.replace("\\", "/").partition("/")
    cir = os.path.join(PSPICE_FILES, design, profile, profile + ".cir")
    if not os.path.isfile(cir):
        sys.exit(f"No circuit file at {cir}. Run the profile once from Capture to generate it.")
    return cir


def _is_signed(path):
    folder, base = os.path.split(path)
    stem = os.path.splitext(base)[0].lower()
    return any(f.lower() == stem + ".libsig" for f in os.listdir(folder))


def _has_lib_sections(path):
    with open(path, "r", errors="replace") as f:
        return any(l.strip().upper().startswith(".ENDL") for l in f)


def normalise_probe(p):
    """PSpice reads V(NAME) as a device voltage and fails with 'Must be a two terminal
    device' for a node. Node voltages need brackets: V([NAME])."""
    m = re.fullmatch(r"\s*V\(\s*([^\[\](),\s]+)\s*\)\s*", p, re.IGNORECASE)
    return f"V([{m.group(1)}])" if m else p


def prepare(cir, out_dir, name, probes, analysis, extra):
    src_dir = os.path.dirname(cir)
    probes = [normalise_probe(p) for p in probes]
    lines_out, missing = [], []
    with open(cir, "r", errors="replace") as f:
        lines = f.read().splitlines()
    for line in lines:
        m = _PATH_DIRECTIVE.match(line)
        if m:
            path = m.group(2)
            candidate = os.path.normpath(os.path.join(src_dir, path.replace("\\", "/")))
            if os.path.exists(candidate):
                prefix = m.group(1)
                # A batch run does not find subcircuits in the unsigned home-made library
                # through .LIB (SPDT_PREC "undefined"), but does through .INC. Signed vendor
                # libraries (with a .LIBsig file) must stay .LIB: as .INC, OPAx192 fails with
                # ORPSIM-16583 "More than one imported model containing transistors or diodes".
                if (prefix.strip().upper().startswith('.LIB') and not _is_signed(candidate)
                        and not _has_lib_sections(candidate)):
                    prefix = prefix.replace(prefix.strip()[:4], ".INC", 1)
                line = f"{prefix}{candidate}{m.group(3)}"
            elif "/" in path or "\\" in path:
                missing.append(path)     # bare names such as nom.lib come from the PSpice library path
        upper = line.strip().upper()
        if upper.startswith(".PROBE"):
            continue
        if analysis and upper.startswith((".TRAN", ".AC", ".DC", ".NOISE", ".STEP")):
            continue
        if upper == ".END":
            if analysis:
                lines_out.extend(analysis)
            lines_out.extend(extra)
            if not any("FILEMODELSEARCH" in l.upper() for l in lines_out):
                lines_out.append(".OPTIONS FILEMODELSEARCH")    # without it .LIB subcircuits are not found
            lines_out.append(".PROBE/CSDF " + " ".join(probes) if probes else ".PROBE/CSDF")
        lines_out.append(line)
    if missing:
        sys.exit("Missing include/library files referenced by the circuit:\n  " + "\n  ".join(missing))
    os.makedirs(out_dir, exist_ok=True)
    run_cir = os.path.join(out_dir, name + ".cir")
    with open(run_cir, "w") as f:
        f.write("\n".join(lines_out) + "\n")
    return run_cir


def other_pspice_pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq pspice.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return [line.split('","')[1] for line in out.splitlines() if line.lower().startswith('"pspice.exe"')]


def wait_for_free_pspice(timeout):
    """pspice.exe is single-instance: a second launch hands its job to the running
    window and exits at once without simulating. So wait until no PSpice is open."""
    start, told = time.time(), False
    while time.time() - start < timeout:
        pids = other_pspice_pids()
        if not pids:
            return True
        if not told:
            print(f"waiting:  another PSpice is open (PID {', '.join(pids)}). It may be another run "
                  "or the user's PSpice window. Runs start when it closes.", flush=True)
            told = True
        time.sleep(3)
    return False


def run(run_cir, timeout, wait):
    base = os.path.splitext(run_cir)[0]
    out_file = base + ".out"
    for ext in (".out", ".csd", ".dat"):
        if os.path.exists(base + ext):
            os.remove(base + ext)
    lock = acquire_lock(wait + timeout)
    try:
        if not wait_for_free_pspice(wait):
            return "busy", out_file, base + ".csd", 0.0
        return _simulate(run_cir, out_file, base, timeout)
    finally:
        if lock:
            os.remove(LOCK)


def acquire_lock(max_age):
    """Serialise runs started through this script. A lock older than max_age is stale."""
    os.makedirs(RUNS, exist_ok=True)
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(LOCK) > max_age:
                    os.remove(LOCK)
                    continue
            except FileNotFoundError:
                continue
            time.sleep(2)


def _simulate(run_cir, out_file, base, timeout):
    proc = subprocess.Popen([PSPICE, "-r", os.path.basename(run_cir)], cwd=os.path.dirname(run_cir))
    start, last_size, last_change = time.time(), -1, time.time()
    status = "timeout"
    try:
        while time.time() - start < timeout:
            time.sleep(1)
            if proc.poll() is not None:
                status = "exited"
                break
            if not os.path.exists(out_file):
                continue
            with open(out_file, "r", errors="replace") as f:
                text = f.read()
            if "Total job time" in text:
                status = "done"
                time.sleep(1)    # let PSpice flush the .csd file
                break
            if len(text) != last_size:
                last_size, last_change = len(text), time.time()
            elif "ERROR" in text and time.time() - last_change > 10:
                status = "error"
                break
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(10)
    return status, out_file, base + ".csd", time.time() - start


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", help="<design>/<profile> or a path to a .cir file")
    p.add_argument("--name", help="run name (default: profile name)")
    p.add_argument("--probe", nargs="*", default=[], help='signals to save, e.g. "V([VX])"; default saves all')
    p.add_argument("--analysis", action="append", default=[],
                   help="replace all analysis lines (.TRAN/.AC/.DC/.NOISE/.STEP) with these; repeatable")
    p.add_argument("--extra", action="append", default=[], help="extra directive added before .END; repeatable")
    p.add_argument("--timeout", type=float, default=600, help="maximum simulation time in seconds")
    p.add_argument("--wait", type=float, default=1800,
                   help="maximum seconds to wait for another open PSpice instance to close")
    a = p.parse_args(argv)

    cir = resolve_cir(a.target)
    name = a.name or os.path.splitext(os.path.basename(cir))[0]
    out_dir = os.path.join(RUNS, name)
    run_cir = prepare(cir, out_dir, name, a.probe, a.analysis, a.extra)
    print(f"circuit: {run_cir}")
    status, out_file, csd, elapsed = run(run_cir, a.timeout, a.wait)

    errors = []
    if os.path.exists(out_file):
        with open(out_file, "r", errors="replace") as f:
            errors = [l.strip() for l in f if "ERROR" in l]
    elif status == "exited":
        errors = ["PSpice exited without writing a .out file. Another PSpice instance probably "
                  "took the job. Close all PSpice windows and run again."]
    elif status == "busy":
        errors = [f"Another PSpice instance stayed open for {a.wait:.0f} s. Close it and run again."]
    print(f"status:  {status} after {elapsed:.0f} s")
    print(f"output:  {out_file}")
    print(f"data:    {csd if os.path.exists(csd) else '(none)'}")
    for e in errors:
        print(f"  {e}")
    return 0 if status == "done" and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
