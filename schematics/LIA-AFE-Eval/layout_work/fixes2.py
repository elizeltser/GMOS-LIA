import pcbnew, sys, math, json
B = sys.argv[1]; D = json.load(open(sys.argv[2])); b = pcbnew.LoadBoard(B); M = 1e6
def V(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def P(q): return (round(q.x / M, 2), round(q.y / M, 2))
T = list(b.GetTracks())
# 1) +5VA: drop the via between R6's pads, run the B stub to the existing via at (79.6, 89.6)
for t in T:
    if t.GetNetname() != '+5VA': continue
    if t.GetClass() == 'PCB_VIA' and P(t.GetPosition()) == (79.6, 88.3): b.Remove(t)
    elif t.GetClass() != 'PCB_VIA' and {P(t.GetStart()), P(t.GetEnd())} == {(79.6, 88.3), (79.6, 89.6)}: b.Remove(t)
    elif t.GetClass() != 'PCB_VIA' and {P(t.GetStart()), P(t.GetEnd())} == {(79.6, 87.5), (79.6, 88.3)}: t.SetEnd(V(79.6, 89.6)) if P(t.GetStart()) == (79.6, 87.5) else t.SetStart(V(79.6, 89.6))
# 2) hole-to-hole: two +5VA vias too close -> keep one, move tracks of the other to it
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == '+5VA']
for x in D['violations']:
    if x['type'] != 'hole_to_hole': continue
    px, py = x['items'][0]['pos']['x'], x['items'][0]['pos']['y']
    near = sorted([v for v in vias if math.hypot(v.GetPosition().x / M - px, v.GetPosition().y / M - py) < 1.0], key=lambda v: v.GetPosition().x)
    if len(near) == 2:
        keep, drop = near; kp, dp = keep.GetPosition(), drop.GetPosition()
        for t in list(b.GetTracks()):
            if t.GetClass() == 'PCB_VIA' or t.GetNetname() != '+5VA': continue
            if t.GetStart() == dp: t.SetStart(kp)
            if t.GetEnd() == dp: t.SetEnd(kp)
        b.Remove(drop); print('merged vias', P(dp), '->', P(kp))
# 3) hair-line misses (< 0.02 mm) between a track and a PTH pad: shift the segment away
def seg_items():
    return [t for t in b.GetTracks() if t.GetClass() != 'PCB_VIA']
for x in D['violations']:
    if x['type'] != 'clearance': continue
    import re
    m = re.search(r"clearance ([\d.]+) mm; actual ([\d.]+)", x['description'])
    if not m: continue
    deficit = float(m.group(1)) - float(m.group(2))
    descs = [i['description'] for i in x['items']]
    if deficit > 0.03 or not any(d.startswith('PTH pad') for d in descs) or not any(d.startswith('Track') for d in descs): continue
    pos = [i['pos'] for i in x['items']]
    pad_i = [k for k, d in enumerate(descs) if d.startswith('PTH')][0]; tr_i = 1 - pad_i
    net = re.search(r'\[([^\]]+)\]', descs[tr_i]).group(1)
    tx, ty = pos[tr_i]['x'], pos[tr_i]['y']
    # find the track segment of that net closest to the reported point
    best = None
    for t in seg_items():
        if t.GetNetname() != net: continue
        s, e = t.GetStart(), t.GetEnd()
        x0, y0, x1, y1 = s.x / M, s.y / M, e.x / M, e.y / M
        L = (x1 - x0) ** 2 + (y1 - y0) ** 2
        u = 0 if L == 0 else max(0, min(1, ((tx - x0) * (x1 - x0) + (ty - y0) * (y1 - y0)) / L))
        dd = math.hypot(tx - (x0 + u * (x1 - x0)), ty - (y0 + u * (y1 - y0)))
        if best is None or dd < best[0]: best = (dd, t)
    t = best[1]
    # pad centre
    padc = None
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.HasHole() and math.hypot(p.GetPosition().x / M - pos[pad_i]['x'], p.GetPosition().y / M - pos[pad_i]['y']) < 1.5:
                padc = p.GetPosition()
    if padc is None: continue
    s, e = t.GetStart(), t.GetEnd()
    mx, my = (s.x + e.x) / 2 / M, (s.y + e.y) / 2 / M
    dx, dy = mx - padc.x / M, my - padc.y / M
    if abs(e.x - s.x) < 10: dy = 0       # vertical segment: move sideways only
    elif abs(e.y - s.y) < 10: dx = 0
    n = math.hypot(dx, dy) or 1; sh = deficit + 0.02
    mv = pcbnew.VECTOR2I(pcbnew.FromMM(dx / n * sh), pcbnew.FromMM(dy / n * sh))
    old = [s, e]
    for o in old:
        for u in seg_items():
            if u.GetNetname() != net: continue
            if u.GetStart() == o: u.SetStart(o + mv)
            elif u.GetEnd() == o: u.SetEnd(o + mv)
    print('nudged', net, round(sh, 3))
# 4) starved thermals: solid connection for those pads
for x in D['violations']:
    if x['type'] != 'starved_thermal': continue
    for i in x['items']:
        d = i['description']
        if 'pad' in d:
            import re
            m = re.search(r'pad (\S+) \[GND\] of (\S+)', d)
            if m:
                for f in b.GetFootprints():
                    if f.GetReference() == m.group(2):
                        for p in f.Pads():
                            if p.GetNumber() == m.group(1): p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL); print('solid', m.group(2), m.group(1))
b.Save(B)
