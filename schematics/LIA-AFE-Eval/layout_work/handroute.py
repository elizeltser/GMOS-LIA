# Hand routes of the critical nets (layout_guidelines.md CR-1..CR-3)
import pcbnew, sys
B = sys.argv[1]; b = pcbnew.LoadBoard(B)
F, Bk = pcbnew.F_Cu, pcbnew.B_Cu
for t in list(b.GetTracks()):
    b.Remove(t)
def V(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def line(layer, w, net, pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(x0, y0)); t.SetEnd(V(x1, y1))
        t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)
def via(x, y, net):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
    v.SetLayerPair(F, Bk); v.SetNet(b.FindNet(net)); b.Add(v)
W = 0.25
# CR-1 drain pair. DRN_A: U20.8 (B) -> via -> F.Cu over the mux bodies -> right lane -> U2.2
A = '/DRN_A'
line(Bk, W, A, [(94.22, 68.86), (92.9, 68.86)]); via(92.9, 68.86, A)
line(F, W, A, [(92.9, 68.86), (92.9, 61.0), (112.9, 61.0), (112.9, 103.39), (118.43, 103.39)])
line(F, W, A, [(100.6, 61.0), (100.6, 61.02)])                 # R25.1 (R_D)
line(F, W, A, [(112.9, 100.0), (113.97, 100.0)])               # R90.2 (test resistor)
# DRN_B: U21.8 (B) -> via -> F.Cu left lane -> U2.3, R31 and R91 branches
Bn = '/DRN_B'
line(Bk, W, Bn, [(105.22, 68.86), (104.1, 68.86)]); via(104.1, 68.86, Bn)
line(F, W, Bn, [(104.1, 68.86), (104.1, 70.4), (111.4, 70.4), (111.4, 107.17)])
line(F, W, Bn, [(110.2, 70.4), (110.2, 69.42)])               # R31.1 (R_D)
line(F, W, Bn, [(111.4, 104.67), (118.43, 104.67)])           # U2.3
# CR-2 pixel drains on B.Cu inside the socket (lanes in pin order, no crossings)
P = '/Sensor/PIX_D'
line(Bk, W, P + '3', [(95.53, 68.86), (95.53, 70.0), (94.6, 70.93), (94.6, 79.0), (93.52, 80.08), (93.0, 80.08)])
line(Bk, W, P + '2', [(96.17, 68.86), (96.17, 70.2), (95.4, 70.97), (95.4, 96.8), (94.34, 97.86), (93.0, 97.86)])
line(Bk, W, P + '1', [(96.83, 68.86), (96.83, 70.4), (96.2, 71.03), (96.2, 114.6), (95.16, 115.64), (93.0, 115.64)])
line(Bk, W, P + '6', [(106.53, 68.86), (106.53, 70.0), (105.04, 71.49), (105.04, 119.66), (106.1, 120.72), (108.24, 120.72)])
line(Bk, W, P + '5', [(107.17, 68.86), (107.17, 70.4), (105.84, 71.73), (105.84, 99.34), (106.9, 100.4), (108.24, 100.4)])
line(Bk, W, P + '4', [(107.83, 68.86), (107.83, 70.8), (106.64, 71.99), (106.64, 79.02), (107.7, 80.08), (108.24, 80.08)])
# CR-3 gate: F.Cu spine inside the socket (two planes above the B.Cu drains)
G = '/GATE'; WG = 0.3
line(F, WG, G, [(89.6, 77.6), (90.9, 78.9), (90.9, 85.58)])   # TP11 -> R59.2
line(F, WG, G, [(90.9, 85.58), (91.32, 85.16), (100.6, 85.16)])
line(F, WG, G, [(100.6, 75.0), (100.6, 120.72)])
for y in (102.94, 120.72): line(F, WG, G, [(93.0, y), (100.6, y)])
for y in (75.0, 95.32, 115.64): line(F, WG, G, [(100.6, y), (108.24, y)])
b.Save(B)
print('hand routes added')
