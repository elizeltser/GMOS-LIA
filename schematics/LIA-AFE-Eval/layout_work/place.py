import pcbnew,sys
B=sys.argv[1]; b=pcbnew.LoadBoard(B)
# ref: (x, y, rot, side)  side 'F' or 'B'
P={
'H1':(54.0,44.0,0,'F'),'H2':(146.0,44.0,0,'F'),
# --- Excitation tidy-up
'R5':(87.3,88.0,90,'F'),'C7':(84.0,88.6,0,'F'),'R6':(79.67,88.6,0,'F'),
'R8':(81.3,86.2,0,'F'),'C8':(84.4,86.2,0,'F'),'R59':(90.9,86.4,90,'F'),
'C2':(86.0,79.6,90,'F'),'C4':(77.2,84.4,0,'F'),
'TP11':(89.6,77.6,0,'F'),'TP13':(89.6,73.1,0,'F'),
# --- control test points next to J7
'TP6':(71.0,94.4,0,'F'),'TP7':(75.5,94.5,0,'F'),'TP8':(79.8,94.4,0,'F'),
'TP9':(71.0,98.8,0,'F'),'TP10':(75.4,98.8,0,'F'),
'C65':(70.2,65.6,90,'F'),'C66':(72.0,65.6,90,'F'),'R38':(70.6,77.4,0,'F'),
# --- muxes (rotated 180 deg: drain pins face the socket)
'U20':(96.5,66.0,90,'B'),'U21':(107.5,66.0,90,'B'),
'C71':(97.5,60.6,90,'B'),'C72':(108.5,60.6,90,'B'),
'R57':(94.9,60.4,90,'B'),'R56':(105.9,60.4,90,'B'),
'R54':(96.6,66.0,0,'F'),'R55':(107.6,66.0,0,'F'),
'R25':(100.6,60.2,90,'F'),'R31':(110.2,68.6,90,'F'),
'C73':(90.0,110.6,180,'F'),
# --- drain-bias block
'U10':(122.0,57.0,0,'F'),
'R21':(117.9,56.4,-90,'F'),'R23':(117.6,59.6,-90,'F'),'R60':(117.9,53.4,90,'F'),'C74':(115.6,51.8,90,'F'),
'R27':(126.1,56.4,-90,'F'),'R29':(126.4,59.6,-90,'F'),'R61':(126.1,53.4,90,'F'),'C75':(128.4,51.8,90,'F'),
'C76':(123.8,54.0,0,'F'),'C77':(120.2,59.9,180,'F'),
'TP16':(115.3,55.3,0,'F'),'TP17':(129.8,56.2,0,'F'),
# --- drain test resistors and loops near the in-amp
'R90':(114.8,100.0,180,'F'),'TP14':(116.9,96.6,0,'F'),
'R91':(111.4,108.0,90,'F'),'TP15':(111.8,112.0,0,'F'),
# --- in-amp: inputs face the drain pair
'U2':(120.91,104.03,0,'F'),'R10':(121.0,100.5,0,'F'),
'C88':(125.6,102.6,90,'F'),'C89':(118.2,107.9,0,'F'),
# --- heaters (top band)
'U9':(76.0,50.0,0,'F'),
'R24':(69.6,47.4,0,'F'),'IC3':(65.0,49.6,0,'F'),'C87':(65.0,53.0,0,'F'),'R69':(60.8,49.8,90,'F'),'C86':(60.8,53.2,90,'F'),
'R20':(70.4,53.6,0,'F'),'R22':(70.4,55.2,0,'F'),'C83':(73.9,53.3,-90,'F'),
'R30':(83.9,51.0,-90,'F'),'IC1':(87.0,50.3,180,'F'),'C85':(90.0,51.0,-90,'F'),'R68':(84.6,47.4,180,'F'),'C84':(82.1,45.6,0,'F'),
'R26':(79.4,53.4,0,'F'),'R28':(79.4,55.0,0,'F'),'C82':(78.9,46.9,0,'F'),
'TP18':(80.2,65.0,0,'F'),'TP19':(84.6,65.0,0,'F'),'TP20':(89.0,65.0,0,'F'),
# --- demodulator: switch between the SMAs, X above J8, Y below J9
'U24':(140.5,103.0,0,'F'),'C95':(135.6,104.6,90,'F'),'C96':(145.4,102.8,90,'F'),
'J10':(147.6,86.4,0,'F'),
'U26':(137.5,66.5,0,'F'),'U27':(137.5,129.5,0,'F'),'R79':(133.0,63.6,90,'F'),'R84':(133.0,126.6,90,'F'),'R78':(132.2,67.8,0,'F'),'R83':(132.2,130.8,0,'F'),'C98':(135.2,70.0,0,'F'),'C100':(135.2,133.0,0,'F'),'R14':(136.4,61.8,0,'F'),'R16':(136.4,124.8,0,'F'),'C13':(140.4,59.6,0,'F'),'C14':(140.4,122.6,0,'F'),'C15':(139.6,70.2,0,'F'),'C16':(139.6,133.2,0,'F'),'R15':(141.9,65.0,-90,'F'),'R17':(141.9,128.0,-90,'F'),'C97':(139.4,63.4,0,'F'),'C99':(139.4,126.4,0,'F'),'R88':(143.6,66.0,90,'F'),'R93':(143.6,129.0,90,'F'),'R89':(143.6,69.2,-90,'F'),'R92':(143.6,132.2,-90,'F'),'R80':(145.4,72.0,90,'F'),'TP30':(146.0,61.6,0,'F'),'TP26':(131.4,72.6,0,'F'),'TP28':(131.4,135.6,0,'F'),'TP27':(135.4,73.6,0,'F'),'TP29':(135.4,136.6,0,'F'),'R85':(145.6,123.4,90,'F'),'TP31':(146.3,128.0,0,'F'),'C53':(71.6,124.2,90,'F'),'C59':(71.0,136.2,90,'F'),
# --- front-end test loops moved left to make room for the Y channel
'TP21':(125.0,123.0,0,'F'),'TP22':(125.0,127.4,0,'F'),'TP23':(125.0,131.8,0,'F'),'TP25':(125.0,136.2,0,'F'),
}
fps={f.GetReference():f for f in b.GetFootprints()}
for r,(x,y,rot,side) in P.items():
    f=fps[r]
    if (side=='B')!=f.IsFlipped(): f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
    f.SetOrientationDegrees(rot)
