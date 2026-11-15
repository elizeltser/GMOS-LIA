# GND pours on all four layers (In1 solid plane), then fill.
import pcbnew, sys
B = sys.argv[1]; b = pcbnew.LoadBoard(B)
def V(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
for z in list(b.Zones()):
    if z.GetZoneName().startswith('AUTO_GND'): b.Remove(z)
gnd = b.FindNet('GND')
for li, name in ((pcbnew.In1_Cu, 'AUTO_GND_In1'), (pcbnew.In2_Cu, 'AUTO_GND_In2'), (pcbnew.F_Cu, 'AUTO_GND_F'), (pcbnew.B_Cu, 'AUTO_GND_B')):
    z = pcbnew.ZONE(b); z.SetLayer(li); z.SetNet(gnd); z.SetZoneName(name)
    o = z.Outline(); o.NewOutline()
    for x, y in ((50.5, 40.5), (149.5, 40.5), (149.5, 149.5), (50.5, 149.5)): o.Append(V(x, y))
    z.SetAssignedPriority(1)
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.3)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(B)
print('zones filled')
