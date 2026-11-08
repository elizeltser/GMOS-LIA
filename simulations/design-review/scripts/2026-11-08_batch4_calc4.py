"""Batch 4 calc4: Sallen-Key post-filter feedthrough with the datasheet open-loop output impedance, drain-window compliance, BPF_OUT clipping.
Model values (P-34): L = 81.6 uH, R14 = 200 kohm, 2f0 ripple 453 nV, 4f0 180 nV. Datasheet (SBOS869, read 2026-11-08): ZO = 700 ohm open loop at 1 MHz,
GBW 2.2 MHz (+-2.25 V) to 2.5 MHz (+-18 V). Closed-loop follower: Zo_cl(f) = Zo_ol f / GBW, i.e. L = Zo_ol / (2 pi GBW)."""
import numpy as np
R14=200e3; f0=518.03
Lm=81.6e-6
print("model L = %.1f uH; scaling by the Zo ratio 700/1470 = %.3f gives %.1f uH (same GBW assumed): 2f0 ripple %.0f nV"%(Lm*1e6,700/1470,Lm*1e6*700/1470,453*700/1470))
for GBW in [2.2e6,2.5e6]:
    L=700/(2*np.pi*GBW)
    k=L/Lm
    print("datasheet Zo 700 ohm, GBW %.1f MHz: L = %.1f uH, ratio to model %.2f -> 2f0 ripple %.0f nV, 4f0 %.0f nV, floor %.2e x f (model 2.56e-9 f)"%(GBW/1e6,L*1e6,k,453*k,180*k,2*np.pi*L/R14))
# comb rms scaling, P-34: 10.4 uV rms at ai = 0.398 V (model)
print("edge comb rms: model 10.4 uV -> %.1f uV with L = 44.6 uH (same scaling)"%(10.4*44.6/81.6))
# ratio of the 2f0 ripple to noise
print("2f0 ripple 453 nV = %.1f %% of the 16.96 uV rms X_OUT noise; drain-referred %.1f nV"%(453/16960*100,453/25.19))
# ---- drain window
print()
Id=7.5e-6; RD=330e3
for vs in [0.5,1.0,2.0,2.4,2.63,3.5]:
    print("VSUP_A %.2f V -> drain %.3f V (7.5 uA x 330 kohm = %.3f V)"%(vs,vs-Id*RD,Id*RD))
print("drain >= +0.05 V (design-context: drain DC 50 mV to 250 mV) needs VSUP_A >= %.3f V = DAC2 >= %.3f V (VSUP = 1.1 DAC2 - 7.5 mV)"%(0.05+Id*RD,(0.05+Id*RD+0.0075)/1.1))
print("TMUX1109 abs max Sx/Dx: -0.5 V to VDD+0.5 V (SCDS406A table 5.1, read 2026-11-08); recommended 0 to VDD; VSS tied to GND on a single supply")
print("drain reaches -0.5 V at VSUP_A = %.3f V (DAC2 = %.3f V)"%(-0.5+Id*RD,(-0.5+Id*RD+0.0075)/1.1))
# ---- clipping at U3B
print()
G=39.571
for vd in [0.1,0.128,0.14]:
    print("drain %.0f mV pk -> BPF_OUT %.2f V pk ; P5VA 5.12 V minus 2 kohm-class swing (60 mV typ) = %.2f V"%(vd*1e3,G*vd,5.12-0.06))
print("datasheet max swing 500 mV at 2 kohm gives a BPF_OUT limit of %.2f V -> drain amplitude %.0f mV pk"%(5.12-0.5,(5.12-0.5)/G*1e3))
print("INA828 output: DC mismatch 200 mV x 9.897 = %.2f V plus 50 mV x 9.897 = %.2f V pk -> %.2f V of the +-5 V rail"%(0.2*9.897,0.05*9.897,0.25*9.897))
# demodulator noise
print()
en=15e-9; Rpar=5e3
nd=np.sqrt((en*np.sqrt(2))**2+4*1.38e-23*300*Rpar)  # noise gain 2 in the -1 state, 10k||10k
print("U26A at BPF_OUT: %.1f nV/rtHz -> drain-referred %.2f nV/rtHz = %.3f %% of the 729 nV/rtHz sensor noise power"%(nd*1e9,nd/39.571*1e9,(nd/39.571/729e-9)**2*100))