# board outline 100 x 110 mm: move the top edge from y 50 to y 40 (owner approved a larger board)
D10 = pcbnew.FromMM(10)
for d in list(b.GetDrawings()):
    if d.GetLayer() != pcbnew.Edge_Cuts: continue
    s, e = d.GetStart(), d.GetEnd()
    if d.GetShape() == pcbnew.SHAPE_T_ARC and max(s.y, e.y) <= pcbnew.FromMM(54.01) and min(s.y, e.y) >= pcbnew.FromMM(49.99):
        d.Move(pcbnew.VECTOR2I(0, -D10))
    elif d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        if s.y == e.y == pcbnew.FromMM(50): d.Move(pcbnew.VECTOR2I(0, -D10))
        elif s.x == e.x:
            if s.y == pcbnew.FromMM(54): d.SetStart(pcbnew.VECTOR2I(s.x, pcbnew.FromMM(44)))
            if e.y == pcbnew.FromMM(54): d.SetEnd(pcbnew.VECTOR2I(e.x, pcbnew.FromMM(44)))
b.Save(B)
# courtyard overlap / outside-board report
M=1e6; items=[]
for f in b.GetFootprints():
    bk=f.IsFlipped(); c=f.GetCourtyard(pcbnew.B_CrtYd if bk else pcbnew.F_CrtYd).BBox()
    items.append((f.GetReference(),bk,c.GetLeft()/M,c.GetTop()/M,c.GetRight()/M,c.GetBottom()/M,f.GetPosition().x/M))
for i,a in enumerate(items):
    if a[2]<50 or a[4]>150 or a[3]<40 or a[5]>150: print('OUTSIDE',a[0])
    for c in items[i+1:]:
        if a[1]!=c[1]: continue
        if a[2]<c[4]-0.05 and c[2]<a[4]-0.05 and a[3]<c[5]-0.05 and c[3]<a[5]-0.05: print('OVERLAP',a[0],c[0])
