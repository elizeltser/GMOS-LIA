# Grid router for LIA-AFE-Eval (runs in KiCad's python).
# usage: route.py board.kicad_pcb [--clear]
import pcbnew, sys, math, heapq, time
import numpy as np

B = sys.argv[1]
b = pcbnew.LoadBoard(B)
M = 1e6
RES = 0.1                      # grid pitch, mm
X0, Y0, NX, NY = 50.0, 40.0, 1000, 1100
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]   # In1 is the solid GND plane
LN = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}
NL = 3
VIA_D, VIA_DRILL = 0.6, 0.3

PARTIAL = '--partial' in sys.argv
HAND = set(t.GetNetname() for t in b.GetTracks())
if '--clear' in sys.argv:
    for t in list(b.GetTracks()):
        b.Remove(t)

def cell(x, y):
    return int(round((x - X0) / RES)), int(round((y - Y0) / RES))

def mm(i, j):
    return X0 + i * RES, Y0 + j * RES

# ---------------------------------------------------------------- net classes
def nclass(net):
    if net == 'GND': return 'GND'
    if net in ('+15V', '-15V', '+5VA', '-5VA', '+5VP', '+3V3') or net.startswith('/Power/'): return 'Power'
    if net.startswith('/Sensor/HTR_') or net.startswith('/Sensor/PIX_H') or net.startswith('/HSENSE_'): return 'Heater'
    if net.startswith('Net-(IC') and net.endswith('-IN+)'): return 'Heater'
    if net.startswith('/DRN_') or net.startswith('/Sensor/PIX_D') or net.startswith('/GATE') \
       or (net.startswith('Net-(IC') and net.endswith('-IN+)')) or net == '/DAC/DAC_REF': return 'Sens'
    if net.startswith('/SPI_') or net == '/DAC_CS' or net.startswith('/MUX') or net in ('/REF_X', '/REF_Y'): return 'Digital'
    return 'Default'

CLR = {'GND': 0.2, 'Power': 0.2, 'Heater': 0.2, 'Sens': 0.3, 'Digital': 0.2, 'Default': 0.2}
WID = {'GND': 0.4, 'Power': 0.4, 'Heater': 0.4, 'Sens': 0.25, 'Digital': 0.2, 'Default': 0.2}
# category of copper for clearance purposes
CAT = {'GND': 0, 'Power': 1, 'Digital': 1, 'Heater': 2, 'Default': 2, 'Sens': 3}

def clearance(ca, cb):
    """ca, cb: categories. returns required clearance (mm)."""
    base = 0.3 if 3 in (ca, cb) else 0.2
    if (ca == 3 and cb == 1) or (cb == 3 and ca == 1): base = 0.5
    return base

# allowed layers, layer cost factors, via cost per class / net
def rules(net, cls):
    if net.startswith('/Sensor/PIX_D'): return [0], [1, 9, 9], 999
    if net.startswith('/DRN_'): return [0, 2], [1, 9, 3], 60
    if net.startswith('/GATE'): return [0, 2], [1.3, 9, 1], 15
    if net == '/DAC/DAC_REF': return [2, 0], [2, 9, 1], 30
    if cls == 'Power': return [0, 1, 2], [3, 1, 3], 4
    if cls == 'Heater': return [0, 1, 2], [1.5, 4, 1.3], 4
    if cls == 'Digital': return [0, 1, 2], [3, 6, 1], 6
    if cls == 'Sens': return [0, 2], [1, 9, 2], 20
    return [0, 1, 2], [1, 6, 1.4], 8

# region cost: digital and heater nets avoid the analog core on the outer layers
CORE = (91, 60, 141, 126)
SENS_AREAS = [((93.9, 73.5, 107.3, 122.5), 8.0), ((110.6, 59.5, 114.0, 108.5), 8.0), ((92.0, 59.8, 113.5, 62.2), 8.0)]
def region_cost(cls, net):
    extra = [] if (net.startswith('/Sensor/PIX_D') or net.startswith('/DRN_') or net == '/GATE') else SENS_AREAS
    return extra + region_cost0(cls, net)
