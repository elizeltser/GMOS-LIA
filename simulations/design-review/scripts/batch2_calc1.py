import numpy as np
f=517.0; s=2j*np.pi*f
R17=4.64e3;R18=18.7e3;R21=4.64e3;R22=4.64e3;C1=C2=C3=33e-9;C4=130e-9;RG=5e3
def H(R17=R17,R18=R18,R21=R21,R22=R22,C1=C1,C2=C2,C3=C3,C4=C4,RG=RG,f=f):
    s=2j*np.pi*f
    G=1+50e3/RG
    hp=(s**2*R17*R18*C1*C2)/(s**2*R17*R18*C1*C2+s*R17*(C1+C2)+1)
    lp=1/(s**2*R22*R21*C4*C3+s*C3*(R22+R21)+1)
    return G*hp*lp
H0=H(); print("H0",abs(H0),np.angle(H0,deg=True))
# return currents into Vref, Vd = 15 mV amplitude
Vd=15e-3; Vin=11*Vd
# HP nodes
A=np.array([[1/R17+s*C1+s*C2, -(1/R17+s*C2)],[-s*C2, s*C2+1/R18]])
b=np.array([s*C1*Vin,0])
Aa,B=np.linalg.solve(A,b)
iR18=B/R18
# LP
Hp=B
# nodes N,M: (N-Hp)/R22+(N-M)/R21+(N-M)*0 ... C4 from N to M(vout=M)
A2=np.array([[1/R22+1/R21+s*C4, -(1/R21+s*C4)],[-1/R21, 1/R21+s*C3]])
b2=np.array([Hp/R22,0]); N,M=np.linalg.solve(A2,b2)
iC3=M*s*C3
print("VSAMPLE amp mV",abs(M)*1e3,"|iR18| uA",abs(iR18)*1e6,"|iC3| uA",abs(iC3)*1e6,"sum",abs(iR18+iC3)*1e6)
for rr in [0.1,1,10]:
    a=rr*abs(iR18+iC3); print("Zref",rr,"ohm ripple uV",a*1e6,"isolated DC err uV",2/np.pi*a*1e6, "rel to 105.8mV %",2/np.pi*a/0.1058*100)
# phase sensitivity: which comps dominate
rng=np.random.default_rng(1)
n=200000
def mc(tolR,tolC,which=None):
    def u(nom,t): return nom*(1+rng.uniform(-t,t,n))
    Hs=H(R17=u(R17,tolR),R18=u(R18,tolR),R21=u(R21,tolR),R22=u(R22,tolR),C1=u(C1,tolC),C2=u(C2,tolC),C3=u(C3,tolC),C4=u(C4,tolC),RG=u(RG,tolR))
    r=Hs/H0
    ph=np.angle(r,deg=True); g=abs(r)-1
    return ph.std(),g.std()*100,np.mean(abs(ph)>1)*100
print("1%R 5%C",mc(.01,.05))
print("0.1%R 5%C",mc(.001,.05))
print("0.1%R 1%C",mc(.001,.01))
print("0.1%R 2%C",mc(.001,.02))
print("0.1%R 0.5%C",mc(.001,.005))
print("0.1%R 0.2%C",mc(.001,.002))
print("1%R 0%C",mc(.01,1e-9))
print("0.1%R 0%C",mc(.001,1e-9))
# drift: all C +x, all R +x
for x in [1e-3,3e-3,1e-2]:
    h=H(R17=R17*(1+x),R18=R18*(1+x),R21=R21*(1+x),R22=R22*(1+x),C1=C1*(1+x),C2=C2*(1+x),C3=C3*(1+x),C4=C4*(1+x))/H0
    print("all C,R +",x*100,"% -> phase deg",np.angle(h,deg=True),"gain %",(abs(h)-1)*100)
for x in [1e-3,1e-2]:
    h=H(C1=C1*(1+x),C2=C2*(1+x),C3=C3*(1+x),C4=C4*(1+x))/H0
    print("all C +",x*100,"% -> phase deg",np.angle(h,deg=True),"gain %",(abs(h)-1)*100)
# C0G 30ppm/K *50K =0.15%: 
x=30e-6*50
h=H(C1=C1*(1+x),C2=C2*(1+x),C3=C3*(1+x),C4=C4*(1+x))/H0; print("C0G 50K",np.angle(h,deg=True),(abs(h)-1)*100)
x=0.15
h=H(C1=C1*(1-x),C2=C2*(1-x),C3=C3*(1-x),C4=C4*(1-x))/H0; print("X7R -15%",np.angle(h,deg=True),(abs(h)-1)*100)
# gain vs freq 100 Hz and 10 kHz
for ff in [100,200,517,1000,5000,10000]:
    print(ff,abs(H(f=ff)))
# phase slope
d=np.angle(H(f=518)/H(f=516),deg=True)/2; print("deg/Hz",d)
