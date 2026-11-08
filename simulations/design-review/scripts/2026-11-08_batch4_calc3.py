"""Batch 4 calc3: offset budget at X_OUT, angle errors from uncalibrated X/Y errors, precision of the phase-sweep (ellipse) calibration,
post-filter capacitor leakage, dummy-card numbers.
Datasheet values (SBOS869, read 2026-11-08): Vos +-25 uV typ, +-100 uV max, drift +-0.5 uV/degC typ, Ib +-5 pA typ, +-20 pA max.
Project values: P-23 offset formula, P-30 noise 16.96 uV rms (ENBW 0.4167 Hz), P-27 scale 25.19 V/V, R78/R79/R83/R84 0.1 %."""
import numpy as np
rng=np.random.default_rng(7)
# ---- offset budget at X_OUT (P-23 formula: 4 Vos(U3A) + 2 Vos(U3B) + 2 Vos(U26A) + Vos(U26B) + 400 kohm Ib)
w=np.array([4,2,2,1])
for name,v in [("typ 25 uV",25e-6),("max 100 uV",100e-6)]:
    print("Offset at X_OUT, Vos %s: worst %.0f uV, RSS %.0f uV"%(name,v*w.sum()*1e6,v*np.sqrt((w**2).sum())*1e6))
print("Ib term 20 pA x 400 kohm = %.1f uV"%(20e-12*400e3*1e6))
for d in [0.5e-6]:
    print("drift 0.5 uV/K: worst %.1f uV/K, RSS %.1f uV/K; over 5 K: %.0f / %.0f uV (noise 16.96 uV rms)"%(d*w.sum()*1e6,d*np.sqrt((w**2).sum())*1e6,5*d*w.sum()*1e6,5*d*np.sqrt((w**2).sum())*1e6))
S=25.19
print("referred to the drain (/%.2f V/V): 0.91 mV -> %.1f uV; noise 16.96 uV -> %.2f uV"%(S,0.91e-3/S*1e6,16.96/S))
# ---- angle errors if nothing is calibrated, signal R at X_OUT
print()
for drain_mV in [50,10,1]:
    R=S*drain_mV*1e-3
    print("drain %3d mV pk: R = %.1f mV | offset 0.91 mV -> angle error %.2f deg, amplitude error up to %.2f %% | offset 0.125 mV (RSS typ) -> %.2f deg"%(drain_mV,R*1e3,0.91e-3/R*180/np.pi,0.91e-3/R*100,0.125e-3/R*180/np.pi))
# gain mismatch and orthogonality
for dg in [0.001,0.002]:
    print("X/Y gain mismatch %.2f %% -> max angle error %.3f deg"%(dg*100,dg/2*180/np.pi))
print("0.1 %% pair (R79/R78): delta up to 0.2 %% -> scale error delta/2 = 0.1 %% per channel (DI-05); two channels RSS %.2f %%"%(np.sqrt(2)*0.1))
# timing: Y reference T/4 error from timer resolution (NUCLEO-F303RE, 72 MHz timer clock, assumption: not verified) and TMUX6136 channel delay mismatch
f0=518.03; T=1/f0
print("timer tick 1/72 MHz = %.1f ns -> %.4f deg of 518 Hz; T/4 = %.3f us = %.1f ticks"%(1e9/72e6,360*f0/72e6,T/4*1e6,T/4*72e6))
# ---- post-filter capacitor leakage -> DC gain error
for IR in [100e6,400e6,1e9,10e9]:
    print("C15 insulation resistance %.0f Mohm: DC gain error %.4f %% (R14+R15 = 400 kohm)"%(IR/1e6,-400e3/IR*100))
print("IR x C needed for 0.1 %%: %.0f Mohm x uF at 1.5 uF"%(400e6*1.5))
# ---- precision of the phase-sweep calibration
def fit(npts,dwell_s,A=0.2519,eps=0.05,gr=1.001,X0=0.3e-3,Y0=-0.2e-3,th=167.1,trials=2000):
    corr=1.2   # s, correlation time of the post-filter noise (1/(2 ENBW))
    sig=16.96e-6/np.sqrt(max(dwell_s/corr,1.0))
    p=np.deg2rad(np.arange(npts)*360/npts)
    res=[]
    for _ in range(trials):
        # model: X = X0 + a cos(p+th), Y = Y0 + b sin(p+th+eps)  (b = a*gr)
        t=np.deg2rad(th); e=np.deg2rad(eps)
        X=X0+A*np.cos(p+t)+rng.normal(0,sig,npts)
        Y=Y0+A*gr*np.sin(p+t+e)+rng.normal(0,sig,npts)
        # linear LS: X = X0 + c1 cos p + s1 sin p ; Y = Y0 + c2 cos p + s2 sin p
        M=np.c_[np.ones(npts),np.cos(p),np.sin(p)]
        cx=np.linalg.lstsq(M,X,rcond=None)[0]; cy=np.linalg.lstsq(M,Y,rcond=None)[0]
        ax=np.hypot(cx[1],cx[2]); ay=np.hypot(cy[1],cy[2])
        phx=np.arctan2(-cx[2],cx[1])      # X = ax cos(p + phx)
        phy=np.arctan2(cy[1],cy[2])-0     # Y = ay sin(p + phy)  -> cos(p + phy - pi/2)
        eps_est=np.rad2deg(phy-(phx))     # phase of Y axis minus X axis (orthogonality error, deg)
        res.append([cx[0],cy[0],ay/ax,eps_est,np.rad2deg(phx)])
    r=np.array(res)
    return sig,r[:,0].std()*1e6,r[:,1].std()*1e6,r[:,2].std()*1e6,r[:,3].std(),r[:,3].mean()
print()
print("Phase-sweep calibration, 10 mV drain signal (R = 252 mV), true X0 = +300 uV, Y0 = -200 uV, gain ratio 1.001, eps = 0.05 deg")
print("%6s %8s | %9s %9s %9s %12s %12s %10s"%("points","dwell s","sigma uV","s(X0) uV","s(Y0) uV","s(gy/gx) ppm","s(eps) deg","mean eps"))
for n,d in [(8,10),(8,20),(16,10),(16,30)]:
    s,a,b,c,e,m=fit(n,d)
    print("%6d %8d | %9.1f %9.1f %9.1f %12.0f %12.4f %10.3f"%(n,d,s*1e6,a,b,c,e,m))
print("time per point = settle 5 s + dwell; settle: (1+x)exp(-x) = 4e-6 gives x = %.1f -> %.1f s at tau 0.3 s"%(
    (lambda x:x)(next(x for x in np.arange(1,30,0.01) if (1+x)*np.exp(-x)<4e-6)), 0.3*next(x for x in np.arange(1,30,0.01) if (1+x)*np.exp(-x)<4e-6)))
# ---- dummy card (gate -> drain) numbers
vg=2.5e-3; ipk=10e-3/330e3
Rg=vg/ipk; Xc=1/(2*np.pi*f0*100e-9)
print()
print("Dummy card: drain current for 10 mV pk across 330 kohm = %.1f nA pk; gate 2.5 mV pk -> Rg = %.1f kohm; series 100 nF: Xc = %.2f kohm, lead %.2f deg; DC current if no capacitor = %.1f uA"%(ipk*1e9,Rg/1e3,Xc/1e3,np.degrees(np.arctan(Xc/Rg)),0.9946/Rg*1e6))
