import numpy as np
try:
    import scipy.signal as sg
except Exception as e:
    print("noscipy",e); raise
R17=4.64e3;R18=18.7e3;R21=4.64e3;R22=4.64e3;C1=C2=C3=33e-9;C4=130e-9
# HP num/den in s
hp_n=[R17*R18*C1*C2,0,0]; hp_d=[R17*R18*C1*C2,R17*(C1+C2),1]
lp_n=[1]; lp_d=[R22*R21*C4*C3,C3*(R22+R21),1]
num=np.polymul(hp_n,lp_n); den=np.polymul(hp_d,lp_d)
num=11*np.array(num)
sys=sg.TransferFunction(num,den)
t=np.linspace(0,0.08,160001)
for dv in [0.01,0.05,0.1,0.15,0.3]:
    tt,y=sg.step(sys,T=t); y=y*dv
    pk=np.max(abs(y)); 
    idx=np.where(abs(y)>1e-3)[0]; trec=tt[idx[-1]]
    idx1=np.where(abs(y)>1e-3*abs(dv)/0.1)[0]
    print(f"dV={dv} V: peak {pk:.3f} V, |y|>1mV until {trec*1e3:.2f} ms")
# also the step response polarity peak time
tt,y=sg.step(sys,T=t); print("peak time ms",tt[np.argmax(abs(y))]*1e3, "peak per V",np.max(abs(y)))
# DC step on demod: VX ripple at f_osc for tau 0.1 and 10ms
fosc=517
for tau in [0.1,0.01]:
    att=1/np.sqrt(1+(2*np.pi*fosc*tau)**2)
    print("tau",tau,"fundamental ripple per V of VSAMPLE excursion:",4/np.pi*att*1e3,"mV/V")
