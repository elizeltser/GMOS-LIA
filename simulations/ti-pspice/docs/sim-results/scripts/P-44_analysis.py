"""P-44 analysis: NUCLEO-F303RE DAC staircase through the gate filter (MFB U1B, R59, gate load).

Run from simulations/ti-pspice:
    python docs/sim-results/scripts/P-44_analysis.py [--mc 2000]

It reads sim-runs/<run>/<run>.csd (transient runs P44_ref, P44a_*, P44b_*; AC runs P44c_ac, P44c_ac_off),
fits the waveforms on a uniform 0.1 us grid over the window 10 T to 30 T, compares them with the closed form
of P-44_expected.py (its functions are executed from the file, its prints and Monte Carlo are skipped),
repeats the code-error Monte Carlo with the measured transfer function, and writes the figures
docs/sim-results/figures/P-44_*.png. Every number in docs/sim-results/P-44.md is printed by this script.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mc", type=int, default=2000, help="Monte Carlo boards (same seed and model as P-44_expected.py)")
args = ap.parse_args()

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # simulations/ti-pspice
FIG = ROOT / "docs/sim-results/figures"
FIG.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

# ---------------------------------------------------------------- closed form from P-44_expected.py
EXP = HERE / "P-44_expected.py"
_head = EXP.read_text(encoding="utf-8").split('print(f"|H(f0)|')[0]
_argv = sys.argv
sys.argv = [str(EXP), "--mc", "1"]
ns = {"__file__": str(EXP), "__name__": "p44_expected"}
exec(compile(_head, str(EXP), "exec"), ns)
sys.argv = _argv
lines, codes, metrics_ns, NH = ns["lines"], ns["codes"], ns["metrics"], ns["NH"]
F0, VDC, VFS = ns["F0"], ns["VDC"], ns["VFS"]
R5, R6, R7, C6, C7, R59 = ns["R5"], ns["R6"], ns["R7"], ns["C6"], ns["C7"], ns["R59"]
CGATE = 50e-12
TAU_E = 100e-9  # PSpice edge time of the staircase (gen_exc_stair.py, --edge default)
MMAX = 4000  # lines kept in the closed form (about 2 MHz)

# ---------------------------------------------------------------- window and grid (entry P-44)
DT = 1e-7
T0 = 10 / F0
NPTS = 386100  # 38.61 ms at 0.1 us = 20 periods less 38.6 ns
TG = T0 + DT * np.arange(NPTS)
T1 = TG[-1]
HALF = NPTS // 2  # 10 periods
DUR = 1 / F0
DEG = 180 / np.pi


def s_of(f):
    return 2j * np.pi * np.asarray(f, float)


def h_out(f, r6=R6):
    """V(GOUT)/V(EXC_DAC) of the ideal MFB (same formula as P-44_expected.py, without the gate load)."""
    s = s_of(f)
    return -(R5 / r6) / (s * s * C7 * C6 * R5 * R7 + s * C6 * (R5 + R7 + R5 * R7 / r6) + 1)


def h_mfb(f, r6=R6, cgate=CGATE):
    """V(GATE)/V(EXC_DAC) of the ideal MFB with R59 and the gate capacitance."""
    return h_out(f, r6) / (1 + s_of(f) * R59 * cgate)


def y_in(f, r6=R6):
    """Admittance seen at EXC_DAC by the MFB input (R6 into NC7), ideal op amp, U1BM at AC ground."""
    s = s_of(f)
    b = 1 / r6 + s * C7 + 1 / R7 + (1 / R5) * (1 + 1 / (s * R7 * C6))
    return (1 / r6) * (1 - 1 / (r6 * b))


def ed_rc(f, rdac, cdac, r6=R6):
    """V(EXC_DAC)/V(source) for a series rdac from the source and a shunt cdac at EXC_DAC."""
    yr = 1.0 / rdac
    return yr / (yr + s_of(f) * cdac + y_in(f, r6))


def parse_val(txt):
    m = re.match(r"([0-9.eE+-]+)(meg|[a-zA-Z]?)", txt.strip().lower())
    mult = {"": 1, "k": 1e3, "meg": 1e6, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12}
    return float(m.group(1)) * mult[m.group(2)]


def netlist_value(path, pattern):
    m = re.search(pattern, path.read_text(encoding="utf-8"), flags=re.M)
    return parse_val(m.group(1))


# netlist check: the closed form constants must match the simulated netlist
_net = ROOT / "sim-runs/P44a_N128/P44a_N128.cir"
for _name, _val, _pat in [
    ("R6", R6, r"^R_R6\s+\S+\s+\S+\s+(\S+)"),
    ("R5", R5, r"^R_R5\s+\S+\s+\S+\s+(\S+)"),
    ("R7", R7, r"^R_R7\s+\S+\s+\S+\s+(\S+)"),
    ("C7", C7, r"^C_C7\s+\S+\s+\S+\s+(\S+)"),
    ("C6", C6, r"^C_C6\s+\S+\s+\S+\s+(\S+)"),
    ("R59", R59, r"^R_R59\s+\S+\s+\S+\s+(\S+)"),
]:
    assert abs(netlist_value(_net, _pat) - _val) < 1e-12 * _val, _name
assert abs(netlist_value(_net, r"^\.PARAM .*cgate=(\S+)") - CGATE) < 1e-18
# the MFB denominator identity: input admittance formula reproduces the closed form
_f = np.array([50.0, 518.0, 65786.0, 1e6])
_s = s_of(_f)
_b = 1 / R6 + _s * C7 + 1 / R7 + (1 / R5) * (1 + 1 / (_s * R7 * C6))
assert np.allclose(-(1 / R6) / (_b * _s * R7 * C6), h_out(_f), rtol=1e-10, atol=0)
# a series 15 kOhm in front of R6 is the same as R6 = 135 kOhm (no other element at EXC_DAC)
assert np.allclose(h_mfb(_f, R6 + 15e3), h_mfb(_f) * ed_rc(_f, 15e3, 0.0), rtol=1e-9, atol=0)
print("Checks passed: netlist values, input admittance, series 15 kOhm equals R6 + 15 kOhm.")

# ---------------------------------------------------------------- basis and least-squares fit
RUNS = [
    # name, kind, N, bits, amplitude (V pk at the source)
    ("P44_ref", "sin", 128, 12, 0.3),
    ("P44a_N32", "stair", 32, 12, 0.3),
    ("P44a_N64", "stair", 64, 12, 0.3),
    ("P44a_N128", "stair", 128, 12, 0.3),
    ("P44a_N256", "stair", 256, 12, 0.3),
    ("P44a_8b", "stair", 128, 8, 0.3),
    ("P44a_max", "stair", 128, 12, 1.2),
    ("P44b_tau05", "rc", 128, 12, 0.3),
    ("P44b_tau1", "rc", 128, 12, 0.3),
    ("P44b_off", "off", 128, 12, 0.3),
]
ENTRY = {  # P-44 index entry, table for the ideal MFB
    "P44a_N32": dict(mvpp=4.9936, dac=-29.83, img=-50.27, thd=0.066, thdn=0.404, resid=7.19),
    "P44a_N64": dict(mvpp=5.0000, dac=-35.99, img=-68.75, thd=0.034, thdn=0.036, resid=1.09),
    "P44a_N128": dict(mvpp=5.0015, dac=-42.08, img=-87.02, thd=0.031, thdn=0.033, resid=0.59),
    "P44a_N256": dict(mvpp=5.0023, dac=-48.13, img=-105.19, thd=0.020, thdn=0.021, resid=0.38),
    "P44a_8b": dict(mvpp=5.0156, dac=-42.08, img=-87.02, thd=0.609, thdn=0.616, resid=10.93),
    "P44a_max": dict(mvpp=20.0077, dac=-42.08, img=-87.02, thd=0.007, thdn=0.008, resid=0.70),
}
_basis = {}


def ks_for(n):
    imgs = [] if n is None else [n - 1, n + 1, 2 * n - 1, 2 * n + 1]
    return list(range(1, NH + 1)) + sorted(set(imgs))


def design(n):
    if n not in _basis:
        ks = ks_for(n)
        cols = [np.ones(NPTS)]
        for k in ks:
            w = 2 * np.pi * k * F0 * TG
            cols += [np.sin(w), np.cos(w)]
        _basis[n] = (ks, np.column_stack(cols))
    return _basis[n]


def fit(y, n, sl=slice(None)):
    ks, A = design(n)
    coef = np.linalg.lstsq(A[sl], y[sl], rcond=None)[0]
    amp = {}
    for i, k in enumerate(ks):
        a, b = coef[1 + 2 * i], coef[2 + 2 * i]
        amp[k] = dict(a=a, b=b, pk=float(np.hypot(a, b)), ph=float(DEG * np.arctan2(b, a)))
    return dict(dc=float(coef[0]), amp=amp, coef=coef, ks=ks, A=A)


def residual(y, fr):
    """Gate minus DC and the fitted fundamental (unfiltered)."""
    c = fr["coef"]
    return y - c[0] - c[1] * fr["A"][:, 1] - c[2] * fr["A"][:, 2]


def band_thdn(r, a1):
    """THD+N to 20 kHz: FFT of the residual (DC and fundamental removed), brick wall at 20 kHz."""
    R = np.fft.rfft(r)
    fr = np.fft.rfftfreq(NPTS, DT)
    band = (fr > 0) & (fr <= 20e3)
    p = 2 * np.sum(np.abs(R[band]) ** 2) / NPTS**2  # mean square in the band
    return np.sqrt(p) / (a1 / np.sqrt(2)), np.sqrt(p)


def img_levels(fr, n, a1):
    out = {}
    if n is None:
        return out
    for k in (n - 1, n + 1, 2 * n - 1, 2 * n + 1):
        out[k] = 20 * np.log10(fr["amp"][k]["pk"] / a1)
    return out


def edge_check(tt, n):
    """Fraction of staircase edges (k ts and k ts + 100 ns) with a solver time point within 5 ns."""
    ts = 1 / (F0 * n)
    sel = (tt >= T0) & (tt <= T1)
    tw = np.sort(tt[sel])
    k = np.arange(int(np.ceil(T0 / ts)), int(np.floor(T1 / ts)) - 1)
    res = []
    for e in (k * ts, k * ts + TAU_E):
        i = np.clip(np.searchsorted(tw, e), 1, len(tw) - 1)
        d = np.minimum(np.abs(tw[i] - e), np.abs(tw[i - 1] - e))
        res.append(np.mean(d < 5e-9))
    return min(res), float(np.median(np.diff(tw)))


# ---------------------------------------------------------------- closed form per run
def closed(n, bits, amp, Hs, Ed, rnd=False):
    c, lsb = codes(n, bits, amp)
    v = c * lsb
    if rnd:
        v = np.round(v, 6)  # gen_exc_stair.py writes the levels with {v:.6f}
    m, x = lines(v, MMAX)
    f = np.maximum(m, 1) * F0
    xs = x * np.sinc(f * TAU_E) * np.exp(-1j * np.pi * f * TAU_E)
    g = Hs(f) * xs
    ge = Ed(f) * xs
    g1, e1 = g[1], ge[1]
    return dict(
        gate_mvpp=2 * abs(g1) * 1e3,
        gate_ph=float(DEG * np.angle(g1)) + 90.0,
        exc_ph=float(DEG * np.angle(e1)) + 90.0,
        exc_mvpp=2 * abs(e1) * 1e3,
        thd=np.sqrt(np.sum(np.abs(g[2:NH + 1]) ** 2)) / abs(g1),
        thdn=np.sqrt(np.sum(np.abs(g[2:int(20e3 / F0) + 1]) ** 2)) / abs(g1),
        resid_uv=np.sqrt(np.sum(np.abs(g[2:]) ** 2) / 2) * 1e6,
        img_gate=20 * np.log10(abs(g[n - 1]) / abs(g1)),
        img_exc=20 * np.log10(abs(ge[n - 1]) / abs(e1)),
        h_uv=np.abs(g[2:8]) * 1e6,
        g=g,
        ge=ge,
        m=m,
    )


def thd_mc(v, n, Hfun):
    m, x = lines(v, 4 * n + 2)
    g = Hfun(np.maximum(m, 1) * F0) * x
    return np.sqrt(np.sum(np.abs(g[2:NH + 1]) ** 2)) / abs(g[1])


def make_H(fg, H):
    lf = np.log10(fg)
    mdb = 20 * np.log10(np.abs(H))
    ph = np.unwrap(np.angle(H))

    def Hf(f):
        l = np.log10(np.maximum(np.asarray(f, float), 1.0))
        return 10 ** (np.interp(l, lf, mdb) / 20) * np.exp(1j * np.interp(l, lf, ph))

    return Hf


def corner(Hf):
    fg = np.logspace(np.log10(F0), 6, 6000)
    mag = 20 * np.log10(np.abs(Hf(fg)))
    drop = mag - 20 * np.log10(abs(Hf(np.array([F0]))[0]))
    i = int(np.argmax(drop <= -3.0))
    l1, l2 = np.log10(fg[i - 1]), np.log10(fg[i])
    d1, d2 = drop[i - 1], drop[i]
    return 10 ** (l1 + (-3 - d1) / (d2 - d1) * (l2 - l1))


# ---------------------------------------------------------------- AC data (P44c)
def load_csd(name):
    return read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")[0]


ac_on = load_csd("P44c_ac")
ac_off = load_csd("P44c_ac_off")
fac = np.asarray(ac_on.x, float)
H_on_raw = np.asarray(ac_on["V(GATE)"]) / np.asarray(ac_on["V(EXC_DAC)"])
H_off_raw = np.asarray(ac_off["V(GATE)"]) / 1.0  # AC source = 1 V (EXC_IDEAL), gate over source
Ed_off_raw = np.asarray(ac_off["V(EXC_DAC)"]) / 1.0
assert np.allclose(np.asarray(ac_on["V(EXC_DAC)"]), 1.0)  # buffer on: EXC_DAC is the source
Hm_on = make_H(fac, H_on_raw)
Hm_off = make_H(fac, H_off_raw)
Ed_off_m = make_H(fac, Ed_off_raw)
H_ideal_on = lambda f: h_mfb(f)  # noqa: E731
H_ideal_off = lambda f: h_mfb(f, R6 + 15e3)  # noqa: E731

print("\n== P44c: measured transfer GATE/source against the ideal MFB (AC runs)")
print(f"{'f (Hz)':>10} {'|H| meas dB':>12} {'|H| ideal dB':>13} {'diff dB':>8} {'ph meas deg':>12} "
      f"{'ph ideal deg':>12} {'diff deg':>9} {'off diff dB':>11}")
for f in (10, 100, 518, 1000, 2590, 5180, 10000, 16060, 20000, 50000, 65786, 66822, 100000, 200000, 500000, 1e6):
    hm = Hm_on(f)
    hi = H_ideal_on(f)
    ho = Hm_off(f)
    hoi = H_ideal_off(f)
    print(f"{f:10.0f} {20*np.log10(abs(hm)):12.3f} {20*np.log10(abs(hi)):13.3f} "
          f"{20*np.log10(abs(hm/hi)):8.3f} {DEG*np.angle(hm):12.4f} {DEG*np.angle(hi):12.4f} "
          f"{DEG*np.angle(hm/hi):9.4f} {20*np.log10(abs(ho/hoi)):11.3f}")
Hm_grid = H_on_raw
Hi_grid = H_ideal_on(fac)
dB_grid = 20 * np.log10(np.abs(Hm_grid / Hi_grid))
le100 = fac <= 100e3
i_max = np.argmax(np.abs(dB_grid) * le100)
i_05 = np.argmax((np.abs(dB_grid) > 0.5) & le100) if np.any((np.abs(dB_grid) > 0.5) & le100) else -1
img_sel = (fac >= 60e3) & (fac <= 70e3)
print(f"max |diff| 10 Hz to 100 kHz: {abs(dB_grid[i_max]):.3f} dB at {fac[i_max]:.1f} Hz (grid points)")
print(f"first grid point above 0.5 dB: {fac[i_05]:.1f} Hz, diff {dB_grid[i_05]:+.3f} dB" if i_05 >= 0 else
      "no grid point above 0.5 dB up to 100 kHz")
print(f"max |diff| 60 to 70 kHz (image region): {np.max(np.abs(dB_grid[img_sel])):.3f} dB")
print(f"diff above 100 kHz: max {np.max(np.abs(dB_grid[fac > 100e3])):.2f} dB at 1 MHz edge, "
      f"diff at 1 MHz {dB_grid[-1]:+.2f} dB")
print("worst +/- diff, 10 Hz to 100 kHz:", f"{dB_grid[le100].max():+.3f} dB / {dB_grid[le100].min():+.3f} dB")
# buffer off: measured against closed form R6 = 135 kOhm, up to 100 kHz
dB_off = 20 * np.log10(np.abs(H_off_raw / H_ideal_off(fac)))
print(f"buffer off, measured vs closed (R6 = 135 kOhm) up to 100 kHz: max |diff| "
      f"{np.max(np.abs(dB_off[le100])):.4f} dB")
print("corner (-3 dB re 518 Hz): ideal R6=120k", f"{corner(H_ideal_on):.1f} Hz,",
      "measured buffer on", f"{corner(Hm_on):.1f} Hz,",
      "closed R6=135k", f"{corner(H_ideal_off):.1f} Hz,", "measured buffer off", f"{corner(Hm_off):.1f} Hz")
print(f"gain re 518 Hz: buffer off measured {20*np.log10(abs(Hm_off(F0))/abs(Hm_on(F0))):.4f} dB, "
      f"closed {20*np.log10(abs(H_ideal_off(F0))/abs(H_ideal_on(F0))):.4f} dB")
print(f"|H(518 Hz)| buffer on: 1/{1/abs(Hm_on(F0)):.4f}, ideal 1/{1/abs(H_ideal_on(F0)):.4f}; "
      f"phase on {DEG*np.angle(Hm_on(F0)):+.4f} deg, ideal {DEG*np.angle(H_ideal_on(F0)):+.4f} deg")
print(f"buffer off: |H(518 Hz)| 1/{1/abs(Hm_off(F0)):.4f}, closed 1/{1/abs(H_ideal_off(F0)):.4f}; "
      f"phase meas {DEG*np.angle(Hm_off(F0)):+.4f}, closed {DEG*np.angle(H_ideal_off(F0)):+.4f} deg")
print(f"EXC_DAC / source, buffer off, measured: {abs(Ed_off_m(F0)):.6f}  (120/135 = {120/135:.6f})")

# ---------------------------------------------------------------- transient runs
ANA = {}
for name, kind, n, bits, amp in RUNS:
    sec = load_csd(name)
    tt = np.asarray(sec.x, float)
    sigs = ["V(EXC_DAC)", "V(GATE)"] + (["V(EXC_IDEAL)"] if kind in ("rc", "off") else [])
    y = {s: np.interp(TG, tt, np.asarray(sec[s], float)) for s in sigs}
    nb = n if n is not None else 128
    G = fit(y["V(GATE)"], nb)
    E = fit(y["V(EXC_DAC)"], nb)
    a1g = G["amp"][1]["pk"]
    a1e = E["amp"][1]["pk"]
    rg = residual(y["V(GATE)"], G)
    thdn, thdn_rms = band_thdn(rg, a1g)
    rms_t = float(np.sqrt(np.mean(rg**2)))
    harm = {k: G["amp"][k]["pk"] for k in range(2, NH + 1)}
    thd = np.sqrt(sum(v * v for v in harm.values())) / a1g
    # settling: fundamental in the first and the second 10 periods
    G1 = fit(y["V(GATE)"], nb, slice(0, HALF))
    G2 = fit(y["V(GATE)"], nb, slice(HALF, None))
    E1 = fit(y["V(EXC_DAC)"], nb, slice(0, HALF))
    E2 = fit(y["V(EXC_DAC)"], nb, slice(HALF, None))
    ANA[name] = dict(
        kind=kind, n=n, bits=bits, amp=amp, G=G, E=E, a1g=a1g, a1e=a1e, rg=rg,
        mvpp=2 * a1g * 1e3, ph=G["amp"][1]["ph"], eph=E["amp"][1]["ph"],
        dc=G["dc"], edc=E["dc"], harm=harm, thd=thd, thdn=thdn, thdn_rms=thdn_rms, resid=rms_t * 1e6,
        img_g=img_levels(G, n, a1g) if n else {}, img_e=img_levels(E, n, a1e) if n else {},
        settle_g=100 * (G2["amp"][1]["pk"] - G1["amp"][1]["pk"]) / G2["amp"][1]["pk"],
        settle_gph=G2["amp"][1]["ph"] - G1["amp"][1]["ph"],
        settle_e=100 * (E2["amp"][1]["pk"] - E1["amp"][1]["pk"]) / E2["amp"][1]["pk"],
        settle_eph=E2["amp"][1]["ph"] - E1["amp"][1]["ph"],
        tt=tt, y=y,
    )
    if kind != "sin":
        ANA[name]["edge"] = edge_check(tt, n)
    # Parseval check of the residual band power (sanity)
    p_all = 2 * np.sum(np.abs(np.fft.rfft(rg))[1:-1] ** 2) / NPTS**2 + (np.abs(np.fft.rfft(rg))[-1] / NPTS) ** 2
    ANA[name]["parseval_rms"] = float(np.sqrt(p_all))
    print(f"fit done {name}: gate {2*a1g*1e3:.5f} mVpp")

# closed form for every stair run and the measured-H version
C_DAC_TAU = {}
for name, kind, n, bits, amp in RUNS:
    if kind == "rc":
        txt = (ROOT / "sim-runs" / name / f"{name}.cir").read_text(encoding="utf-8")
        rd = parse_val(re.search(r"^R_DAC\s+\S+\s+\S+\s+(\S+)", txt, flags=re.M).group(1))
        cd = parse_val(re.search(r"^C_DAC\s+\S+\s+\S+\s+(\S+)", txt, flags=re.M).group(1))
        C_DAC_TAU[name] = (rd, cd)
        assert abs(rd - 1e3) < 1e-6
CL = {}
for name, kind, n, bits, amp in RUNS:
    if kind == "sin":
        continue
    if kind == "stair":
        ideal = closed(n, bits, amp, H_ideal_on, lambda f: np.ones_like(f))
        meas = closed(n, bits, amp, Hm_on, lambda f: np.ones_like(f))
    elif kind == "rc":
        rd, cd = C_DAC_TAU[name]
        ideal = closed(n, bits, amp, lambda f: h_mfb(f) * ed_rc(f, rd, cd), lambda f: ed_rc(f, rd, cd))
        meas = closed(n, bits, amp, lambda f: Hm_on(f) * ed_rc(f, rd, cd), lambda f: ed_rc(f, rd, cd))
        rc_only = closed(n, bits, amp, lambda f: h_mfb(f) / (1 + s_of(f) * rd * cd), lambda f: 1 / (1 + s_of(f) * rd * cd))
        CL[name + "_rconly"] = rc_only
    else:  # off
        ideal = closed(n, bits, amp, H_ideal_off, lambda f: ed_rc(f, 15e3, 0.0))
        meas = closed(n, bits, amp, Hm_off, Ed_off_m)
    CL[name] = ideal
    CL[name + "_meas"] = meas
    CL[name + "_stair"] = closed(n, bits, amp, H_ideal_on, lambda f: np.ones_like(f))  # buffer on, ideal
    CL[name + "_stair_meas"] = closed(n, bits, amp, Hm_on, lambda f: np.ones_like(f))
    # the ideal closed form for N = 128 with the staircase only (buffer on) for the P44a comparison
for n_ in (32, 64, 128, 256):
    CL[f"N{n_}"] = closed(n_, 12, 0.3, H_ideal_on, lambda f: np.ones_like(f))
    CL[f"N{n_}_meas"] = closed(n_, 12, 0.3, Hm_on, lambda f: np.ones_like(f))

# ---------------------------------------------------------------- reference floor
R_REF = ANA["P44_ref"]
print("\n== Floor: P44_ref (ideal SIN, same window and grid)")
print(f"gate fundamental {R_REF['mvpp']:.4f} mVpp, phase {R_REF['ph']:+.4f} deg; EXC_DAC fundamental "
      f"{2*R_REF['a1e']*1e3:.4f} mVpp")
print(f"gate THD (h2 to h20) {100*R_REF['thd']:.5f} %, THD+N {100*R_REF['thdn']:.5f} %, residual "
      f"{R_REF['resid']:.4f} uV rms")
print("gate harmonics h2..h7 (uV pk): " + ", ".join(f"{R_REF['harm'][k]*1e6:.4f}" for k in range(2, 8)))
print(f"EXC_DAC THD (h2 to h20) {100*np.sqrt(sum(R_REF['E']['amp'][k]['pk']**2 for k in range(2, NH+1)))/R_REF['a1e']:.5f} %")
print(f"settling (ref): gate fundamental halves differ by {R_REF['settle_g']:+.5f} % and {R_REF['settle_gph']:+.5f} deg")

# ---------------------------------------------------------------- P44a table
print("\n== P44a: staircase runs, fitted over the window (buffer on, measured MFB)")
hdr = ("run", "mVpp", "ph gate", "THD %", "THD+N %", "resid uV", "EXC img dBc", "gate img dBc", "settle %")
print(" | ".join(f"{h:>12}" for h in hdr))
for name, kind, n, bits, amp in RUNS:
    if kind != "stair":
        continue
    A = ANA[name]
    print(f"{name:>12} | {A['mvpp']:12.4f} | {A['ph']:12.4f} | {100*A['thd']:12.5f} | {100*A['thdn']:12.5f} | "
          f"{A['resid']:12.4f} | {A['img_e'][n-1]:12.3f} | {A['img_g'][n-1]:12.3f} | {A['settle_g']:12.5f}")

print("\nP44a fitted harmonics of GATE, h2..h7 (uV pk):")
for name, kind, n, bits, amp in RUNS:
    if kind == "stair" or kind in ("rc", "off"):
        A = ANA[name]
        print(f"  {name:12s} " + " ".join(f"{A['harm'][k]*1e6:9.4f}" for k in range(2, 8)))

print("\nP44a images of GATE and EXC_DAC (dBc), all lines (N-1, N+1, 2N-1, 2N+1):")
for name, kind, n, bits, amp in RUNS:
    if kind in ("stair", "rc", "off") and n:
        A = ANA[name]
        print(f"  {name:12s} GATE " + " ".join(f"{A['img_g'][k]:9.3f}" for k in sorted(A['img_g']))
              + " | EXC " + " ".join(f"{A['img_e'][k]:9.3f}" for k in sorted(A['img_e'])))

print("\nClosed form (ideal MFB, model with 100 ns edges) against the table of the entry:")
for name in ENTRY:
    c = CL[name]
    e = ENTRY[name]
    print(f"  {name:10s} mVpp {c['gate_mvpp']:9.4f} (entry {e['mvpp']:9.4f}) | EXC img {c['img_exc']:8.3f} "
          f"(entry {e['dac']:8.3f}) | gate img {c['img_gate']:8.3f} (entry {e['img']:8.3f}) | THD {100*c['thd']:.4f} "
          f"(entry {e['thd']}) | THD+N {100*c['thdn']:.4f} (entry {e['thdn']}) | resid {c['resid_uv']:.3f} "
          f"(entry {e['resid']})")
print("Closed form with the measured MFB (P44c_ac) for the same runs, and the fit:")
for name in ENTRY:
    cm = CL[name + "_meas"]
    A = ANA[name]
    print(f"  {name:10s} gate img closed meas {cm['img_gate']:8.3f} dBc, fit {A['img_g'][A['n'] - 1]:8.3f} dBc | "
          f"THD closed meas {100*cm['thd']:.4f} %, fit {100*A['thd']:.4f} % | resid closed meas {cm['resid_uv']:.3f} uV, fit {A['resid']:.3f} uV")

# ---------------------------------------------------------------- P44b
print("\n== P44b: realistic DAC (RC and buffer off) against the N = 128 reference")
REF = ANA["P44a_N128"]
for name in ("P44b_tau05", "P44b_tau1", "P44b_off"):
    A = ANA[name]
    ci = CL[name]
    cm = CL[name + "_meas"]
    cr = CL.get(name + "_rconly")
    print(f"{name}: gate {A['mvpp']:.5f} mVpp, closed {ci['gate_mvpp']:.5f} (meas H {cm['gate_mvpp']:.5f}), "
          f"diff {100*(A['mvpp']/ci['gate_mvpp']-1):+.4f} %")
    print(f"   EXC_DAC fund {2*A['a1e']*1e3:.5f} mVpp, closed {ci['exc_mvpp']:.5f}")
    dph_meas = A["ph"] - REF["ph"]
    dph_cl = ci["gate_ph"] - CL["P44a_N128"]["gate_ph"]
    print(f"   gate phase shift vs N128 measured {dph_meas:+.5f} deg, closed {dph_cl:+.5f} deg, "
          f"diff {dph_meas-dph_cl:+.5f} deg; RC only {(cr['gate_ph']-CL['P44a_N128']['gate_ph']) if cr else float('nan'):+.5f} deg")
    img_m = A["img_g"][127] - REF["img_g"][127]
    img_c = ci["img_gate"] - CL["P44a_N128"]["img_gate"]
    img_rc = (cr["img_gate"] - CL["P44a_N128"]["img_gate"]) if cr else float("nan")
    print(f"   gate image at 127 f0 change vs N128: measured {img_m:+.4f} dB, closed {img_c:+.4f} dB, "
          f"RC only {img_rc:+.4f} dB, diff {img_m-img_c:+.4f} dB")
    print(f"   EXC_DAC image at 127 f0 (dBc) {A['img_e'][127]:.4f}, closed {ci['img_exc']:.4f}; "
          f"EXC image change vs N128 {A['img_e'][127]-REF['img_e'][127]:+.4f} dB")
    print(f"   gate THD {100*A['thd']:.5f} %, closed {100*ci['thd']:.5f} %; harmonics h2..h7 closed/fit (uV): "
          + " ".join(f"{ci['h_uv'][i]:.3f}/{A['harm'][i+2]*1e6:.3f}" for i in range(6)))
    print(f"   settling halves: gate {A['settle_g']:+.5f} %, phase {A['settle_gph']:+.5f} deg")
print(f"buffer off: gate closed (R6 = 135 kOhm) {CL['P44b_off']['gate_mvpp']:.5f} mVpp, fit "
      f"{ANA['P44b_off']['mvpp']:.5f} mVpp, diff {100*(ANA['P44b_off']['mvpp']/CL['P44b_off']['gate_mvpp']-1):+.4f} %")
print(f"buffer off gate fund phase: closed {CL['P44b_off']['gate_ph']:+.5f} deg, fit {ANA['P44b_off']['ph']:+.5f} deg")

# ---------------------------------------------------------------- closed form against fit at N = 128
print("\n== N = 128: closed form against the fit (gate harmonics, uV pk)")
print(f"{'k':>3} {'closed ideal':>13} {'closed meas H':>14} {'fit PSpice':>11} {'fit - ideal':>12} "
      f"{'fit - meas':>11} {'floor (ref)':>12}")
for i, k in enumerate(range(2, 8)):
    ci = CL["P44a_N128"]["h_uv"][i]
    cm = CL["P44a_N128_meas"]["h_uv"][i]
    fv = ANA["P44a_N128"]["harm"][k] * 1e6
    fl = R_REF["harm"][k] * 1e6
    print(f"{k:3d} {ci:13.4f} {cm:14.4f} {fv:11.4f} {fv-ci:+12.4f} {fv-cm:+11.4f} {fl:12.4f}")
print("EXC_DAC harmonics h2..h7 (uV pk), closed (exact codes) against fit:")
for k in range(2, 8):
    ce = abs(CL["P44a_N128"]["ge"][k]) * 1e6
    print(f"  h{k}: closed {ce:.4f}, fit {ANA['P44a_N128']['E']['amp'][k]['pk']*1e6:.4f} uV")
print(f"residual N128 measured {ANA['P44a_N128']['resid']:.4f} uV rms, closed ideal {CL['P44a_N128']['resid_uv']:.4f}, "
      f"closed meas {CL['P44a_N128_meas']['resid_uv']:.4f}")
print("Parseval check (time-domain rms against the FFT band, uV rms):",
      ", ".join(f"{k}: {1e6*ANA[k]['parseval_rms']:.4f}/{ANA[k]['resid']:.4f}" for k in ("P44a_N128",)))

# ---------------------------------------------------------------- edge check and settling summary
print("\n== Edge check (solver points within 5 ns of each staircase edge) and solver step:")
for name, kind, n, bits, amp in RUNS:
    if kind != "sin":
        frac, med = ANA[name]["edge"]
        print(f"  {name:12s} edges with a point within 5 ns: {100*frac:.2f} %, median saved step {med*1e9:.1f} ns")
print("\n== Settling (first 10 periods against second 10 periods of the window):")
for name, kind, n, bits, amp in RUNS:
    A = ANA[name]
    print(f"  {name:12s} gate {A['settle_g']:+.6f} %, phase {A['settle_gph']:+.6f} deg; EXC {A['settle_e']:+.6f} %")

# ---------------------------------------------------------------- Monte Carlo
MODELS = ("random +-1 LSB", "bow 4 LSB", "S-curve 4 LSB", "random + bow + S")


def run_mc(Hfun, boards):
    rng = np.random.default_rng(44)  # same seed and loop order as P-44_expected.py
    res = {}
    for amp in (0.3, 1.2):
        c, lsb = codes(128, 12, amp)
        for name in MODELS:
            t = []
            for _ in range(boards):
                err = np.zeros(4096)
                if "random" in name:
                    err += rng.uniform(-1, 1, 4096)
                uu = np.linspace(-1, 1, 4096)
                if "bow" in name or "+ S" in name:
                    err += 4 * (1 - uu**2) * rng.choice((-1, 1)) * (rng.uniform(0, 1) if "+" in name else 1)
                if "S-curve" in name or "+ S" in name:
                    err += 4 * 2.598 * uu * (1 - uu**2) * rng.choice((-1, 1)) * (rng.uniform(0, 1) if "+" in name else 1)
                v = (c + err[c.astype(int)]) * lsb
                t.append(thd_mc(v, 128, Hfun))
                if "random" not in name and "+" not in name:
                    break
            res[(amp, name)] = np.array(t) * 100
    return res


print(f"\n== Code-error Monte Carlo, N = 128, 12 bit, {args.mc} boards (same model as P-44_expected.py)")
mc_ideal = run_mc(lambda f: h_mfb(f), args.mc)
mc_meas = run_mc(Hm_on, args.mc)
print(f"{'amp V pk':>8} {'model':18s} {'ideal med %':>12} {'ideal p95 %':>12} {'meas med %':>11} {'meas p95 %':>11} {'meas max %':>11}")
for amp in (0.3, 1.2):
    for name in MODELS:
        a = mc_ideal[(amp, name)]
        b = mc_meas[(amp, name)]
        print(f"{amp:8.2f} {name:18s} {np.median(a):12.5f} {np.percentile(a,95):12.5f} {np.median(b):11.5f} "
              f"{np.percentile(b,95):11.5f} {b.max():11.5f}")

# ---------------------------------------------------------------- checks added after the judge review
ONES = lambda f: np.ones_like(f)  # noqa: E731

print("\n== Window check: FFT over 20 exact periods (25600 points per period) against the LS fit")
P20, SPP = 20, 25600
MM = P20 * SPP
TG20 = T0 + np.arange(MM) * (P20 * DUR / MM)
for name, kind, n, bits, amp in RUNS:
    sec = load_csd(name)
    tt = np.asarray(sec.x, float)
    res = {}
    for node, key in (("V(GATE)", "G"), ("V(EXC_DAC)", "E")):
        y = np.interp(TG20, tt, np.asarray(sec[node], float))
        X = np.fft.rfft(y) * 2 / MM
        fr = ANA[name][key]
        dif = {k: abs(abs(X[k * P20]) - fr["amp"][k]["pk"]) * 1e6 for k in fr["ks"]}
        kmax = max(dif, key=dif.get)
        res[key] = (dif[kmax], kmax, dif[3] if 3 in dif else 0.0, dif[5] if 5 in dif else 0.0, dif[7] if 7 in dif else 0.0)
    print(f"  {name:12s} max |FFT - fit| over the fitted lines: GATE {res['G'][0]:.5f} uV (line {res['G'][1]}), "
          f"EXC_DAC {res['E'][0]:.5f} uV (line {res['E'][1]}), EXC h3, h5, h7 differences "
          f"{res['E'][2]:.5f}, {res['E'][3]:.5f}, {res['E'][4]:.5f} uV")

print("\n== PWL rounding check: levels in circuits/afe_eval_P44_N128.cir against round(code x LSB, 6)")
_txt = (ROOT / "circuits/afe_eval_P44_N128.cir").read_text(encoding="utf-8")
_pwl = np.array([float(v) for v in re.findall(r"^\+ \S+ (\S+)$", _txt, flags=re.M)])
_c128, _lsb128 = codes(128, 12, 0.3)
_file_levels = _pwl[::2][:128]  # two PWL points per sample, the first of each pair holds the level
print(f"  max |file level - round(code x LSB, 6)| over one period: "
      f"{np.max(np.abs(_file_levels - np.round(_c128 * _lsb128, 6)))*1e6:.6f} uV")
_ex = closed(128, 12, 0.3, H_ideal_on, ONES)
_rd = closed(128, 12, 0.3, H_ideal_on, ONES, rnd=True)
print("  EXC_DAC lines (uV pk): k, exact closed form, closed form with 1 uV levels, fit of PSpice")
for k in range(2, 8):
    print(f"   h{k}: {abs(_ex['ge'][k])*1e6:9.4f} {abs(_rd['ge'][k])*1e6:9.4f} "
          f"{ANA['P44a_N128']['E']['amp'][k]['pk']*1e6:9.4f}")
print("  gate lines (uV pk) with ideal H: rounded minus exact, h2..h7: "
      + " ".join(f"{abs(_rd['g'][k]-_ex['g'][k])*1e6:.5f}" for k in range(2, 8)))
print("  gate fit minus rounded closed form, h2..h7 (uV): "
      + " ".join(f"{ANA['P44a_N128']['harm'][k]*1e6 - abs(_rd['g'][k])*1e6:+.4f}" for k in range(2, 8)))

print("\n== Floor scaling with amplitude and the combined THD")
_h2_03 = ANA["P44_ref"]["harm"][2]
_h2_12 = ANA["P44a_max"]["harm"][2]
print(f"  h2 floor: {_h2_03*1e6:.4f} uV at 0.3 V, {_h2_12*1e6:.4f} uV at 1.2 V; "
      f"relative to h1: {100*_h2_03/ANA['P44_ref']['a1g']:.5f} % and {100*_h2_12/ANA['P44a_max']['a1g']:.5f} %")
_thd_ref = 100 * ANA["P44_ref"]["thd"]
_thd_cl_max = 100 * CL["P44a_max"]["thd"]
print(f"  floor THD (P44_ref) {_thd_ref:.5f} %, closed ideal THD at 1.2 V {_thd_cl_max:.5f} %, "
      f"root sum square {np.sqrt(_thd_cl_max**2 + _thd_ref**2):.5f} % against measured "
      f"{100*ANA['P44a_max']['thd']:.5f} %")

print("\n== GATE/GOUT check (P44c_ac) and the output stage model")
_G = np.asarray(ac_on["V(GATE)"])
_O = np.asarray(ac_on["V(GOUT)"])
_pole = np.abs(_G / _O * (1 + s_of(fac) * R59 * CGATE))
print(f"  |GATE/GOUT x (1 + s R59 Cg)|: max deviation from 1 over 10 Hz to 1 MHz "
      f"{np.max(np.abs(20*np.log10(_pole))):.5f} dB")
SEL = [int(np.argmin(np.abs(fac - x))) for x in (518, 20e3, 50e3, 65786, 100e3, 200e3, 1e6)]
print("  grid frequencies used (Hz): " + " ".join(f"{fac[i]:.1f}" for i in SEL))
_gi = 20 * np.log10(np.abs(_O / h_out(fac)))
print("  GOUT measured minus ideal op amp (dB): " + " ".join(f"{fac[i]/1e3:.2f}k:{_gi[i]:+.3f}" for i in SEL))
print("  GOUT measured (dB): " + " ".join(f"{fac[i]/1e3:.2f}k:{20*np.log10(abs(_O[i])):.3f}" for i in SEL))


def gout_model(gbw, ro):
    """GOUT of the MFB with a single-pole op amp (GBW) and output impedance ro, load R59 + gate capacitor."""
    out = np.zeros(len(fac), complex)
    for i, ss in enumerate(s_of(fac)):
        a = gbw * 2 * np.pi / ss  # open-loop gain of a single pole: A(s) = 2 pi GBW / s
        zl = R59 + 1 / (ss * CGATE)
        Y = np.zeros((3, 3), complex)
        b = np.zeros(3, complex)
        Y[0] = [1 / R6 + ss * C7 + 1 / R5 + 1 / R7, -1 / R7, -1 / R5]
        b[0] = 1 / R6
        Y[1] = [-1 / R7, 1 / R7 + ss * C6, -ss * C6]
        Y[2] = [-1 / R5, -ss * C6 + a / ro, 1 / R5 + ss * C6 + 1 / zl + 1 / ro]
        out[i] = np.linalg.solve(Y, b)[2]
    return out


_ro0 = 1e-3  # zero output impedance
_m0 = gout_model(1.1e6, _ro0)
print("  model, GBW 1.1 MHz, Ro = 0 (dB): " + " ".join(f"{fac[i]/1e3:.2f}k:{20*np.log10(abs(_m0[i])):.3f}" for i in SEL))
_m500 = gout_model(1.1e6, 500.0)
print("  model, GBW 1.1 MHz, Ro = 500 Ohm (dB): " + " ".join(f"{fac[i]/1e3:.2f}k:{20*np.log10(abs(_m500[i])):.3f}" for i in SEL))
_band = (fac >= 20e3) & (fac <= 1e6)
_meas_db = 20 * np.log10(np.abs(_O))
_best = None
for gbw in (0.2e6, 0.3e6, 0.5e6, 0.8e6, 1.1e6, 1.6e6, 2.5e6):
    for ro in range(0, 1001, 25):
        m = gout_model(gbw, max(ro, _ro0))
        err = np.sqrt(np.mean((20 * np.log10(np.abs(m[_band])) - _meas_db[_band]) ** 2))
        if _best is None or err < _best[0]:
            _best = (err, gbw, ro, m)
print(f"  best fit over GBW (0.2 to 2.5 MHz) and Ro (0 to 1000 Ohm), 20 kHz to 1 MHz: rms error {_best[0]:.3f} dB, "
      f"GBW {_best[1]/1e6:.2f} MHz, Ro {_best[2]} Ohm")
print("  best-fit model (dB): " + " ".join(f"{fac[i]/1e3:.2f}k:{20*np.log10(abs(_best[3][i])):.3f}" for i in SEL))
print("  measured (dB):       " + " ".join(f"{fac[i]/1e3:.2f}k:{20*np.log10(abs(_O[i])):.3f}" for i in SEL))

# ---------------------------------------------------------------- window and aliasing checks (judge, round 3)
def _lsfit_exc(run, ks_list, tg):
    sec = load_csd(run)
    tt = np.asarray(sec.x, float)
    ye = np.asarray(sec["V(EXC_DAC)"], float)
    y = np.interp(tg, tt, ye)
    cols = [np.ones_like(tg)]
    for k in ks_list:
        w = 2 * np.pi * k * F0 * tg
        cols += [np.sin(w), np.cos(w)]
    c = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)[0]
    amp = {k: float(np.hypot(c[1 + 2 * i], c[2 + 2 * i])) for i, k in enumerate(ks_list)}
    return amp, tt, ye


def _fft_exc(tt, ye, spp, ks_list):
    M = 20 * spp
    tg = T0 + np.arange(M) * (20 * DUR / M)
    X = np.fft.rfft(np.interp(tg, tt, ye)) / M * 2
    return {k: float(abs(X[20 * k])) for k in ks_list}


print("")
print("== Window and aliasing check, EXC_DAC lines (uV pk): LS on the short window, LS on an exact 20-period grid, FFT at 25600 and 51200 points per period")
for _run, _n, _show in (("P44a_max", 128, (3, 5, 7, 255, 257)), ("P44a_N32", 32, (3, 5, 7, 31, 33, 63, 65))):
    _ks = ks_for(_n)
    _short, _tt, _ye = _lsfit_exc(_run, _ks, T0 + 1e-7 * np.arange(NPTS))
    _exact, _, _ = _lsfit_exc(_run, _ks, T0 + np.arange(NPTS) * (20 * DUR / NPTS))
    _f1 = _fft_exc(_tt, _ye, 25600, _ks)
    _f2 = _fft_exc(_tt, _ye, 51200, _ks)
    for _k in _show:
        print(f"  {_run:9s} line {_k:3d}: LS short {_short[_k]*1e6:.4f}  LS exact {_exact[_k]*1e6:.4f}  "
              f"FFT25600 {_f1[_k]*1e6:.4f}  FFT51200 {_f2[_k]*1e6:.4f}")
    print(f"  {_run:9s} max |LS exact - LS short| over the fitted lines: "
          f"{max(abs(_exact[k] - _short[k]) for k in _ks)*1e6:.4f} uV")

print("")
print("== Floor at 1.2 V: vector bounds (P44_ref floor h2 to h7 times 4, floor h8 to h20 taken as 0)")
_cl12 = closed(128, 12, 1.2, H_ideal_on, ONES, rnd=True)
_gh = np.abs(_cl12["g"][2:NH + 1])
_fl = np.zeros(NH - 1)
for _k in range(2, 8):
    _fl[_k - 2] = 4 * ANA["P44_ref"]["harm"][_k]
_a1 = np.abs(_cl12["g"][1])
print("  closed h2 to h7 at 1.2 V (uV pk): " + " ".join(f"{v*1e6:.4f}" for v in _gh[:6]))
print("  floor h2 to h7 times 4 (uV pk):   " + " ".join(f"{v*1e6:.4f}" for v in _fl[:6]))
_thd_cl12 = 100 * np.sqrt(np.sum(_gh**2)) / _a1
_thd_in = 100 * np.sqrt(np.sum((_gh + _fl)**2)) / _a1
_thd_anti = 100 * np.sqrt(np.sum((_gh - _fl)**2)) / _a1
_thd_meas = 100 * ANA["P44a_max"]["thd"]
print(f"  closed THD (levels rounded to 1 uV) {_thd_cl12:.5f} %")
print(f"  bound anti-phase {_thd_anti:.5f} %, bound in phase {_thd_in:.5f} %, measured {_thd_meas:.5f} %")
print(f"  measured inside the bound: {_thd_anti <= _thd_meas <= _thd_in}")

# ---------------------------------------------------------------- figures
one = TG < T0 + DUR  # one period, starting at 10 T
t_ms = (TG[one] - T0) * 1e3
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, n in zip(axs, (32, 128)):
    A = ANA[f"P44a_N{n}"]
    E, G = A["E"], A["G"]
    e_scaled = (A["y"]["V(EXC_DAC)"] - E["dc"]) * (-1 / 120) * 1e3
    g_dc = (A["y"]["V(GATE)"] - G["dc"]) * 1e3
    fitted = (G["coef"][1] * G["A"][:, 1] + G["coef"][2] * G["A"][:, 2]) * 1e3
    ax.plot(t_ms, e_scaled[one], drawstyle="steps-post", lw=0.9, label="EXC_DAC - DC, times -1/120")
    ax.plot(t_ms, g_dc[one], lw=1.2, label="GATE - DC")
    ax.plot(t_ms, fitted[one], "k--", lw=0.9, label="fitted fundamental")
    ax.set_title(f"N = {n}, 12 bit, 0.3 V pk")
    ax.set_xlabel("time from 10 T (ms)")
    ax.grid(alpha=0.3)
axs[0].set_ylabel("voltage (mV)")
axs[1].legend(fontsize=8, loc="upper right")
fig.tight_layout()
fig.savefig(FIG / "P-44_period_overlay.png", dpi=130)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.2))
for name, lab in (("P44a_N32", "N = 32"), ("P44a_N128", "N = 128"), ("P44a_8b", "N = 128, 8 bit")):
    r = ANA[name]["rg"][one] * 1e6
    ax.plot(t_ms, r, lw=0.9, label=f"{lab}: {ANA[name]['resid']:.2f} uV rms")
ax.set_xlabel("time from 10 T (ms)")
ax.set_ylabel("residual (uV), GATE minus DC and fundamental")
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "P-44_residual.png", dpi=130)
plt.close(fig)

fig, axs = plt.subplots(2, 2, figsize=(11, 6.5), sharex=True)
kmax = int(300e3 / F0)
kk = np.arange(1, kmax + 1)
bins = np.rint(kk * F0 * NPTS * DT).astype(int)
for col, n in enumerate((32, 128)):
    A = ANA[f"P44a_N{n}"]
    for row, key in enumerate(("E", "G")):
        y = A["y"]["V(EXC_DAC)"] if key == "E" else A["y"]["V(GATE)"]
        X = np.fft.rfft(y - np.mean(y)) * 2 / NPTS
        a = np.abs(X[bins])
        dbc = 20 * np.log10(np.maximum(a, 1e-12) / a[0])
        ax = axs[row, col]
        ax.vlines(kk * F0 / 1e3, -200, dbc, lw=1.0)
        ax.set_ylim(-160, 5)
        ax.set_xlim(0, 300)
        ax.grid(alpha=0.3)
        ax.set_title(f"{'EXC_DAC (relative to its fundamental)' if key == 'E' else 'GATE (relative to its fundamental)'}, N = {n}",
                     fontsize=9)
        if row == 1:
            ax.set_xlabel("frequency (kHz)")
        if col == 0:
            ax.set_ylabel("level (dBc)")
fig.tight_layout()
fig.savefig(FIG / "P-44_spectra.png", dpi=130)
plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
Ns = np.array([32, 64, 128, 256])
thd_m = np.array([100 * ANA[f"P44a_N{n}"]["thd"] for n in Ns])
thd_c = np.array([100 * CL[f"N{n}"]["thd"] for n in Ns])
thd_cm = np.array([100 * CL[f"N{n}_meas"]["thd"] for n in Ns])
img_m = np.array([ANA[f"P44a_N{n}"]["img_g"][n - 1] for n in Ns])
img_c = np.array([CL[f"N{n}"]["img_gate"] for n in Ns])
img_cm = np.array([CL[f"N{n}_meas"]["img_gate"] for n in Ns])
axs[0].loglog(Ns, thd_m, "o-", label="PSpice (fit)")
axs[0].loglog(Ns, thd_c, "s--", label="closed form, ideal MFB")
axs[0].loglog(Ns, thd_cm, "^:", label="closed form, measured MFB")
axs[0].axhline(100 * R_REF["thd"], color="grey", lw=0.8, label="ideal SIN floor (P44_ref)")
axs[0].axhline(0.3, color="red", lw=0.8, ls="--", label="gate THD limit 0.3 %")
axs[0].set_xlabel("samples per period N")
axs[0].set_ylabel("gate THD, h2 to h20 (%)")
axs[0].legend(fontsize=7)
axs[0].grid(alpha=0.3, which="both")
axs[1].semilogx(Ns, img_m, "o-", label="PSpice (fit)")
axs[1].semilogx(Ns, img_c, "s--", label="closed form, ideal MFB")
axs[1].semilogx(Ns, img_cm, "^:", label="closed form, measured MFB")
axs[1].axhline(-80, color="red", lw=0.8, ls="--", label="image limit -80 dBc")
axs[1].set_xlabel("samples per period N")
axs[1].set_ylabel("gate image at (N-1) f0 (dBc)")
axs[1].legend(fontsize=7)
axs[1].grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig(FIG / "P-44_thd_image_vs_N.png", dpi=130)
plt.close(fig)
print("\nFigures written to", FIG)
