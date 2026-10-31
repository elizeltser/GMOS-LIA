"""Estimates behind the LIA-AFE-Eval schematic rev 0.1 review (2026-10-29).
Run: python3 2026-10-29_schematic_rev0.1_calc1.py
Datasheet values: OPA2196 SBOS869 (GBW 2.5 MHz, Zo 700 ohm @1 MHz, Cdiff 1.6 pF, Ccm 6.4 pF),
INA828 SBOS792A, TMUX1109 SCDS406A, TMUX6136 SCDS397B, DAC80508 SLASEL1D, INA190 SBOS863D.
Parasitics (pin capacitance, layout) are assumptions and are marked 'assumed'."""
import math, cmath
class _NP:
    pi=math.pi
    @staticmethod
    def sqrt(x): return math.sqrt(x)
    @staticmethod
    def hypot(a,b): return math.hypot(a,b)
    @staticmethod
    def log10(x): return math.log10(x)
    @staticmethod
    def arctan(x): return math.atan(x)
    @staticmethod
    def degrees(x): return math.degrees(x)
np=_NP()
FREQS=[10**(3+5*k/20000) for k in range(20001)]   # 1 kHz .. 100 MHz

def crossover(Lfun):
    """first frequency where |L|<1 and phase margin in degrees (unwrapped from -90 deg start)"""
    ph_prev=None; off=0.0
    for f in FREQS:
        L=Lfun(f)
        ph=math.degrees(cmath.phase(L))
        if ph_prev is not None:
            while ph+off-ph_prev>180: off-=360
            while ph+off-ph_prev<-180: off+=360
        ph_prev=ph+off
        if abs(L)<1:
            return f, 180+ph_prev
    return None,None

def loop_pm(gbw, beta, rsrc, cin, zo=0.0, rload=None, cl=0.0, rsh=0.0, f=None):
    """Single-pole op amp A=gbw/(jf), feedback divider beta with source resistance rsrc
    loading input capacitance cin (pole), output resistance zo driving rsh + (rload||cl)
    (the loop is closed after rsh). Returns crossover frequency and phase margin."""
    f = np.logspace(3, 8, 200000) if f is None else f
    s = 2j*np.pi*f
    A = gbw/(f*1j)                       # ideal integrator, A(j f) = GBW/(j f)
    fb = beta/(1+s*rsrc*cin)
    L = A*fb
    if rload is not None:
        zl = rload/(1+s*rload*cl)        # load incl. capacitance
        L = L*zl/(zo+rsh+zl) if zo else L
    mag = np.abs(L)
    i = np.where(mag < 1)[0][0]
    pm = 180 + np.degrees(np.angle(L[i]))
    return f[i], pm

print("== 1. Heater driver U9 (G=2, 49.9k/49.9k, feedback after 15 ohm shunt) ==")
gbw = 2.5e6
Rf = Rg = 49.9e3
for cin in (8e-12, 10e-12, 14e-12):
    for cf in (0, 2.2e-12, 3.3e-12, 4.7e-12):
        def L(f, cin=cin, cf=cf):
            s_ = 2j*math.pi*f
            Zf = Rf/(1+s_*Rf*cf)
            beta = Rg/(Rg+Zf)/(1+s_*(Rg*Zf/(Rg+Zf))*cin)
            A = gbw/(1j*f)
            zl = 600/(1+s_*600*100e-12)          # heater 600 ohm || 100 pF (assumed)
            return A*beta*zl/(700+15+zl)         # Zo = 700 ohm (datasheet), shunt 15 ohm
        fc, pm = crossover(L)
        print(f"  Cin={cin*1e12:4.0f} pF Cf={cf*1e12:3.1f} pF: fc={fc/1e3:7.1f} kHz PM={pm:5.1f} deg")

