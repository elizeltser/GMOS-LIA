"""Expected values for the LIA-AFE-Eval index entries P-23 to P-34.

Ideal (op amps with infinite gain) transfer functions of the LIA-AFE-Eval
netlist exported on 2026-11-07 (commit 3429288). Component values are the
schematic values. Run: python afe_eval_expected.py [--mc]
"""
import sys
import numpy as np

kB, q, T = 1.380649e-23, 1.602176634e-19, 300.0
f0 = 518.0

# Front end
RG = 5.62e3
G_INA = 1 + 50e3 / RG
R9 = R11 = R12 = R13 = 9.31e3
C9 = C10 = C11 = C12 = 33e-9
K = 2.0  # 1 + R70/R71 = 1 + R72/R73


def hpf(f, R1=R9, R2=R13, C1=C10, C2=C11, k=K):
    """Sallen-Key high-pass, C10 then C11 in series, R9 to the output, R13 to GND."""
    s = 2j * np.pi * f
    num = k * s**2
    den = s**2 + s * (1 / (R2 * C1) + 1 / (R2 * C2) + (1 - k) / (R1 * C1)) + 1 / (R1 * R2 * C1 * C2)
    return num / den


def lpf(f, R1=R11, R2=R12, C1=C9, C2=C12, k=K):
    """Sallen-Key low-pass, R11 then R12, C9 to the output, C12 to GND."""
    s = 2j * np.pi * f
    w = 1 / (R1 * R2 * C1 * C2)
    den = s**2 + s * (1 / (R1 * C1) + 1 / (R2 * C1) + (1 - k) / (R2 * C2)) + w
    return k * w / den


def front(f):
    return G_INA * hpf(f) * lpf(f)


def mfb(f, R1=120e3, R2=1e3, R3=1e3, C1=47e-9, C2=22e-9):
    """MFB low-pass: R1 (R6) input, C1 (C7) to GND, R2 (R5) to output, R3 (R7) to -IN, C2 (C6) -IN to output."""
    s = 2j * np.pi * f
    return -(1 / (R1 * R3 * C1 * C2)) / (s**2 + s / C1 * (1 / R1 + 1 / R2 + 1 / R3) + 1 / (R2 * R3 * C1 * C2))


def sk_post(f, R=200e3, C=1.5e-6):
    """Unity-gain Sallen-Key low-pass with equal parts (R14 R15 C13 C15), Q = 0.5."""
    s = 2j * np.pi * f
    w = 1 / (R * R * C * C)
    return w / (s**2 + s * 2 / (R * C) + w)


def section(title):
    print("\n== " + title)


section("Front end at f0 = 518 Hz")
fc = 1 / (2 * np.pi * R9 * C10)
print(f"section f0 = {fc:.2f} Hz, Q = {1/(3-K):.3f}, G_INA = {G_INA:.4f} V/V")
for f in (f0, fc):
    H = front(f)
    print(f"f = {f:.2f} Hz: |H| = {abs(H):.4f} V/V, phase = {np.degrees(np.angle(H)):+.3f} deg")
fs = np.linspace(100, 2000, 190001)
Hm = abs(front(fs))
ipk = Hm.argmax()
band = fs[Hm >= Hm[ipk] / np.sqrt(2)]
print(f"peak {Hm[ipk]:.4f} V/V at {fs[ipk]:.2f} Hz, -3 dB band {band[0]:.1f} to {band[-1]:.1f} Hz")
for f in (50, 100, 150, 2 * f0, 3 * f0, 500, 550, 5e3):
    H = front(f)
    print(f"  f = {f:7.1f} Hz: |H| = {abs(H):.5f} V/V ({20*np.log10(abs(H)/abs(front(f0))):+.2f} dB rel f0), "
          f"phase {np.degrees(np.angle(H)):+.2f} deg")
# phase slope at f0
d = 0.01
slope = np.degrees(np.angle(front(f0 + d)) - np.angle(front(f0 - d))) / (2 * d)
print(f"phase slope at f0 = {slope:.4f} deg/Hz")

