# GND stitching vias: 4 mm grid + 3 mm along the edge, only where every copper layer is free.
# usage: stitch.py BOARD   (zones must exist; refills at the end)
import pcbnew, sys, math
B = sys.argv[1]; b = pcbnew.LoadBoard(B); M = 1e6
VD, DR, CLR, HOLE = 0.6, 0.3, 0.35, 0.55
gnd = b.FindNet('GND')
trk = []; vias = []; pads = []; holes = []
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition(); vias.append((p.x / M, p.y / M, t.GetWidth(pcbnew.F_Cu) / 2 / M, t.GetNetname()))
        holes.append((p.x / M, p.y / M, t.GetDrillValue() / 2 / M))
    else:
        trk.append((t.GetStart().x / M, t.GetStart().y / M, t.GetEnd().x / M, t.GetEnd().y / M, t.GetWidth() / 2 / M, t.GetNetname()))
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        pads.append((bb.GetLeft() / M, bb.GetTop() / M, bb.GetRight() / M, bb.GetBottom() / M, p.GetNetname(), p.HasHole()))
        if p.HasHole(): holes.append((p.GetPosition().x / M, p.GetPosition().y / M, max(p.GetDrillSize().x, p.GetDrillSize().y) / 2 / M))
    cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd).BBox()
def segd(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0; L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - (x0 + u * dx), py - (y0 + u * dy))
def ok(x, y):
    r = VD / 2
    for x0, y0, x1, y1, w, n in trk:
        if n == 'GND': continue
        if min(x0, x1) - 3 < x < max(x0, x1) + 3 and min(y0, y1) - 3 < y < max(y0, y1) + 3:
            if segd(x, y, x0, y0, x1, y1) < r + w + CLR: return False
    for vx, vy, vr, n in vias:
        if math.hypot(x - vx, y - vy) < r + vr + (0.2 if n == 'GND' else CLR): return False
    for hx, hy, hr in holes:
        if math.hypot(x - hx, y - hy) < DR / 2 + hr + HOLE: return False
    for x0, y0, x1, y1, n, th in pads:
        dx = max(x0 - x, 0, x - x1); dy = max(y0 - y, 0, y - y1)
        if math.hypot(dx, dy) < r + (0.25 if n == 'GND' else CLR): return False
    return True
zones = {z.GetLayer(): z for z in b.Zones() if z.GetZoneName().startswith('AUTO_GND')}
def in_pour(x, y):
    v = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
    n = sum(1 for l, z in zones.items() if z.HitTestFilledArea(l, v))
    return n >= 3          # In1 plus at least two more layers
cand = []
for i in range(14):        # edge ring, 3 mm pitch, 1.6 mm in from the edge
    pass
k = 42.0
while k <= 148.0:
    for x, y in ((k, 41.6), (k, 148.4), (51.6, k), (148.4, k)): cand.append((x, y))
    k += 3.0
for gx in range(54, 148, 4):
    for gy in range(44, 148, 4): cand.append((gx + 0.0, gy + 0.0))
# keep the socket interior free of extra vias (drain lanes, gate spine)
cand = [c for c in cand if not (93.5 < c[0] < 107.7 and 73.0 < c[1] < 123.5)]
added = 0
for x, y in cand:
    if (52.5 < x < 147.5 or 42.5 < y < 147.5) and ok(x, y) and in_pour(x, y):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        v.SetWidth(pcbnew.FromMM(VD)); v.SetDrill(pcbnew.FromMM(DR)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(gnd); b.Add(v); vias.append((x, y, VD / 2, 'GND')); holes.append((x, y, DR / 2)); added += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(B)
print('stitching vias added:', added)