print("\n== 2. Drain-supply U10 (R_F 10k, R_G 100k, noise gain 1.1; output 1k+10uF outside loop) ==")
Rf, Rg = 10e3, 100e3
for cin in (8e-12, 10e-12, 14e-12):
    for cf in (0, 3.3e-12, 5.6e-12):
        def L(f, cin=cin, cf=cf):
            s_ = 2j*math.pi*f
            Zf = Rf/(1+s_*Rf*cf)
            beta = Rg/(Rg+Zf)/(1+s_*((Zf*Rg)/(Zf+Rg))*cin)
            return gbw/(1j*f)*beta
        fc, pm = crossover(L)
        print(f"  Cin={cin*1e12:4.0f} pF Cf={cf*1e12:3.1f} pF: fc={fc/1e3:7.1f} kHz PM={pm:5.1f} deg")

print("\n== 3. Drain node DRN_A/B (R_D = 330 k) ==")
RD = 330e3; f0 = 518.0; w = 2*np.pi*f0
for C in (45e-12, 55e-12, 65e-12):   # assumed: TMUX1109 ~38 pF (LIA-Readout 4.4) + INA 4 + U23 1.6 + socket/trace
    fp = 1/(2*np.pi*RD*C)
    print(f"  C={C*1e12:.0f} pF: pole {fp/1e3:.1f} kHz, gain at 518 Hz {-10*np.log10(1+(f0/fp)**2):.4f} dB, phase {-np.degrees(np.arctan(f0/fp)):.2f} deg")
for dC in (1e-12, 2e-12, 5e-12, 10e-12):
    cmrr = 1/(w*RD*dC)
    print(f"  mismatch {dC*1e12:4.0f} pF: CM-to-diff conversion {1/cmrr:.2e} -> CMRR {20*np.log10(cmrr):.1f} dB")
for rin, cp in ((10e6, 11e-12), (1e6, 100e-12)):
    print(f"  scope probe {rin/1e6:.0f} Mohm || {cp*1e12:.0f} pF on one DRN node: DC loading {RD/(RD+rin)*100:.2f} % of the node resistance, extra lag {np.degrees(np.arctan(w*RD*cp)):.2f} deg")
print("  INA828 current noise 170 fA/rtHz * 330 k =", 170e-15*RD*1e9, "nV/rtHz per input")
en_rd = np.sqrt(4*1.380649e-23*300*RD)*1e9
print("  R_D thermal noise per leg", round(en_rd,1), "nV/rtHz")
en_leg = np.hypot(en_rd, 170e-15*RD*1e9)
en_diff = np.sqrt(2)*np.hypot(en_leg, 7.0/np.sqrt(2)) if False else np.hypot(np.sqrt(2)*en_leg, 7.0)
print("  differential input noise (R_D legs + INA828 e_n 7 nV):", round(en_diff,1), "nV/rtHz")
print("  fraction of the 730 nV/rtHz sensor shot noise power:", round((en_diff/730)**2*100,1), "%")
tau = 0.45
bw = 1/(4*tau)
print(f"  noise bandwidth of the post-filter (tau {tau} s): {bw:.2f} Hz -> drain-referred {en_diff*np.sqrt(bw):.0f} nV rms, at X_OUT (x38.2) {en_diff*np.sqrt(bw)*38.2/1e3:.2f} uV rms")

print("\n== 4. Signal chain levels ==")
G = 1+50e3/5.62e3
print("  INA828 G =", round(G, 3))
for vd in (15e-3, 50e-3):
    inav = vd*G
    hpf = inav*2; bpf = hpf*2
    print(f"  drain {vd*1e3:.0f} mV pk -> INA_OUT {inav:.3f} V pk, HPF_OUT {hpf:.3f} V pk, BPF_OUT {bpf:.3f} V pk, X_OUT-VMID (DC, in phase) = {(2/math.pi)*bpf*1.5:.3f} V")
print("  AN-12b mismatch 200 mV -> INA_OUT DC", 0.2*G, "V; + 0.495 V pk signal =", 0.2*G+50e-3*G, "V (INA828 swing +/-4.85 V)")
print("  OPA2196 transition region on +5 V rail: 2.0 .. 3.5 V; BPF_OUT +IN of the demod op amp reaches", 50e-3*G*4, "V at the 50 mV pk limit")

