# Bring PCB pad nets in line with the schematic netlist; restore TP6; strip copper and AUTO zones.
import pcbnew, sys, re
import json
B, NET = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(B)
pin_net = {(r, p): n for r, p, n in json.load(open(NET))}
_trk = list(b.GetTracks()); _zn = list(b.Zones())
for t in _trk: b.Remove(t)
for z in _zn:
    if z.GetZoneName().startswith('AUTO_GND'): b.Remove(z)
fps = {f.GetReference(): f for f in b.GetFootprints()}
if 'TP6' not in fps:
    src = fps['TP7']
    f = pcbnew.Cast_to_FOOTPRINT(src.Duplicate(False))
    f.SetReference('TP6'); f.SetValue('EXC_DAC')
    path = src.GetPath().AsString().split('/')
    path[-1] = '80158e87-13bb-4c90-ad2a-63466e9f5cfa'
    f.SetPath(pcbnew.KIID_PATH('/'.join(path)))
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(71.0), pcbnew.FromMM(94.4)))
    b.Add(f); fps['TP6'] = f; print('TP6 restored at (71.0, 94.4)')
nets = {}
def net(n):
    ni = b.FindNet(n)
    if ni is None or ni.GetNetCode() <= 0:
        ni = pcbnew.NETINFO_ITEM(b, n); b.Add(ni); print('added net', n)
    return ni
changed = 0
for (r, pnum), n in pin_net.items():
    if r not in fps: print('missing footprint', r); continue
    for p in fps[r].Pads():
        if p.GetNumber() == pnum and p.GetNetname() != n:
            if n.startswith('unconnected'): continue
            print('  %s.%s %s -> %s' % (r, pnum, p.GetNetname(), n)); p.SetNet(net(n)); changed += 1
print('pad nets changed:', changed)
b.Save(B)