def region_cost0(cls, net):
    if cls == 'Digital' or net in ('/REF_X', '/REF_Y'):
        return [(CORE, 3.0)]
    if cls == 'Heater' and not net.startswith('/Sensor/PIX_H'):
        return [((105, 72, 141, 126), 4.0)]
    return []

# ---------------------------------------------------------------- copper raster
owner = np.full((NL, NY, NX), -1, np.int32)     # net code, -2 = keep-out
netcode = {}
netname = {}
def code(n):
    if n not in netcode:
        netcode[n] = len(netcode); netname[netcode[n]] = n
    return netcode[n]
code('GND')

def stamp_rect(l, x0, y0, x1, y1, c):
    i0, j0 = cell(x0, y0); i1, j1 = cell(x1, y1)
    i0 = max(i0, 0); j0 = max(j0, 0); i1 = min(i1, NX - 1); j1 = min(j1, NY - 1)
    if i1 >= i0 and j1 >= j0:
        owner[l, j0:j1 + 1, i0:i1 + 1] = np.where(owner[l, j0:j1 + 1, i0:i1 + 1] == -1, c, np.where(owner[l, j0:j1 + 1, i0:i1 + 1] == c, c, -2)) if c >= 0 else c

def stamp_disk(l, x, y, r, c):
    ic, jc = cell(x, y); k = int(math.ceil(r / RES))
    j0, j1 = max(jc - k, 0), min(jc + k, NY - 1); i0, i1 = max(ic - k, 0), min(ic + k, NX - 1)
    jj, ii = np.mgrid[j0:j1 + 1, i0:i1 + 1]
    m = ((ii - ic) ** 2 + (jj - jc) ** 2) * RES * RES <= r * r + 1e-9
    sub = owner[l, j0:j1 + 1, i0:i1 + 1]
    if c < 0: sub[m] = c
    else:
        sub[m & (sub == -1)] = c

def poly_mask(pts):
    """even-odd raster of a polygon (list of (x,y) mm)."""
    xs = X0 + np.arange(NX) * RES
    mask = np.zeros((NY, NX), bool)
    n = len(pts)
    ys = Y0 + np.arange(NY) * RES
    for j, y in enumerate(ys):
        xi = []
        for k in range(n):
            (xa, ya), (xb, yb) = pts[k], pts[(k + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xi.append(xa + (y - ya) * (xb - xa) / (yb - ya))
        xi.sort()
        for a, c in zip(xi[0::2], xi[1::2]):
            i0 = int(math.ceil((a - X0) / RES)); i1 = int(math.floor((c - X0) / RES))
            if i1 >= i0: mask[j, max(i0, 0):min(i1, NX - 1) + 1] = True
    return mask

pads_of = {}       # net -> list of pad dicts
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.IsOnCopperLayer(): continue
        n = p.GetNetname()
        if not n or n.startswith('unconnected'): c = -2
        else: c = code(n)
        pos = p.GetPosition(); x, y = pos.x / M, pos.y / M
        bb = p.GetBoundingBox()
        th = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        npth = p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
        if npth or (th and not n and f.GetReference().startswith('H')):
            # mounting hole: outer layers keep-out 1.3 mm beyond the hole + inner 0.5 mm
            r = max(bb.GetWidth(), bb.GetHeight()) / 2 / M
            for l in (0, 2): stamp_disk(l, x, y, r + 1.3, -2)
            stamp_disk(1, x, y, r + 0.5, -2)
            continue
        if th: lays = [0, 1, 2]
        else: lays = [LN[pcbnew.B_Cu]] if f.IsFlipped() else [LN[pcbnew.F_Cu]]
        circ = p.GetShape(pcbnew.F_Cu if not f.IsFlipped() else pcbnew.B_Cu) == pcbnew.PAD_SHAPE_CIRCLE
        for l in lays:
            if circ: stamp_disk(l, x, y, bb.GetWidth() / 2 / M, c)
            else: stamp_rect(l, bb.GetLeft() / M, bb.GetTop() / M, bb.GetRight() / M, bb.GetBottom() / M, c)
        if c >= 0:
            pads_of.setdefault(n, []).append(dict(ref=f.GetReference(), num=p.GetNumber(), x=x, y=y, lays=lays, fx=f.GetPosition().x / M, fy=f.GetPosition().y / M,
                bb=(bb.GetLeft() / M, bb.GetTop() / M, bb.GetRight() / M, bb.GetBottom() / M)))

# existing zones (the owner's input pours) as copper of their net
zone_cells = {}
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    n = z.GetNetname(); c = code(n)
    o = z.Outline().Outline(0)
    pts = [(o.CPoint(k).x / M, o.CPoint(k).y / M) for k in range(o.PointCount())]
    m = poly_mask(pts)
    for li in z.GetLayerSet().Seq():
        if li in LN:
            l = LN[li]
            owner[l][m & (owner[l] == -1)] = c
            zone_cells.setdefault(n, []).append((l, m))

# existing (hand-routed) copper
for t in b.GetTracks():
    c = code(t.GetNetname())
    if t.GetClass() == 'PCB_VIA':
        x, y = t.GetPosition().x / M, t.GetPosition().y / M
        for l in range(NL): stamp_disk(l, x, y, t.GetWidth(pcbnew.F_Cu) / 2 / M, c)
    elif t.GetLayer() in LN:
        l = LN[t.GetLayer()]; w = t.GetWidth() / M
        x0, y0, x1, y1 = t.GetStart().x / M, t.GetStart().y / M, t.GetEnd().x / M, t.GetEnd().y / M
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / (RES / 2)) + 1)
        for k in range(n + 1):
            stamp_disk(l, x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, w / 2, c)