print("\n== 5. VMID_PF divider (R76 150 k / R77 100 k from VMID) ==")
r = 100e3/250e3
for name, tol, tc in (("0.1 %, 10 ppm tracking 5", 0.001, 5e-6), ("0.1 %, 25 ppm independent 50", 0.001, 50e-6), ("1 %, 100 ppm basic", 0.01, 200e-6)):
    dr = r*(1-r)*2*tol                   # worst case, opposite sign tolerances
    off = 2.5*dr*2.5                      # X_OUT - VMID = (2.5 r - 1) VMID, VMID = 2.5 V
    drift = 1.5*tc                         # V/K : 2.5*VMID*r(1-r)*dtc = 2.5*2.5*0.24*dtc
    print(f"  {name}: offset {off*1e3:.1f} mV worst, drift {drift*1e6:.0f} uV/K at X_OUT = {drift/38.2*1e6:.2f} uV/K drain-referred (AN-23b 0.2 uV/K)")
Rth = 5e3
print("  VMID with 250 k load:", round(2.5*250e3/(250e3+Rth), 4), "V (ratio unaffected)")

print("\n== 6. Output 100 ohm into loads (X_OUT centre 2.5 V) ==")
for rl in (1e6, 50.0):
    v = 2.5*rl/(rl+100); i = 2.5/(rl+100)
    print(f"  load {rl:.0f} ohm: node {v:.4f} V ({v/2.5*100:.2f} %), output current {i*1e3:.2f} mA")

print("\n== 7. DSENSE overvoltage with all pixels off (DRN = VSUP) ==")
for vsup in (2.0, 3.5):
    vo = min(8*vsup, 4.9)
    print(f"  VSUP {vsup} V: U23 output {vo:.2f} V, injected current into a clamped 3.3 V pin through 10 k: {(vo-3.3-0.3)/10e3*1e3:.2f} mA")

print("\n== 8. Heater path ==")
for rh in (600, 750, 1200, 300):
    i = 4.0/rh
    print(f"  heater {rh} ohm at 4.0 V: {i*1e3:.2f} mA, shunt drop {i*15*1e3:.0f} mV, INA190 out {i*15*25:.2f} V (limit ~3.25 V), driver output {4.0+i*15:.2f} V, switch drop {i*4.5*1e3:.0f} mV (RON 4.5 ohm max, TMUX1109 5V, 85C)")
print("  INA190 full-scale current at VS=3.3 V:", 3.25/25/15*1e3, "mA")
print("  heater DAC code input to U9 at 4.0 V:", 4.0/2, "V (OPA2196 transition region starts at +5VP-3 = 2.0 V)")

print("\n== 9. Supply headroom ==")
for vin in (8.0, 9.0, 12.0):
    vd = 0.4
    print(f"  +/-{vin:.0f} V in: rail {vin-vd:.1f} V; ADP7118 headroom {vin-vd-5:.1f} V; LDO dissipation +5VA(40 mA) {(vin-vd-5)*0.04*1e3:.0f} mW, +5VP(15 mA) {(vin-vd-5)*0.015*1e3:.0f} mW; TMUX6136 VDD-VSS = {2*(vin-vd):.1f} V (>=10 V)")

print("\n== 10. DAC noise at the drain supply ==")
H = 1/np.sqrt(1+(518/(1/(2*np.pi*1e3*10e-6)))**2)
print("  R60/C74 corner", 1/(2*np.pi*1e3*10e-6), "Hz, attenuation at 518 Hz", round(H, 4), "-> 78 nV x 1.1 x H =", round(78*1.1*H, 2), "nV/rtHz at VSUP (limit 50)")

print("\n== 11. Back-feed through TMUX6136 SEL when the board is off and REF_X is high ==")
for rs in (0, 100, 330, 1000):
    i = (3.3-0.6)/(rs+25)   # 25 ohm ~ MCU output resistance
    print(f"  series {rs} ohm: clamp current {i*1e3:.1f} mA (abs max 30 mA; STM32 pin source limit 25 mA)")
