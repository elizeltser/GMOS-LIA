import numpy as np
exec(open(__file__.replace('batch2_calc5','batch2_calc1')).read().split('# return currents')[0])
fosc=517.0
ns=np.arange(1,400,2)
def factor(Hf):
    # Hf: function f-> complex (array over samples)
    h1=Hf(fosc)
    num=0
    for n in ns:
        h=Hf(n*fosc); num=num+(np.abs(h)*np.cos(np.angle(h)))/n**2
    # X fundamental-only term: |H1| cos(phi1)
    return num/(np.abs(h1)*np.cos(np.angle(h1)))
Hnom=lambda f:H(f=f)
print("nominal factor",factor(Hnom))
rng=np.random.default_rng(3)
n=4000
for tolR,tolC in [(.01,.05),(.001,.01),(.001,.002)]:
    u=lambda nom,t: nom*(1+rng.uniform(-t,t,n))
    p=dict(R17=u(R17,tolR),R18=u(R18,tolR),R21=u(R21,tolR),R22=u(R22,tolR),C1=u(C1,tolC),C2=u(C2,tolC),C3=u(C3,tolC),C4=u(C4,tolC),RG=u(RG,tolR))
    fac=factor(lambda f:H(f=f,**p))
    print(tolR,tolC,"factor mean",fac.mean(),"std %",fac.std()*100,"min/max",fac.min(),fac.max())