# board edge keep-out (0.5 mm) incl. rounded corners: outside of a 99 mm square with r=4 corners
jj, ii = np.mgrid[0:NY, 0:NX]
xx = X0 + ii * RES; yy = Y0 + jj * RES
edge = (xx < 50.6) | (xx > 149.4) | (yy < 40.6) | (yy > 149.4)
for cx, cy in ((54, 44), (146, 44), (54, 146), (146, 146)):
    q = ((xx - cx) * np.sign(cx - 100) > 0) & ((yy - cy) * np.sign(cy - 95) > 0)
    edge |= q & ((xx - cx) ** 2 + (yy - cy) ** 2 > (4 - 0.6) ** 2)
for l in range(NL): owner[l][edge] = -2
del jj, ii, xx, yy

# ---------------------------------------------------------------- hole-to-hole map (0.5 mm between drill edges)
VH = bytearray(NX * NY)
def mark_hole(x, y, rh):
    r = rh + 0.5 + VIA_DRILL / 2 + 0.05
    ic, jc = cell(x, y); k = int(math.ceil(r / RES))
    for dj in range(-k, k + 1):
        for di in range(-k, k + 1):
            if (dj * dj + di * di) * RES * RES <= r * r:
                i, j = ic + di, jc + dj
                if 0 <= i < NX and 0 <= j < NY: VH[j * NX + i] = 1
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA': mark_hole(t.GetPosition().x / M, t.GetPosition().y / M, t.GetDrillValue() / 2 / M)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.HasHole(): mark_hole(p.GetPosition().x / M, p.GetPosition().y / M, max(p.GetDrillSize().x, p.GetDrillSize().y) / 2 / M)

# ---------------------------------------------------------------- helpers
def disk_offsets(r_cells):
    k = int(math.ceil(r_cells))
    return [(dj, di) for dj in range(-k, k + 1) for di in range(-k, k + 1) if dj * dj + di * di <= r_cells * r_cells + 1e-6]

def dilate(mask, r_mm):
    out = mask.copy()
    if r_mm <= 0: return out
    for dj, di in disk_offsets(r_mm / RES):
        if dj == 0 and di == 0: continue
        sj0, sj1 = max(0, -dj), NY - max(0, dj); si0, si1 = max(0, -di), NX - max(0, di)
        out[sj0 + dj:sj1 + dj, si0 + di:si1 + di] |= mask[sj0:sj1, si0:si1]
    return out

