"""Parse PSpice CSDF (.csd) text waveform files.

PSpice writes CSDF when the circuit contains `.PROBE/CSDF`. A file holds one
section per analysis run (a `.STEP` sweep produces one section per step).

Usage:
    python tools/csdf.py FILE.csd --list
    python tools/csdf.py FILE.csd --summary [--signals V(VX) V(VY)]
    python tools/csdf.py FILE.csd --csv OUT.csv [--section 0] [--signals ...]

Library use:
    from csdf import read_csdf
    sections = read_csdf("run.csd")
    s = sections[0]
    s.x            # sweep variable (time or frequency), numpy array
    s["V(VX)"]     # signal by any of its aliases, numpy array (complex for AC)
"""

import argparse
import re
import sys

import numpy as np

_NAME_RE = re.compile(r"'([^']*)'(\s*;)?")


class Section:
    def __init__(self, header, groups, x, data):
        self.header = header      # dict of header keys, e.g. ANALYSIS, SWEEPVAR
        self.groups = groups      # list of alias lists, one per stored node
        self.x = x
        self.data = data          # 2-D array, column i belongs to groups[i]
        self._index = {}
        for i, aliases in enumerate(groups):
            for a in aliases:
                self._index.setdefault(a.upper(), i)

    @property
    def names(self):
        return [g[0] for g in self.groups]

    @property
    def step(self):
        """Step label of a .STEP section, e.g. 'Step param f =  300' (from SUBTITLE)."""
        return self.header.get("STEPVALUE") or self.header.get("SUBTITLE", "").strip()

    @property
    def step_value(self):
        """Numeric step value parsed from the label, or None for an unstepped run."""
        m = re.search(r"=\s*([-+0-9.eE]+)", self.step)
        return float(m.group(1)) if m else None

    def __contains__(self, name):
        return name.upper() in self._index

    def __getitem__(self, name):
        try:
            return self.data[:, self._index[name.upper()]]
        except KeyError:
            raise KeyError(f"{name!r} not found; available: {', '.join(self.names)}")


def _parse_header(text):
    return {k: v for k, v in re.findall(r"(\w+)='([^']*)'", text)}


def _parse_names(text):
    groups, current = [], []
    for m in _NAME_RE.finditer(text):
        current.append(m.group(1))
        if not m.group(2):        # no ';' after the name closes this node's alias group
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _parse_value(tok, complex_values):
    val = tok.split(":")[0]
    if complex_values:
        re_part, im_part = val.split("/")
        return complex(float(re_part), float(im_part))
    return float(val)


def read_csdf(path):
    with open(path, "r", errors="replace") as f:
        text = f.read()
    sections = []
    for chunk in text.split("#H")[1:]:
        head, _, rest = chunk.partition("#N")
        names_txt, _, body = rest.partition("#C")
        header = _parse_header(head)
        groups = _parse_names(names_txt)
        is_complex = header.get("COMPLEXVALUES", "NO").upper() == "YES"
        body = body.split("#;")[0]
        xs, rows = [], []
        for point in ("#C" + body).split("#C")[1:]:
            toks = point.split()
            if len(toks) < 2:
                continue
            xs.append(float(toks[0]))
            rows.append([_parse_value(t, is_complex) for t in toks[2:]])
        dtype = complex if is_complex else float
        data = np.array(rows, dtype=dtype).reshape(len(rows), len(groups))
        sections.append(Section(header, groups, np.array(xs), data))
    return sections


def _select(section, signals):
    if not signals:
        return section.names
    return [s for s in signals]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--list", action="store_true", help="list sections and signal names")
    p.add_argument("--summary", action="store_true", help="min/max/mean/final value per signal")
    p.add_argument("--csv", help="write one section to CSV (AC data as magnitude and phase in degrees)")
    p.add_argument("--section", type=int, default=0)
    p.add_argument("--signals", nargs="*")
    a = p.parse_args(argv)

    sections = read_csdf(a.file)
    if a.list or not (a.summary or a.csv):
        for i, s in enumerate(sections):
            print(f"[{i}] {s.header.get('ANALYSIS')}  sweep={s.header.get('SWEEPVAR')}  "
                  f"points={len(s.x)}  {s.header.get('SUBTITLE', '')}")
            for g in s.groups:
                print("     " + " = ".join(g))
    if a.summary:
        for i, s in enumerate(sections):
            print(f"[{i}] {s.header.get('ANALYSIS')} {s.header.get('SUBTITLE', '')}")
            for name in _select(s, a.signals):
                v = s[name]
                if np.iscomplexobj(v):
                    mag = np.abs(v)
                    k = int(np.argmax(mag))
                    print(f"  {name:20s} |max|={mag[k]:.4g} at {s.x[k]:.4g}  |first|={mag[0]:.4g}  |last|={mag[-1]:.4g}")
                else:
                    print(f"  {name:20s} min={v.min():.4g} max={v.max():.4g} mean={v.mean():.4g} final={v[-1]:.4g}")
    if a.csv:
        s = sections[a.section]
        cols, header = [s.x], [s.header.get("SWEEPVAR", "x")]
        for name in _select(s, a.signals):
            v = s[name]
            if np.iscomplexobj(v):
                cols += [np.abs(v), np.degrees(np.angle(v))]
                header += [f"|{name}|", f"phase({name})"]
            else:
                cols.append(v)
                header.append(name)
        np.savetxt(a.csv, np.column_stack(cols), delimiter=",", header=",".join(header), comments="")
        print(f"wrote {a.csv}")


if __name__ == "__main__":
    sys.exit(main())