section("Chain scale factor (sine at the drains, square-wave demodulator, unity post-filter)")
H0 = front(f0)
print(f"X_OUT = (2/pi) |H| v_pk cos(theta) = {2/np.pi*abs(H0):.4f} x v_pk cos(theta)")
for v in (1e-3, 10e-3, 15e-3, 50e-3):
    print(f"  v_pk = {v*1e3:5.1f} mV: BPF_OUT = {abs(H0)*v*1e3:8.2f} mV pk, X_OUT = {2/np.pi*abs(H0)*v*1e3:8.3f} mV")
print("Demodulator: SEL = 1 -> S1A (BPF_OUT) -> output +BPF_OUT; SEL = 0 -> S1B (GND) -> -BPF_OUT.")
print("REF_X high in the first half period, input sin(wt + theta): X = +(2/pi) A cos(theta) ... see sign note below")
# sign: mean over period of sign(sin wt) * A sin(wt+theta) = (2/pi) A cos(theta)
t = np.linspace(0, 1, 200001)[:-1]
for th in (0, 90):
    sig = np.sin(2 * np.pi * t + np.radians(th))
    ref = np.where(t < 0.5, 1, -1)
    print(f"  theta = {th:3d} deg: mean(ref*sin) = {np.mean(ref*sig):+.5f} (2/pi cos = {2/np.pi*np.cos(np.radians(th)):+.5f})")

section("Demodulator output ripple and post-filter")
A = 1.0
# full-wave rectified sine at theta = 0: 2f0 component amplitude 4A/(3 pi)
r2 = 4 * A / (3 * np.pi)
print(f"2f0 component at X_DEM_OUT for theta = 0: {r2:.4f} x A pk")
fpf = 1 / (2 * np.pi * 200e3 * 1.5e-6)
print(f"post-filter fc (double pole) = {fpf:.4f} Hz, tau per pole = {200e3*1.5e-6:.3f} s")
for f in (2 * f0, 1.0, 18.0, 32.0, fpf):
    print(f"  |H_post({f:.3f} Hz)| = {abs(sk_post(f)):.3e} ({20*np.log10(abs(sk_post(f))):.1f} dB)")
# settling of the critically damped pair: error = (1 + t/tau) exp(-t/tau)
tau = 0.3
for tt in (1, 2, 3, 4, 5):
    print(f"  step settling at {tt} s: error {(1+tt/tau)*np.exp(-tt/tau):.2e}")
taus = 200e3 * 15e-9  # fast variant with C13..C16 = 15 nF
print(f"fast variant cpf = 15 nF: tau = {taus*1e3:.1f} ms, |H(2f0)| = {abs(sk_post(2*f0, C=15e-9)):.3e}")
for tt in (0.03, 0.05, 0.08, 0.1):
    print(f"  fast step settling at {tt*1e3:.0f} ms: error {(1+tt/taus)*np.exp(-tt/taus):.2e}")

section("Interference at the in-amp input, X_OUT rejection relative to an f0 signal of equal amplitude")
# Interferer at f_i: demodulator products at |f_i - n f0| for odd n, weight 2/(n pi) each.
for fi in (50, 150, 500, 550, 2 * f0, 3 * f0):
    Hi = abs(front(fi))
    worst = 0.0
    for n in (1, 3, 5, 7):
        fb = abs(fi - n * f0)
        a = Hi * 2 / (n * np.pi) * (abs(sk_post(fb)) if fb > 0 else 1.0)
        worst = max(worst, a)
    ref = abs(front(f0)) * 2 / np.pi
    print(f"  f_i = {fi:6.1f} Hz: |H_front| = {Hi:.4f}, worst beat amplitude ratio {worst/ref:.3e} ({20*np.log10(max(worst,1e-30)/ref):.1f} dB)")
print("  3f0 is demodulated to DC with weight 1/3 by the square reference: DC ratio "
      f"{abs(front(3*f0))/3/abs(front(f0)):.4f} ({20*np.log10(abs(front(3*f0))/3/abs(front(f0))):.1f} dB)")