net_cat_arr = None
def cat_of_codes():
    arr = np.zeros(len(netcode) + 2, np.int8)
    for n, c in netcode.items(): arr[c] = CAT[nclass(n)]
    return arr

KEEPOUT = [((0, 1, 2), (94.0, 73.4, 107.2, 123.0), True),   # socket interior: drain lanes (B) and gate spine (F) only
           ((1,), (92.0, 66.5, 111.2, 74.5), False),          # In2 tracks: keep the plane solid under the mux drain pins
           ((0,), (109.1, 72.0, 114.2, 108.5), True)]          # F.Cu: gap between socket and drain lanes
def exempt(n): return n == 'GND' or n == '/GATE' or n.startswith('/Sensor/PIX_D') or n.startswith('/DRN_')
def blocked_for(c, cls, w):
    """per layer bool masks: True where a track centre (width w) of net c may NOT go;
       and a via mask."""
    cats = cat_of_codes()
    mycat = CAT[cls]
    track = np.zeros((NL, NY, NX), bool)
    via = np.zeros((NY, NX), bool)
    for l in range(NL):
        o = owner[l]
        hard = o == -2
        track[l] |= dilate(hard, w / 2 + 0.25)
        via |= dilate(hard, VIA_D / 2 + 0.25)
        foreign = (o >= 0) & (o != c)
        if not foreign.any(): continue
        oc = np.where(foreign, cats[np.maximum(o, 0)], -1)
        for k in range(4):
            mk = oc == k
            if not mk.any(): continue
            cl = clearance(mycat, k)
            track[l] |= dilate(mk, cl + w / 2 + 0.07)
            via |= dilate(mk, cl + VIA_D / 2 + 0.07)
    # vias of other nets: hole-to-hole spacing is covered by the copper clearance on all layers
    if not exempt(netname[c]):
        for lays_k, (x0, y0, x1, y1), vk in KEEPOUT:
            i0, j0 = cell(x0, y0); i1, j1 = cell(x1, y1)
            for l in lays_k: track[l, j0:j1 + 1, i0:i1 + 1] = True
            if vk: via[j0:j1 + 1, i0:i1 + 1] = True
    return track, via

# ---------------------------------------------------------------- A*
SQ2 = math.sqrt(2)
DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]

OWNV = set()
def astar(srcs, tgt_set, tgt_xy, free, viaok, lays, lcost, vcost, regcost, maxexp=300000, hw=1.3):
    NXY = NX * NY
    tx, ty = tgt_xy
    def h(i, j):
        dx = abs(i - tx); dy = abs(j - ty)
        return (max(dx, dy) + (SQ2 - 1) * min(dx, dy)) * hw
    g = {}; prev = {}; pq = []
    for (l, i, j) in srcs:
        s = l * NXY + j * NX + i
        g[s] = 0.0; prev[s] = -1
        heapq.heappush(pq, (h(i, j), 0.0, s))
    exp = 0
    while pq:
        f, gc, s = heapq.heappop(pq)
        if gc > g.get(s, 1e18) + 1e-9: continue
        if s in tgt_set:
            path = []
            while s != -1:
                path.append(s); s = prev[s]
            return path[::-1]
        exp += 1
        if exp > maxexp: return None
        l = s // NXY; r = s - l * NXY; j = r // NX; i = r - j * NX
        fl = free[l]; lc = lcost[l]
        for di, dj, dc in DIRS:
            ni = i + di; nj = j + dj
            if ni < 0 or nj < 0 or ni >= NX or nj >= NY: continue
            ns = s + dj * NX + di
            nr = r + dj * NX + di
            if not fl[nr] and ns not in tgt_set: continue
            if di and dj and not (fl[r + di] and fl[r + dj * NX]) and ns not in tgt_set: continue
            c = dc * lc * regcost[l][nr]
            ng = gc + c
            if ng < g.get(ns, 1e18):
                g[ns] = ng; prev[ns] = s
                heapq.heappush(pq, (ng + h(ni, nj), ng, ns))
        if viaok[r] and (not VH[r] or r in OWNV):
            for nl in lays:
                if nl == l or not free[nl][r]: continue
                ns = nl * NXY + r
                ng = gc + vcost
                if ng < g.get(ns, 1e18):
                    g[ns] = ng; prev[ns] = s
                    heapq.heappush(pq, (ng + h(i, j), ng, ns))
    return None

