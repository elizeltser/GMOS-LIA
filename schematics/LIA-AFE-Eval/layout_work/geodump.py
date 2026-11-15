import pcbnew,sys,json
b=pcbnew.LoadBoard(sys.argv[1]); M=1e6; D={'edge':[],'zones':[],'tracks':[],'vias':[],'fps':[]}
ln={pcbnew.F_Cu:'F',pcbnew.B_Cu:'B',pcbnew.In2_Cu:'I2',pcbnew.In1_Cu:'I1'}
for d in b.GetDrawings():
    if d.GetLayer()==pcbnew.Edge_Cuts: D['edge'].append([d.GetStart().x/M,d.GetStart().y/M,d.GetEnd().x/M,d.GetEnd().y/M])
for z in b.Zones():
    for li in z.GetLayerSet().Seq():
        if li not in ln or not z.IsFilled(): continue
        fp=z.GetFilledPolysList(li)
        for i in range(fp.OutlineCount()):
            o=fp.Outline(i); D['zones'].append([ln[li],[(o.CPoint(k).x/M,o.CPoint(k).y/M) for k in range(o.PointCount())]])
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': D['vias'].append([t.GetPosition().x/M,t.GetPosition().y/M,t.GetWidth(pcbnew.F_Cu)/M])
    else: D['tracks'].append([ln.get(t.GetLayer(),'?'),t.GetStart().x/M,t.GetStart().y/M,t.GetEnd().x/M,t.GetEnd().y/M,t.GetWidth()/M])
for f in b.GetFootprints():
    bk=f.IsFlipped(); cy=f.GetCourtyard(pcbnew.B_CrtYd if bk else pcbnew.F_CrtYd).BBox()
    pads=[]
    for p in f.Pads():
        bb=p.GetBoundingBox(); pads.append([bb.GetLeft()/M,bb.GetTop()/M,bb.GetWidth()/M,bb.GetHeight()/M,p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH,p.GetNetname().split('/')[-1]])
    D['fps'].append([f.GetReference(),bk,cy.GetLeft()/M,cy.GetTop()/M,cy.GetWidth()/M,cy.GetHeight()/M,pads])
json.dump(D,open(sys.argv[2],'w'))