section("Excitation MFB at 518 Hz")
Hm0 = mfb(f0)
print(f"|H| = {abs(Hm0):.6e} (1/{1/abs(Hm0):.2f}), phase {np.degrees(np.angle(Hm0)):+.3f} deg (incl. the 180 deg inversion)")
w0 = 1 / np.sqrt(1e3 * 1e3 * 47e-9 * 22e-9)
Q = np.sqrt(47e-9 / 22e-9) * np.sqrt(1e3 * 1e3) / (1e3 + 1e3 + 1e3 * 1e3 / 120e3)
print(f"f0_mfb = {w0/2/np.pi:.1f} Hz, Q = {Q:.3f}, DC gain {-1e3/120e3:.6f}")
print(f"lag vs ideal -1/120 at 518 Hz: {np.degrees(np.angle(Hm0/(-1/120))):+.3f} deg, amplitude {abs(Hm0)*120:.5f}")
fs_dac = 128 * f0
Him = mfb(fs_dac - f0)
print(f"DAC image at {fs_dac - f0:.0f} Hz: |H_mfb| rel f0 = {abs(Him)/abs(Hm0):.3e} ({20*np.log10(abs(Him)/abs(Hm0)):.1f} dB);"
      " image amplitude of a 128-step ZOH before filtering is sinc-weighted:")
x = np.pi * (fs_dac - f0) / fs_dac
x1 = np.pi * f0 / fs_dac
img = (np.sin(x) / x) / (np.sin(x1) / x1)  # first ZOH image relative to the fundamental (1/127 for N = 128)
print(f"  ZOH image/fundamental = {img:.4e} ({20*np.log10(img):.1f} dBc), at the gate {20*np.log10(img*abs(Him)/abs(Hm0)):.1f} dBc")
print(f"  ZOH delay of half a sample = {360*0.5/128:.3f} deg")
print("Gate DC: V_GATE = (1 + R5/R6) V_GATE_DC - (R5/R6) V_EXC_DC")
for vg, ve in ((1.0, 1.65), (1.1, 1.65)):
    print(f"  GATE_DC = {vg} V, EXC_DC = {ve} V -> GATE = {(1+1/120)*vg - ve/120:.5f} V")

section("Drain node and CMRR (pixel as ideal current sink)")
RD, Cn = 330e3, 50e-12
Zd = RD / (1 + 2j * np.pi * f0 * RD * Cn)
print(f"Z_drain(518 Hz) with C_node = 50 pF: |Z| = {abs(Zd)/1e3:.2f} kOhm, phase {np.degrees(np.angle(Zd)):+.3f} deg")
id_ = 7.5e-6
print(f"drain DC = V_SUP - {RD*id_:.4f} V; for V_SUP = 1.1*2.4 V = 2.64 V -> {2.64 - RD*id_:.4f} V")
print("CMRR: common-mode current i_cm into both drains, differential error from Z mismatch:")
print("  v_diff/v_cm = dZ/Z = dR/R (1 - j w R C)/(1 + j w R C) ... |dZ/Z| ~ sqrt(dR^2 + (wRC)^2 (dR+dC)^2)/(1+(wRC)^2)")
if "--mc" in sys.argv:
    rng = np.random.default_rng(1)
    N = 200000
    w = 2 * np.pi * f0
    Ra = RD * (1 + rng.uniform(-1e-3, 1e-3, N))
    Rb = RD * (1 + rng.uniform(-1e-3, 1e-3, N))
    Ca = Cn * (1 + rng.uniform(-0.1, 0.1, N))
    Cb = Cn * (1 + rng.uniform(-0.1, 0.1, N))
    Za = Ra / (1 + 1j * w * Ra * Ca)
    Zb = Rb / (1 + 1j * w * Rb * Cb)
    ratio = abs(Za - Zb) / abs((Za + Zb) / 2)
    cm = -20 * np.log10(ratio)
    print(f"  MC R 0.1 % U, C 50 pF +/-10 % U: CMRR median {np.median(cm):.1f} dB, 5 % {np.percentile(cm,5):.1f} dB, 95 % {np.percentile(cm,95):.1f} dB")
    Ca = Cb = Cn
    Za = Ra / (1 + 1j * w * Ra * Ca)
    Zb = Rb / (1 + 1j * w * Rb * Cb)
    cm = -20 * np.log10(abs(Za - Zb) / abs((Za + Zb) / 2))
    print(f"  MC R only: median {np.median(cm):.1f} dB, 5 % {np.percentile(cm,5):.1f} dB")
    # band-pass tolerance: R 0.1 % (gain set and filter), C 5 % and 1 %
    for ctol in (0.05, 0.01):
        def u(t):
            return 1 + rng.uniform(-t, t, N)
        kk = 1 + (10e3 * u(1e-3)) / (10e3 * u(1e-3))
        k2 = 1 + (10e3 * u(1e-3)) / (10e3 * u(1e-3))
        Hh = hpf(f0, R9 * u(1e-3), R13 * u(1e-3), C10 * u(ctol), C11 * u(ctol), kk)
        Hl = lpf(f0, R11 * u(1e-3), R12 * u(1e-3), C9 * u(ctol), C12 * u(ctol), k2)
        H = (1 + 50e3 / (RG * u(1e-3))) * Hh * Hl
        g = (abs(H) / abs(front(f0)) - 1) * 100
        ph = np.degrees(np.angle(H) - np.angle(front(f0)))
        print(f"  BPF MC C {ctol*100:.0f} % U, R 0.1 % U: gain err mean {g.mean():+.3f} %, std {g.std():.3f} %, "
              f"2.5..97.5 % {np.percentile(g,2.5):+.2f}..{np.percentile(g,97.5):+.2f} %; phase std {ph.std():.3f} deg, "
              f"2.5..97.5 % {np.percentile(ph,2.5):+.2f}..{np.percentile(ph,97.5):+.2f} deg")