# ---------------------------------------------------------------- board output
def add_track(l, x0, y0, x1, y1, w, n):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(LAYERS[l]); t.SetNet(b.FindNet(n)); b.Add(t)

def add_via(x, y, n):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(b.FindNet(n)); b.Add(v)

def emit(path, w, n, c):
    NXY = NX * NY
    pts = []
    for s in path:
        l = s // NXY; r = s - l * NXY; j = r // NX; i = r - j * NX
        pts.append((l, i, j))
    # stamp copper
    for (l, i, j) in pts:
        x, y = mm(i, j); stamp_disk(l, x, y, w / 2, c)
    # segments
    k = 0
    while k < len(pts) - 1:
        l, i, j = pts[k]
        if pts[k + 1][0] != l:          # via
            x, y = mm(i, j); add_via(x, y, n); mark_hole(x, y, VIA_DRILL / 2)
            for ll in range(NL): stamp_disk(ll, x, y, VIA_D / 2, c)
            k += 1; continue
        di = pts[k + 1][1] - i; dj = pts[k + 1][2] - j
        m = k + 1
        while m + 1 < len(pts) and pts[m + 1][0] == l and pts[m + 1][1] - pts[m][1] == di and pts[m + 1][2] - pts[m][2] == dj:
            m += 1
        x0, y0 = mm(i, j); x1, y1 = mm(pts[m][1], pts[m][2])
        add_track(l, x0, y0, x1, y1, w, n)
        k = m
    return pts

def pad_cells(p, lays_allowed):
    x0, y0, x1, y1 = p['bb']
    i0, j0 = cell(x0, y0); i1, j1 = cell(x1, y1)
    # shrink to the inner part of the pad so stubs stay inside the copper
    out = []
    for l in p['lays']:
        if l not in lays_allowed: continue
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                x, y = mm(i, j)
                if x0 + 0.02 <= x <= x1 - 0.02 and y0 + 0.02 <= y <= y1 - 0.02:
                    out.append((l, i, j))
    return out

