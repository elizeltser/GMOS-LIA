#!/usr/bin/env python3
"""Sanity checks on a KiCad netlist export (KiCad S-expression format, .net).

Reports:
  SINGLE-NODE   nets with only one connection (excluding KiCad's explicit
                "unconnected-..." nets) - usually mismatched hierarchical labels
  NO-FOOTPRINT  symbols without a footprint
  CAP-ON-R-FP   capacitors placed on a resistor footprint
  NO-VALUE      placeholder values ("C", "R", "L", "?")
  NO-MPN        symbols without an MPN field (only with --mpn)

Usage:
  python3 tools/netcheck.py GMOS-LIA.net [--mpn] [--ignore NET_OR_REF ...]

Exit code 0 if nothing was found, 1 otherwise (usable in CI / pre-commit).
"""
import argparse
import re
import sys


def split_blocks(section: str, keyword: str):
    """Split a top-level section into its '(keyword ...' child blocks."""
    return re.split(r"\n\s*\(" + keyword + r"\s*\n", section)[1:]


def section(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlist", nargs="?", default="GMOS-LIA.net")
    ap.add_argument("--mpn", action="store_true", help="also require an MPN field")
    ap.add_argument("--ignore", nargs="*", default=[],
                    help="net names or refs to ignore (intentional test points, spares)")
    args = ap.parse_args()

    try:
        text = open(args.netlist, encoding="utf-8").read()
    except OSError as e:
        print(f"cannot read {args.netlist}: {e}", file=sys.stderr)
        return 2

    ignore = set(args.ignore)
    findings = []

    # --- nets -------------------------------------------------------------
    for block in split_blocks(section(text, "(nets", None), "net"):
        m = re.search(r'\(name "([^"]*)"', block)
        if not m:
            continue
        name = m.group(1)
        nodes = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', block)
        if (len(nodes) == 1 and not name.startswith("unconnected")
                and name not in ignore and nodes[0][0] not in ignore):
            findings.append(("SINGLE-NODE", f"{name:45s} {nodes[0][0]}.{nodes[0][1]}"))

    # --- components ---------------------------------------------------------
    for c in split_blocks(section(text, "(components", "(libparts"), "comp"):
        ref = re.search(r'\(ref "([^"]+)"', c).group(1)
        if ref in ignore:
            continue
        val_m = re.search(r'\(value "([^"]*)"', c)
        val = val_m.group(1) if val_m else ""
        fp = re.search(r'\(footprint "([^"]+)"', c)
        if not fp:
            findings.append(("NO-FOOTPRINT", f"{ref:6s} {val}"))
        elif re.match(r"C\d", ref) and "Resistor" in fp.group(1):
            findings.append(("CAP-ON-R-FP", f"{ref:6s} {val:8s} {fp.group(1)}"))
        if val in ("C", "R", "L", "") or val.endswith("?"):
            findings.append(("NO-VALUE", f"{ref:6s} '{val}'"))
        if args.mpn and not re.search(r'\(name "(MPN|Manufacturer_Part_Number|PROD_ID)"', c):
            findings.append(("NO-MPN", ref))

    # --- report -------------------------------------------------------------
    order = ["SINGLE-NODE", "NO-FOOTPRINT", "CAP-ON-R-FP", "NO-VALUE", "NO-MPN"]
    for kind in order:
        items = [f for f in findings if f[0] == kind]
        if items:
            print(f"\n{kind} ({len(items)})")
            for _, msg in items:
                print(f"  {msg}")

    counts = ", ".join(f"{k}={sum(1 for f in findings if f[0] == k)}" for k in order)
    print(f"\nSummary: {counts}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
