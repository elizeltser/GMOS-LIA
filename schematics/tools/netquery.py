#!/usr/bin/env python3
"""Query a KiCad netlist (.net, S-expression) and assert expected connections.

Pin references:
  U5.9         reference + pin NUMBER
  U12:PA4      reference + pin NAME (KiCad pinfunction, trailing "_<num>" ignored,
               alternate names after "/" also match, e.g. U7:AIN0 matches AIN0/REFP1)

Commands:
  netquery.py NETLIST net   PIN            print the net of PIN and all its members
  netquery.py NETLIST part  REF            print value, footprint, MPN, datasheet, sheet
  netquery.py NETLIST check FILE [FILE..]  run assertions from check files (exit 1 on failure)

Check-file syntax (one assertion per line, '#' starts a comment):
  same   PIN PIN [PIN ...]     all pins on one net
  diff   PIN PIN               pins on different nets
  nc     PIN                   pin unconnected (no other member on its net)
  conn   PIN                   pin connected to at least one other pin
  name   PIN SUBSTRING         net name of PIN contains SUBSTRING (case-insensitive)
  between REF A B              2-pin part REF sits between A and B, in either orientation.
                               A/B are pins (U4.2, U4:-) or @SUBSTRING (a net whose name
                               contains SUBSTRING, e.g. @GND, @VMID)
  value  REF TEXT              value field equals TEXT
  valuein REF SUBSTRING        value field contains SUBSTRING
  fp     REF SUBSTRING         footprint contains SUBSTRING
  field  REF FIELD SUBSTRING   custom field (e.g. MPN) contains SUBSTRING
  exists REF                   component exists
  absent REF                   component does not exist
"""
import re
import sys


def load(path):
    text = open(path, encoding="utf-8").read()
    comps = {}
    csec = text[text.index("(components"):text.index("(libparts")]
    for c in re.split(r"\n\s*\(comp\s*\n", csec)[1:]:
        ref = re.search(r'\(ref "([^"]+)"', c).group(1)
        d = {"value": "", "footprint": "", "datasheet": "", "sheet": "", "fields": {}}
        for k in ("value", "footprint", "datasheet"):
            m = re.search(r'\(%s "([^"]*)"' % k, c)
            if m:
                d[k] = m.group(1)
        m = re.search(r'\(sheetpath\s*\(names "([^"]*)"', c)
        if m:
            d["sheet"] = m.group(1)
        for name, val in re.findall(r'\(field\s*\(name "([^"]+)"\)\s*"([^"]*)"\)', c):
            d["fields"][name] = val
        comps[ref] = d

    pin_net, net_members, pin_name = {}, {}, {}
    nsec = text[text.index("(nets"):]
    for b in re.split(r"\n\s*\(net\s*\n", nsec)[1:]:
        name = re.search(r'\(name "([^"]*)"', b).group(1)
        nodes = re.findall(
            r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)\s*(?:\(pinfunction "([^"]*)"\))?', b)
        net_members[name] = [(r, p) for r, p, _ in nodes]
        for r, p, f in nodes:
            pin_net[(r, p)] = name
            if f:
                base = f[: -len(p) - 1] if f.endswith("_" + p) else f
                pin_name[(r, p)] = [base] + base.split("/")
    return comps, pin_net, net_members, pin_name