section("Noise at the drains (per side) and referred to the differential input")
e_shot = np.sqrt(2 * q * id_) * RD
e_rd = np.sqrt(4 * kB * T * RD)
e_diff = np.sqrt(2 * (e_shot**2 + e_rd**2))
print(f"shot {e_shot*1e9:.1f} nV/rtHz, R_D thermal {e_rd*1e9:.1f} nV/rtHz per side, differential {e_diff*1e9:.1f} nV/rtHz")
print(f"10 % of the power: amplifier budget {e_diff*np.sqrt(0.1/0.9)*1e9:.1f} nV/rtHz input-referred")
# post-filter ENBW of two coincident poles: 1/(8 tau) for a critically damped 2nd order? ENBW = 1/(8*tau) * ... compute numerically
fq = np.linspace(0, 50, 2000001)
enbw = np.trapezoid(abs(sk_post(fq))**2, fq)
print(f"post-filter ENBW = {enbw:.4f} Hz (tau = 0.3 s per pole)")
fold = 0.0
for n in range(1, 400, 2):
    fold += (4 / (n * np.pi))**2 / 2 * abs(front(n * f0))**2
fold = np.sqrt(fold) / abs(front(f0))
print(f"square-wave fold-down factor (white input noise) = {fold:.4f}")
vn_out = e_diff * abs(front(f0)) * fold * np.sqrt(enbw)
print(f"X_OUT rms noise from the sensor alone = {vn_out*1e6:.2f} uV rms")
print(f"DAC-noise path: VSUP RC (R60 1k, C74 10u) |H(518 Hz)| = {1/abs(1+2j*np.pi*f0*1e3*10e-6):.4e}")

section("Rails with B5819W series diodes (Vf assumed 0.30..0.45 V at the load current, not verified)")
for vin in (5.0, 5.2, 5.5):
    for vf in (0.30, 0.45):
        print(f"  bench {vin} V, Vf {vf} V -> +5VIN {vin-vf:.2f} V; DAC80508 VDD/2 = {(vin-vf)/2:.3f} V vs internal ref 2.5 V")
print("OPA2196 input transition region V+ - 3 V .. V+ - 1.5 V (SBOS869 per review 2026-10-29 F-08):")
for vp in (4.55, 4.7, 5.0):
    print(f"  V+ = {vp} V -> {vp-3:.2f} V .. {vp-1.5:.2f} V")
