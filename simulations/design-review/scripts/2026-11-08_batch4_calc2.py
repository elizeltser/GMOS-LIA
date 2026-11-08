"""Batch 4 calc2: heater driver U9 headroom, model against the OPA2196 datasheet typical swing.
Datasheet: SBOS869 (read 2026-11-08, https://www.ti.com/lit/ds/symlink/opa2196.pdf): GBW 2.2 MHz (VS=+-2.25 V), 2.5 MHz (+-18 V),
ZO = 700 ohm at 1 MHz open loop, swing from rail at RL = 2 kohm: 60 mV typ / 500 mV max (+-2.25 V).
Model (P-33): 10.9 mV + 40.8 mV/mA, Zo 1.47 kohm. Loop phase margin: see the note at the end."""
import numpy as np
R20=R22=49.9e3; R24=15.0; Ron=4.5
# ---------- headroom ----------
print("Headroom: max HFB_A before the output stage runs out, P5VP 5.09 V (P-23) and 4.97 V (+5VA = 5.00 V minus 30 mV)")
Itest=(2.19)/2e3   # load current at the datasheet 60 mV point (RL 2 k to mid supply, VS=+-2.25 V)
k_typ=60e-3/Itest   # V per A, from 60 mV at 1.095 mA, no offset term
print("datasheet typ slope %.1f mV/mA (at %.3f mA); model 40.8 mV/mA + 10.9 mV -> %.1f mV at the same current"%(k_typ,Itest*1e3,(10.9e-3+40.8e-3*Itest*1e3)*1e3))
for Rh in [300,600,1200]:
    for P in [5.09,4.97]:
        out=[]
        for name,off,k in [("model",10.9e-3,40.8e-3*1e3),("datasheet typ",0.0,k_typ)]:
            v=np.linspace(0,5,50001)
            I=v/(Rh+Ron)+v/99.8e3
            hsh=v+R24*I
            ok=P-hsh>=off+k*I
            out.append((name,v[ok].max()))
        print("Rh %5d ohm  P5VP %.2f V: "%(Rh,P)+"  ".join("%s Vmax %.2f V"%o for o in out))
# ---------- loop ----------
# A single-pole/two-pole hand model of the loop (Zo, R24, R_on, Rh || CL, beta = 0.5) gave 46 to 59 deg at 10 nF with Zo = 1.47 kohm,
# against 19 deg from the P-33 transient (overshoot 58 %). The hand model therefore does not represent the OPAx196 model and its
# numbers are NOT used in the review. The effect of Zo = 700 ohm (datasheet) and of compensation must be simulated (test R-07).

# ---- revision 1 (2026-11-08): the 60 mV typical swing of SBOS869 applies for VS = 4.5 V to 8 V, so the slope runs from 30.5 mV/mA
# (VS = 8 V, 60 mV at 1.97 mA) to 54.8 mV/mA (VS = 4.5 V, 1.095 mA). Ceilings for both ends:
print()
print("Ceiling of HFB_A with the typical slope at both ends of the VS range")
for k_mVmA in [30.5,54.8]:
    k=k_mVmA
    for Rh in [300,600,1200]:
        row=[]
        for P in [5.09,4.97]:
            v=np.linspace(0,5,50001); I=v/(Rh+Ron)+v/99.8e3; hsh=v+R24*I
            ok=P-hsh>=k*I
            row.append(v[ok].max())
        print("slope %.1f mV/mA  Rh %5d ohm: +5VP 5.09 V -> %.2f V, 4.97 V -> %.2f V"%(k,Rh,row[0],row[1]))