# ---------------------------------------------------------------- GND fan-out
def gnd_fanout():
    c = netcode['GND']; nadd = 0
    track, via = blocked_for(c, 'GND', 0.25)
    via = dilate(via, 0.2)
    for p in pads_of.get('GND', []):
        if len(p['lays']) == 3: continue          # TH pad reaches In1 directly
        l = p['lays'][0]
        # skip pads inside a GND zone (the owner's input pours)
        cx, cy = cell(p['x'], p['y'])
        if any(zl == l and zm[cy, cx] for zl, zm in zone_cells.get('GND', [])): continue
        best = None
        big = (p['bb'][2] - p['bb'][0]) * (p['bb'][3] - p['bb'][1]) > 1.5
        ox, oy = p['x'] - p['fx'], p['y'] - p['fy']
        a0 = math.degrees(math.atan2(oy, ox)) if math.hypot(ox, oy) > 0.05 else 0
        angs = sorted(range(0, 360, 15), key=lambda a: abs((a - a0 + 180) % 360 - 180))
        for rr in ([0.0] if big else []) + [x * 0.1 for x in range(4, 36)]:
            for a in angs:
                if abs((a - a0 + 180) % 360 - 180) > 100 and rr < 2.0: continue
                x = p['x'] + rr * math.cos(math.radians(a)); y = p['y'] + rr * math.sin(math.radians(a))
                i, j = cell(x, y)
                if 0 <= i < NX and 0 <= j < NY and not via[j, i] and not VH[j * NX + i]:
                    # straight stub must be free on the pad layer
                    ok = True
                    for t in np.linspace(0, 1, 16):
                        px, py = p['x'] + (x - p['x']) * t, p['y'] + (y - p['y']) * t
                        x0b, y0b, x1b, y1b = p['bb']
                        if x0b <= px <= x1b and y0b <= py <= y1b: continue
                        ii, jj2 = cell(px, py)
                        if track[l, jj2, ii]: ok = False; break
                    if ok: best = (x, y); break
            if best: break
        if not best:
            print('  no GND via for', p['ref'], p['num']); continue
        x, y = mm(*cell(*best))
        add_via(x, y, 'GND'); mark_hole(x, y, VIA_DRILL / 2)
        if math.hypot(x - p['x'], y - p['y']) > 0.05: add_track(l, p['x'], p['y'], x, y, 0.25, 'GND')
        i2, j2 = cell(p['x'], p['y'])
        for tt in np.linspace(0, 1, 16): stamp_disk(l, p['x'] + (x - p['x']) * tt, p['y'] + (y - p['y']) * tt, 0.125, c)
        for ll in range(NL): stamp_disk(ll, x, y, VIA_D / 2, c)
        # update via mask locally so the next via keeps its distance
        i, j = cell(x, y); k = int((VIA_D + 0.25) / RES) + 1
        jj, ii = np.mgrid[max(j - k, 0):j + k + 1, max(i - k, 0):i + k + 1]
        via[max(j - k, 0):j + k + 1, max(i - k, 0):i + k + 1] |= ((ii - i) ** 2 + (jj - j) ** 2) * RES * RES <= (VIA_D + 0.25) ** 2
        track[l][max(j - k, 0):j + k + 1, max(i - k, 0):i + k + 1] |= ((ii - i) ** 2 + (jj - j) ** 2) * RES * RES <= (VIA_D / 2 + 0.45) ** 2
        nadd += 1
    print('GND vias:', nadd)

# ---------------------------------------------------------------- net routing
def complete_net(n):
    b.BuildConnectivity(); con = b.GetConnectivity()
    c = netcode[n]; cls = nclass(n); lays, lcost, vcost = rules(n, cls)
    pobj = {}
    for f in b.GetFootprints():
        for q in f.Pads():
            if q.GetNetname() == n: pobj[(f.GetReference(), q.GetNumber())] = q
    pd = {(p['ref'], p['num']): p for p in pads_of[n]}
    seen = set(); clusters = []
    for key, q in pobj.items():
        if key in seen: continue
        cl = {key}
        for it in con.GetConnectedItems(q):
            if it.GetClass() != 'PAD': continue
            q2 = it.Cast() if hasattr(it, 'Cast') else it
            k2 = (q2.GetParentFootprint().GetReference(), q2.GetNumber())
            if k2 in pd: cl.add(k2)
        seen |= cl; clusters.append(cl)
    clusters.sort(key=len, reverse=True)
    print('   clusters', [len(x) for x in clusters])
    if len(clusters) < 2: return True
    w = WID[cls]
    ok = True
    OWNV.clear()
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == n:
            i, j = cell(t.GetPosition().x / M, t.GetPosition().y / M); OWNV.add(j * NX + i)
    for w in (WID[cls], 0.25, 0.2):
        track, via = blocked_for(c, cls, w)
        free = [bytes((~track[l]).ravel().astype(np.uint8)) if l in lays else bytes(NX * NY) for l in range(NL)]
        viaok = bytes((~via).ravel().astype(np.uint8))
        regcost = [[1.0] * (NX * NY) for l in range(NL)]
        tree = [cc for k in clusters[0] for cc in pad_cells(pd[k], lays)]
        rest = []
        for cl in clusters[1:]:
            tcells = [cc for k in cl for cc in pad_cells(pd[k], lays)]
            NXY = NX * NY
            tset = set(l * NXY + j * NX + i for (l, i, j) in tcells)
            k0 = next(iter(cl)); p = pd[k0]
            path = astar(tree, tset, cell(p['x'], p['y']), free, viaok, lays, lcost, vcost, regcost, maxexp=3000000)
            if path is None: rest.append(cl); continue
            pts = emit(path, w, n, c)
            l1, i1, j1 = pts[-1]; x1, y1 = mm(i1, j1)
            pe = min((pd[k] for k in cl), key=lambda q: (q['x'] - x1) ** 2 + (q['y'] - y1) ** 2)
            add_track(l1, x1, y1, pe['x'], pe['y'], min(w, 0.25), n)
            l0, i0, j0 = pts[0]; x0, y0 = mm(i0, j0)
            ps = min((pd[k] for k in clusters[0]), key=lambda q: (q['x'] - x0) ** 2 + (q['y'] - y0) ** 2)
            if l0 in ps['lays'] and ps['bb'][0] <= x0 <= ps['bb'][2] and ps['bb'][1] <= y0 <= ps['bb'][3]:
                add_track(l0, x0, y0, ps['x'], ps['y'], min(w, 0.25), n)
            tree += pts + tcells
        if not rest: return True
        print('   still unconnected', [sorted(r) for r in rest], 'at width', w)
        clusters = [clusters[0]] + rest
    return False

