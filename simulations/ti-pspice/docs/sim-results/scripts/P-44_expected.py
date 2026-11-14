"""Expected values for P-44: NUCLEO-F303RE DAC staircase through the gate filter (MFB U1B, R59, gate load).

Closed form, no simulator. The staircase is periodic with N samples per period, so its spectrum has lines only at
multiples m of f0. Line m of the zero-order hold output is
    X_m = C_(m mod N) * sinc(m/N) * exp(-j pi m/N)
where C_k is the DFT coefficient of one period of DAC voltages (codes x LSB). The gate line is H(j 2 pi m f0) X_m with
H the ideal MFB plus R59 and the gate capacitance. Quantization and DAC code errors are periodic, so they appear only
as harmonics of f0 and as images near multiples of N f0. The filter cannot remove harmonics below its corner.

Run: python docs/sim-results/scripts/P-44_expected.py [--mc 2000]
"""
import argparse
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--mc", type=int, default=2000, help="Monte Carlo samples of the DAC code-error model")
a = ap.parse_args()

F0, VFS, VDC = 518.0, 3.3, 1.65
R6, C7, R5, R7, C6, R59 = 120e3, 47e-9, 1e3, 1e3, 22e-9, 100.0
NH = 20  # THD over harmonics 2..NH


def h_gate(f, cgate=50e-12):
    s = 2j * np.pi * f
    h = -(R5 / R6) / (s * s * C7 * C6 * R5 * R7 + s * C6 * (R5 + R7 + R5 * R7 / R6) + 1)
    return h / (1 + s * R59 * cgate)


def lines(v, mmax):
    """Lines m = 0..mmax (complex peak amplitudes) of the ZOH staircase of one period v (N samples)."""
    n = len(v)
    c = np.fft.fft(v) / n
    m = np.arange(mmax + 1)
    x = c[m % n] * np.sinc(m / n) * np.exp(-1j * np.pi * m / n)
    x[1:] *= 2  # one-sided peak amplitude
    return m, x


def codes(n, bits, amp, phase=0.0):
    lsb = VFS / 2**bits
    k = np.arange(n)
    return np.round((VDC + amp * np.sin(2 * np.pi * k / n + phase)) / lsb), lsb


def metrics(v, n):
    mmax = 4 * n + 2
    m, x = lines(v, mmax)
    g = h_gate(m * F0) * x
    g[0] = 0
    fund = abs(g[1])
    harm = np.abs(g[2:NH + 1])
    thd = np.sqrt(np.sum(harm**2)) / fund
    inband = np.abs(g[2:int(20e3 / F0) + 1])
    thdn20k = np.sqrt(np.sum(inband**2)) / fund
    resid = np.sqrt(np.sum(np.abs(g[2:])**2) / 2)  # rms of everything but the fundamental, all lines to 4N
    img = abs(g[n - 1]) / fund
    dac_img = abs(x[n - 1]) / abs(x[1])
    return dict(fund_pk=fund, thd=thd, thdn=thdn20k, resid=resid, img=img, dac_img=dac_img,
                h=np.abs(g[2:8]), xh=np.abs(x[2:8]))


print(f"|H(f0)| = 1/{1/abs(h_gate(F0)):.3f} V/V, phase {np.degrees(np.angle(h_gate(F0))):.2f} deg")
for f in (2 * F0, 3 * F0, 5 * F0, 10 * F0, 31 * F0, 63 * F0, 127 * F0, 255 * F0):
    print(f"  |H({f/1e3:8.3f} kHz)| relative to f0: {20*np.log10(abs(h_gate(f))/abs(h_gate(F0))):7.2f} dB")

print("\nIdeal DAC (exact codes, ZOH, ideal MFB + R59 + 50 pF). THD = harmonics 2..20, THD+N = all lines 2f0..20 kHz")
print(f"{'N':>4} {'bits':>4} {'amp V':>6} {'gate mVpp':>9} {'DAC img dBc':>11} {'gate img dBc':>12} "
      f"{'THD %':>8} {'THD+N %':>8} {'resid uVrms':>11}")
for bits, amp, ns in ((12, 0.3, (32, 64, 128, 256)), (8, 0.3, (128,)), (12, 1.2, (128,))):
    for n in ns:
        c, lsb = codes(n, bits, amp)
        r = metrics(c * lsb, n)
        print(f"{n:4d} {bits:4d} {amp:6.2f} {2*r['fund_pk']*1e3:9.4f} {20*np.log10(r['dac_img']):11.2f} "
              f"{20*np.log10(r['img']):12.2f} {100*r['thd']:8.4f} {100*r['thdn']:8.4f} {r['resid']*1e6:11.3f}")

# Quantization only: compare with the classical 12-bit noise estimate
c, lsb = codes(128, 12, 0.3)
q = c * lsb - (VDC + 0.3 * np.sin(2 * np.pi * np.arange(128) / 128))
print(f"\n12 bit, N = 128, 0.3 V pk: quantization error {np.std(q)/lsb:.3f} LSB rms (uniform model 0.289 LSB)")

# DAC code-error model (assumed, not a datasheet shape): independent code errors U(-1, 1) LSB, so adjacent-code DNL
# stays within the +-2 LSB datasheet limit, plus a smooth INL bow or S-curve of peak 4 LSB over full scale.
rng = np.random.default_rng(44)
print(f"\nDAC code errors, N = 128, 12 bit, {a.mc} boards. Columns: THD % 50th / 95th / max percentile")
for amp in (0.3, 1.2):
    c, lsb = codes(128, 12, amp)
    u = (c - 2048) / 2048
    for name in ("random +-1 LSB", "bow 4 LSB", "S-curve 4 LSB", "random + bow + S"):
        t = []
        for _ in range(a.mc):
            err = np.zeros(4096)
            if "random" in name:
                err += rng.uniform(-1, 1, 4096)
            uu = np.linspace(-1, 1, 4096)
            if "bow" in name or "+ S" in name:
                err += 4 * (1 - uu**2) * rng.choice((-1, 1)) * (rng.uniform(0, 1) if "+" in name else 1)
            if "S-curve" in name or "+ S" in name:
                err += 4 * 2.598 * uu * (1 - uu**2) * rng.choice((-1, 1)) * (rng.uniform(0, 1) if "+" in name else 1)
            v = (c + err[c.astype(int)]) * lsb
            t.append(metrics(v, 128)["thd"])
            if "random" not in name and "+" not in name:
                break  # deterministic shape: one sample is enough
        t = np.array(t) * 100
        print(f"  {amp:4.2f} V pk  {name:18s} {np.percentile(t,50):8.4f} {np.percentile(t,95):8.4f} {t.max():8.4f}")
