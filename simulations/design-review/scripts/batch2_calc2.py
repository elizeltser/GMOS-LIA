import numpy as np
k=1.380649e-23;T=300.15
def vn(R): return np.sqrt(4*k*T*R)*1e9
print("4kTR 100k",vn(100e3),"10k",vn(10e3))
# datasheet noise at G=11
eNI=7;eNO=90
inamp=np.hypot(eNI,eNO/11); print("INA828 RTI G=11 (no RG)",inamp)
rg=vn(5e3)*50/55; print("RG term",rg, "with RG",np.hypot(inamp,rg))
sim_total=12.68; sim_rest=np.sqrt(12.682**2-8.28**2-5.90**2); print("sim rest",sim_rest)
# datasheet-based total: replace sim INA internal (5.90 plus part of rest) -> lower bound
tot=np.hypot(np.hypot(inamp,rg),4.0) # 4 nV filters/opamps assumption
print("dsheet total approx",tot, "ratio to sim",tot/sim_total)
# Source impedance Rs per leg, bias 100k to Vref each leg
for Rs in [0.001,1e3,10e3,100e3,1e6]:
    Rleg=Rs*100e3/(Rs+100e3)   # parallel noise: source Rs thermal and 100k thermal; thevenin noise
    # noise at input: each leg: 4kT*(Rs||100k) approx (if source Rs is thermal only)
    legn=vn(Rleg)
    diff=np.sqrt(2)*legn
    # current noise 170 fA * Rs? (in at each input, uncorrelated): 
    inn=0.17e-3*Rleg*np.sqrt(2)  # nV: 0.17pA*R(ohm)=... pA*ohm =pV ->nV*1e-3
    # loading gain: divider Rs*2 vs 200k (diff)
    load=200e3/(200e3+2*Rs)
    base=12.68
    tot=np.sqrt(base**2+diff**2+inn**2)
    print(f"Rs={Rs:9.3f} Rleg={Rleg:9.1f} legnoise={legn:6.2f} diff={diff:6.2f} in*R={inn:5.2f} total={tot:6.2f} loading={load:.5f}")
# A_min scaling
fold=0.9014;G=11.07;enb=2.5
def amin(e): return np.pi/2*fold*e*1e-9*np.sqrt(enb)/G*1e9
print("Amin 12.68:",amin(12.68)*G/G, "13.6:",amin(13.6),"14.2",amin(14.2))
# output DC per sensor amplitude
k_out=G*2/np.pi; print("DC out per V sensor amp",k_out)
Amin=28.4e-9; vout=k_out*Amin; print("VX noise-equivalent",vout*1e9,"nV")
noise_rms=126.56e-9*np.sqrt(2.5); print("rms DC-band noise V",noise_rms)
for bits in [16,18,20,24]:
    lsb=5/2**bits; print(bits,"bit LSB uV",lsb*1e6,"quant rms uV",lsb/np.sqrt(12)*1e6,"ratio to noise",lsb/np.sqrt(12)/noise_rms)
# full-scale signal: output span (2A/pi*G) for A=15mV
print("DC out at 15 mV:",k_out*15e-3)
# bits needed to resolve 28 nV amplitude against 5 V full scale
print("dyn range bits",np.log2(5/ (k_out*Amin)))
# headroom budget INA828 output
L=0.15; marg=0.2; sig=0.166
half=2.5-L-marg-sig
print("DC output budget",half,"-> input DC",half/11*1e3,"mV")
# charge injection DC error
for Q,name in [(0.4e-12,"model/TMUX6136"),(6e-12,"TMUX1136")]:
    I=Q*2*517
    print(name,"I=",I*1e9,"nA", "x1ohm uV",I*1e6,"x10 ohm",I*1e7,"x5k",I*5e3*1e3,"mV")
# baseline: 2*Vos demod
for vos in [5e-6,25e-6,150e-6]:
    print("Vos",vos*1e6,"uV -> VX baseline",2*vos*1e6,"uV ->sensor-equivalent",2*vos/k_out*1e9,"nV, x Amin",2*vos/k_out/28.4e-9)
# drift 0.2uV/C *2 *10K
print("drift 10K:",2*0.2e-6*10*1e6,"uV ->",2*0.2e-6*10/k_out*1e9,"nV")
# ripple at 2f on VX at tau=0.1 for 166 mV
print("2f ripple VX tau 0.1, A=0.166:",1.306*0.166/0.2/10,"mV")
# duty hardware: 1 ns asym, offset 1 mV
print("1ns:",2*1e-9/1.934e-3*1e-3*1e6,"nV per mV")
# vref noise: REF3425 24 uVrms 10Hz-10kHz
print("Vref noise density avg",24e-6/np.sqrt(9990)*1e9,"nV/rtHz")
# SK gain error of GBW: INA phase 
print("INA828 phase at 517 Hz BW 640k:",-np.degrees(np.arctan(517/640e3)))
# required Vref ripple coherent for A_min
print("ripple for Amin",noise_rms/(2/np.pi)*1e6,"uV amplitude (1 sigma noise)",  k_out*Amin/(2/np.pi)*1e9,"nV")
# ADC kickback / Rsrc: output R3=10k, ADC input current 1uA -> 10 mV
print("10k*1uA",10e3*1e-6*1e3,"mV")