def route_net(n, widths=None):
    if '--complete' in sys.argv: return complete_net(n)
    c = netcode[n]; cls = nclass(n)
    lays, lcost, vcost = rules(n, cls)
    pads = pads_of[n]
    if len(pads) < 2: return True
    regs = region_cost(cls, n)
    regcost = []
    for l in range(NL):
        rc = np.ones((NY, NX), np.float32)
        if l != 1:
            for (x0, y0, x1, y1), k in regs:
                i0, j0 = cell(x0, y0); i1, j1 = cell(x1, y1); rc[j0:j1, i0:i1] = np.maximum(rc[j0:j1, i0:i1], k)
        regcost.append(rc.ravel().tolist())
    for w in (widths or [WID[cls], 0.25, 0.2]):
        if w > WID[cls]: continue
        track, via = blocked_for(c, cls, w)
        # pad exits: a strip along each own pad's centre lines, 0.35 mm beyond the pad
        for p in (pads if w <= 0.25 else []):
            x0, y0, x1, y1 = p['bb']; cxp, cyp = (x0 + x1) / 2, (y0 + y1) / 2
            for l in p['lays']:
                if l not in lays: continue
                for (ax0, ay0, ax1, ay1) in ((x0 - 0.35, cyp - 0.05, x1 + 0.35, cyp + 0.05), (cxp - 0.05, y0 - 0.35, cxp + 0.05, y1 + 0.35), (x0, y0, x1, y1)):
                    i0, j0 = cell(ax0, ay0); i1, j1 = cell(ax1, ay1)
                    j0, i0 = max(j0, 0), max(i0, 0)
                    sub = owner[l, j0:j1 + 1, i0:i1 + 1]
                    track[l, j0:j1 + 1, i0:i1 + 1] &= ~((sub == -1) | (sub == c))
        free = [bytes((~track[l]).ravel().astype(np.uint8)) if l in lays else bytes(NX * NY) for l in range(NL)]
        viaok = bytes((~via).ravel().astype(np.uint8))
        # tree: start with the pad nearest to the centroid
        cx = sum(p['x'] for p in pads) / len(pads); cy = sum(p['y'] for p in pads) / len(pads)
        order = sorted(pads, key=lambda p: (p['x'] - cx) ** 2 + (p['y'] - cy) ** 2)
        tree = []
        tree += pad_cells(order[0], lays)
        # zones of this net are part of the tree
        left = order[1:]
        okall = True; emitted = []
        while left:
            # nearest remaining pad to the tree
            tx = [mm(t[1], t[2]) for t in tree[::7]] or [(order[0]['x'], order[0]['y'])]
            left.sort(key=lambda p: min((p['x'] - a) ** 2 + (p['y'] - bb) ** 2 for a, bb in tx))
            p = left.pop(0)
            tcells = pad_cells(p, lays)
            if not tcells: okall = False; break
            NXY = NX * NY
            tset = set(l * NXY + j * NX + i for (l, i, j) in tcells)
            srcs = [t for t in tree if free[t[0]][t[2] * NX + t[1]]] or tree
            dist = math.hypot(p['x'] - order[0]['x'], p['y'] - order[0]['y'])
            path = astar(srcs, tset, cell(p['x'], p['y']), free, viaok, lays, lcost, vcost, regcost, maxexp=300000 if dist < 30 else 3000000, hw=1.3 if dist < 30 else 2.0)
            if path is None:
                if PARTIAL: print('   unreached', n, p['ref'], p['num']); continue
                okall = False; break
            pts = emit(path, w, n, c)
            # pad-centre stubs (keep connection exact)
            l0, i0, j0 = pts[0]; l1, i1, j1 = pts[-1]
            x1, y1 = mm(i1, j1)
            if math.hypot(x1 - p['x'], y1 - p['y']) > 0.01: add_track(l1, x1, y1, p['x'], p['y'], min(w, 0.25), n)
            x0, y0 = mm(i0, j0)
            src_pad = min(pads, key=lambda q: (q['x'] - x0) ** 2 + (q['y'] - y0) ** 2)
            if l0 in src_pad['lays'] and src_pad['bb'][0] <= x0 <= src_pad['bb'][2] and src_pad['bb'][1] <= y0 <= src_pad['bb'][3] \
               and math.hypot(x0 - src_pad['x'], y0 - src_pad['y']) > 0.01:
                add_track(l0, x0, y0, src_pad['x'], src_pad['y'], min(w, 0.25), n)
            tree += pts + tcells
            # free mask must now include own new copper: own copper never blocks, nothing to do
        if okall: return True
        print('   retry', n, 'width', w)
        # remove what was emitted for this net and un-stamp
        for t in list(b.GetTracks()):
            if t.GetNetname() == n: b.Remove(t)
        for l in range(NL):
            o = owner[l]; o[o == c] = -1
        restamp(n)
    return False

