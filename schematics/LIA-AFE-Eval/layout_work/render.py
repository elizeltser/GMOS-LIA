import sys,json,matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle,Polygon
D=json.load(open(sys.argv[1])); out=sys.argv[2]
win=[float(v) for v in sys.argv[3:7]] if len(sys.argv)>=7 else [48,48,152,152]
show=sys.argv[7].split(',') if len(sys.argv)>7 else ['F','B','I2']
s=win[2]-win[0]; fig=plt.figure(figsize=(13,13*(win[3]-win[1])/s)); ax=fig.add_axes([0,0,1,1])
ax.set_xlim(win[0],win[2]); ax.set_ylim(win[3],win[1]); ax.set_aspect('equal'); ax.set_facecolor('#111')
col={'F':'#e33','B':'#39f','I2':'#c8c','I1':'#4c4','?':'#fff'}
for e in D['edge']: ax.plot([e[0],e[2]],[e[1],e[3]],'y-',lw=1)
for l,pts in D['zones']:
    if l in show: ax.add_patch(Polygon(pts,closed=True,fc=col[l],alpha=0.10,ec='none'))
for l,x0,y0,x1,y1,w in D['tracks']:
    if l in show: ax.plot([x0,x1],[y0,y1],'-',color=col[l],lw=w*72*13/s,solid_capstyle='round',alpha=0.8,zorder=3 if l=='F' else 2)
for x,y,d in D['vias']: ax.add_patch(Circle((x,y),d/2,fc='#ddd',ec='k',lw=0.3,zorder=5))
fs=max(4,9*100/s)
for r,bk,x,y,w,h,pads in D['fps']:
    ax.add_patch(Rectangle((x,y),w,h,fill=False,ec='#f80' if bk else '#ccc',lw=0.6,ls='--' if bk else '-'))
    for px,py,pw,ph,pth,net in pads:
        ax.add_patch(Rectangle((px,py),pw,ph,fc='#aa6' if pth else ('#558' if bk else '#a55'),ec='none',alpha=0.9,zorder=4))
        if s<45 and net: ax.text(px+pw/2,py+ph/2,net[:9],fontsize=fs*0.33,color='w',ha='center',va='center',zorder=6,rotation=90 if ph>pw*1.5 else 0)
    ax.text(x+w/2,y+h/2,r,fontsize=fs*0.6,color='#fa0' if bk else '#ff0',ha='center',va='center',zorder=7,alpha=0.8)
for k in range(int(win[0]//10*10),int(win[2])+1,10 if s>45 else 2):
    ax.axvline(k,color='#333',lw=0.4); ax.text(k,win[1]+0.6*s/100,str(k),color='#888',fontsize=7)
for k in range(int(win[1]//10*10),int(win[3])+1,10 if s>45 else 2):
    ax.axhline(k,color='#333',lw=0.4); ax.text(win[0]+0.3*s/100,k,str(k),color='#888',fontsize=7)
fig.savefig(out,dpi=100)