def resolve(pin, pin_net, pin_name):
    if "." in pin and ":" not in pin:
        ref, num = pin.split(".", 1)
        return (ref, num) if (ref, num) in pin_net else None
    ref, name = pin.split(":", 1)
    exact = [k for k, names in pin_name.items() if k[0] == ref and names[0] == name]
    hits = exact or [k for k, names in pin_name.items() if k[0] == ref and name in names]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError(f"ambiguous pin name {pin}: {sorted(hits)}; use REF.NUMBER")
    return None


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    path, cmd, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    comps, pin_net, members, pin_name = load(path)

    if cmd == "net":
        k = resolve(args[0], pin_net, pin_name)
        if not k:
            print(f"{args[0]}: not found")
            return 1
        n = pin_net[k]
        print(f"{args[0]} -> {n}")
        print("  " + " ".join(f"{r}.{p}" for r, p in members[n]))
        return 0

    if cmd == "part":
        d = comps.get(args[0])
        if not d:
            print(f"{args[0]}: not found")
            return 1
        for k in ("value", "footprint", "datasheet", "sheet"):
            print(f"{k:10s}{d[k]}")
        for k, v in d["fields"].items():
            print(f"{k:10s}{v}")
        return 0

    if cmd != "check":
        print(__doc__)
        return 2

    fails = total = 0
    for f in args:
        for lineno, line in enumerate(open(f, encoding="utf-8"), 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            total += 1
            tok = line.split()
            op, rest = tok[0], tok[1:]
            ok, msg = False, ""
            try:
                if op in ("same", "diff", "nc", "conn", "name"):
                    keys = [resolve(p, pin_net, pin_name) for p in
                            (rest if op == "same" else rest[:2] if op == "diff" else rest[:1])]
                    if None in keys:
                        missing = [p for p, k in zip(rest, keys) if k is None]
                        ok, msg = False, f"pin not found: {missing}"
                    elif op == "same":
                        nets = {pin_net[k] for k in keys}
                        ok, msg = len(nets) == 1, f"nets: {sorted(nets)}"
                    elif op == "diff":
                        a, b = pin_net[keys[0]], pin_net[keys[1]]
                        ok, msg = a != b, f"both on {a}"
                    elif op == "nc":
                        n = pin_net[keys[0]]
                        ok, msg = len(members[n]) == 1, f"{n}: {len(members[n])} members"
                    elif op == "conn":
                        n = pin_net[keys[0]]
                        ok, msg = len(members[n]) > 1, f"{n}: only this pin"
                    elif op == "name":
                        n = pin_net[keys[0]]
                        ok, msg = rest[1].lower() in n.lower(), f"net is {n}"
                elif op == "between":
                    ref, a, b = rest[0], rest[1], rest[2]
                    pins = sorted(p for (r, p) in pin_net if r == ref)
                    if len(pins) != 2:
                        ok, msg = False, f"{ref} has pins {pins} (needs exactly 2 connected)"
                    else:
                        nets = [pin_net[(ref, p)] for p in pins]

                        def match(spec, net):
                            if spec.startswith("@"):
                                s = spec[1:].lower()
                                n = net.lower()
                                return n == s or n.endswith("/" + s) or s in n.split("/")[-1]
                            k = resolve(spec, pin_net, pin_name)
                            return k is not None and pin_net[k] == net

                        ok = (match(a, nets[0]) and match(b, nets[1])) or \
                             (match(a, nets[1]) and match(b, nets[0]))
                        msg = f"{ref} is between {nets[0]} and {nets[1]}"
                elif op in ("value", "valuein", "fp", "field", "exists", "absent"):
                    d = comps.get(rest[0])
                    if op == "absent":
                        ok, msg = d is None, "still present"
                    elif d is None:
                        ok, msg = False, "component not found"
                    elif op == "exists":
                        ok = True
                    elif op == "value":
                        ok, msg = d["value"] == " ".join(rest[1:]), f"value is '{d['value']}'"
                    elif op == "valuein":
                        ok, msg = rest[1].lower() in d["value"].lower(), f"value is '{d['value']}'"
                    elif op == "fp":
                        ok, msg = rest[1] in d["footprint"], f"footprint is '{d['footprint']}'"
                    elif op == "field":
                        v = d["fields"].get(rest[1], "")
                        ok, msg = rest[2].lower() in v.lower(), f"{rest[1]} is '{v}'"
                else:
                    msg = f"unknown op {op}"
            except Exception as e:  # malformed line
                ok, msg = False, f"error: {e}"
            if not ok:
                fails += 1
                print(f"FAIL {f}:{lineno}: {line}   [{msg}]")
    print(f"{total - fails}/{total} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())