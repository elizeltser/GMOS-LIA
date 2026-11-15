import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
for f in b.GetFootprints():
    if f.GetReference() not in sys.argv[2].split(','): continue
    bb=f.GetCourtyard(pcbnew.F_CrtYd if not f.IsFlipped() else pcbnew.B_CrtYd).BBox() if hasattr(f,'GetCourtyard') else f.GetBoundingBox()
    print(f.GetReference(), 'bbox x%.1f..%.1f y%.1f..%.1f'%(bb.GetLeft()/1e6,bb.GetRight()/1e6,bb.GetTop()/1e6,bb.GetBottom()/1e6))
    for p in f.Pads():
        q=p.GetPosition(); print('   ',p.GetNumber(),'%.2f,%.2f'%(q.x/1e6,q.y/1e6),p.GetNetname().split('/')[-1])