def restamp(n):
    c = netcode[n]
    for p in pads_of[n]:
        for l in p['lays']:
            stamp_rect(l, *p['bb'], c)
    for l, m in zone_cells.get(n, []):
        owner[l][m & (owner[l] == -1)] = c

# ---------------------------------------------------------------- main
t0 = time.time()
if 'GND' not in HAND: gnd_fanout()
_only = [a for a in sys.argv[2:] if not a.startswith('--')]
nets = [n for n in pads_of if n != 'GND' and len(pads_of[n]) >= 2 and (n not in HAND or n in _only)]
def hpwl(n):
    xs = [p['x'] for p in pads_of[n]]; ys = [p['y'] for p in pads_of[n]]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))
prio = ['/DRN_A', '/DRN_B'] + sorted([n for n in nets if n.startswith('/Sensor/PIX_D')]) + ['/GATE', '/DAC/DAC_REF']
rest = sorted([n for n in nets if n not in prio], key=lambda n: (nclass(n) in ('Power',), nclass(n) == 'Digital', hpwl(n)))
order = [n for n in prio if n in nets] + rest
import os
if os.path.exists('first.txt'):
    first = [l.strip() for l in open('first.txt') if l.strip()]
    order = [n for n in first if n in order] + [n for n in order if n not in first]
only = [a for a in sys.argv[2:] if not a.startswith('--')]
if only: order = [n for n in order if n in only]
failed = []
for n in order:
    ts = time.time()
    ok = route_net(n)
    print('%-28s %-8s %s %.1fs' % (n, nclass(n), 'ok' if ok else 'FAILED', time.time() - ts), flush=True)
    if not ok: failed.append(n)
print('failed:', failed, 'total %.0fs' % (time.time() - t0))
open('failed.txt','w').write(chr(10).join(failed))
b.Save(B)
