import pcbnew, sys, math
B = sys.argv[1]; b = pcbnew.LoadBoard(B); M = 1e6
F, Bk, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu
def V(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def P(q): return (round(q.x / M, 2), round(q.y / M, 2))
def seg_is(t, a, c, layer=None):
    s, e = P(t.GetStart()), P(t.GetEnd())
    return ({s, e} == {a, c}) and (layer is None or t.GetLayer() == layer)
items = list(b.GetTracks())
rm = []
for t in items:
    n = t.GetNetname()
    if n in ('/DAC6', '/DAC7'): rm.append(t); continue
    if t.GetClass() == 'PCB_VIA':
        p = P(t.GetPosition())
        if (n, p) in (('GND', (76.8, 86.3)), ('/DAC1', (74.5, 84.2)), ('+5VA', (78.0, 87.5))): rm.append(t)
        continue
    for net, a, c in (('GND', (75.71, 86.29), (76.8, 86.3)), ('/DAC1', (74.5, 84.7), (74.5, 85.08)), ('/DAC1', (74.5, 84.2), (74.5, 84.7)),
                      ('/DAC1', (74.5, 55.1), (74.5, 84.2)), ('+5VA', (79.6, 89.6), (78.0, 88.0)), ('+5VA', (78.0, 88.0), (78.0, 87.5))):
        if n == net and seg_is(t, a, c): rm.append(t)
for t in rm: b.Remove(t)
print('removed', len(rm))
def trk(layer, w, net, pts):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)
def via(x, y, net):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetLayerPair(F, Bk); v.SetNet(b.FindNet(net)); b.Add(v)
trk(Bk, 0.25, 'GND', [(75.71, 86.29), (74.95, 86.29)])                       # U8.6 to the exposed pad
trk(Bk, 0.2, '/DAC1', [(74.5, 85.08), (74.5, 83.4)]); via(74.5, 83.4, '/DAC1'); trk(F, 0.2, '/DAC1', [(74.5, 83.4), (74.5, 55.1)])
trk(Bk, 0.25, '+5VA', [(75.71, 86.79), (77.3, 86.79), (78.0, 87.49)])         # U8.7 to C68
trk(Bk, 0.4, '+5VA', [(78.0, 87.5), (81.0, 87.5), (81.0, 87.67)])             # C68 to C67
trk(Bk, 0.4, '+5VA', [(79.6, 87.5), (79.6, 88.3)]); via(79.6, 88.3, '+5VA'); trk(I2, 0.4, '+5VA', [(79.6, 88.3), (79.6, 89.6)])
trk(Bk, 0.25, '/GATE_DC', [(75.71, 87.29), (76.1, 87.29), (76.6, 87.79)]); via(76.6, 87.8, '/GATE_DC')
trk(F, 0.25, '/GATE_DC', [(76.6, 87.8), (77.6, 86.8), (79.9, 86.8), (80.47, 86.23)])
trk(Bk, 0.2, '/DAC0', [(74.0, 85.08), (74.0, 84.4), (73.75, 84.15), (73.75, 84.0)]); via(73.75, 84.0, '/DAC0')
b.Save(B); print('U8 fixes applied')
