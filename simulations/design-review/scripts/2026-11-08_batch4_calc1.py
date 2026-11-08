"""Batch 4 calc1: TMUX6136 SEL / signal pin clamp current vs series resistor, edge delay, rail charge.
Run: python 2026-11-08_batch4_calc1.py
Assumptions (marked): MCU pin output resistance 25 ohm (earlier review 2026-10-29 F-05, STM32F303 datasheet not read),
clamp drop 0.6 V, SEL pin + test loop capacitance 10 pF (assumption, TMUX6136 CIN not read), 11.1 uF on +15 V rail (P-31)."""
import numpy as np
V=3.3; Vf=0.6; Rout=25.0; Cp=10e-12; Crail=11.1e-6; f0=518.0
print("SEL clamp with VDD=0 (rail floats up to V-Vf = %.1f V)"%(V-Vf))
print("%8s %12s %14s %14s %12s %12s"%("Rser","Ipk mA","30mA limit","tau_charge ms","edge ns","phase deg"))
for R in [0,100,330,1e3,3.3e3,10e3]:
    Ipk=(V-Vf)/(R+Rout)
    tau=(R+Rout)*Crail*1e3
    tedge=0.93*(R+Rout)*Cp*1e9   # 0->2 V (VIH) crossing of a 3.3 V step
    ph=360*f0*tedge*1e-9
    print("%8.0f %12.1f %14s %14.2f %12.1f %12.4f"%(R,Ipk*1e3,"EXCEEDED" if Ipk>30e-3 else "ok",tau,tedge,ph))
print("charge to lift the +15 V rail to 2.7 V: %.1f uC"%(Crail*(V-Vf)*1e6))
print()
print("BPF_OUT into S1A/S2A with VDD=VSS=0 (J5 on, J4 off): clamp current vs series R, BPF_OUT peak")
for Vp in [0.4,2.0,4.0]:
    for R in [0,100,1e3]:
        I=(Vp-0.6)/(R+10)  # 10 ohm = U3B closed-loop output resistance placeholder
        print("  Vpk %.1f V R %5.0f -> %.1f mA %s"%(Vp,R,I*1e3,"> 30 mA" if I>30e-3 else ""))
# Delay added by 1 k at S1A/S2A: load = C_D(~6 pF switch Con 5.5 pF datasheet LCSC listing + 6.4 pF CM + 1.6 pF diff + 5 pF trace)
C=5.5e-12+6.4e-12+1.6e-12+5e-12
for R in [0,100,1e3]:
    t=0.69*(R+120)*C   # 120 ohm = TMUX6136 RON (LCSC listing), 50 % point
    print("S-pin series %5.0f ohm: 50%% delay %.1f ns -> %.4f deg of Y-error term; P-28 fitted delta 38 ns"%(R,t*1e9,360*f0*t))
