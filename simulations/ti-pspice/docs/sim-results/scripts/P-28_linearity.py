"""P-28a to P-28d: demodulator linearity, zero-input offset, edge errors and transition region (LIA-AFE-Eval).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-28_linearity.py
Reads the .csd files of the runs P28a_lin (vpa = vna = 4.6 V), P28b_lin5v (5.0 V), P28c_zero (ain = 0,
vos_in stepped) and P28d_quad (p = 90 deg). Circuits: circuits/afe_demod.cir, afe_demod_P28b.cir,
afe_demod_P28c.cir, afe_demod_P28d.cir. No new simulation is run by this script.

Ideal values: X_OUT = (2/pi) ain cos(p), Y_OUT = -(2/pi) ain sin(p).
Means are time-weighted (trapezoid rule) over 20 whole periods of f0 from 60 ms. The settling reference is the
20 periods before 60 ms. The half-window check compares the second 10 periods with the first 10 periods.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

F0 = 518.0
OMEGA = 2 * np.pi * F0
T0 = 1.0 / F0
N_PER = 20
TW = 0.060
WIN = N_PER * T0            # 38.610 ms
HALF = 10 * T0              # 19.305 ms
PREV = TW - WIN             # 21.39 ms
K = 2.0 / np.pi
TAU = 200e3 * 15e-9         # R14 x C13 of afe_demod.cir = 3 ms
REG_LO_OFF, REG_HI_OFF = 3.0, 1.5
SR_SYM = 7.5e6              # V/s, datasheet rising slew rate at +/-18 V (not read at +/-5 V)
DELAY = (4e-9 + 30e-9 * np.log(1 / 0.3))   # SPDT_PREC break-before-make: about 40 ns (estimate)


def tmean(t, y, t0, t1):
    m = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[m], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[m], [np.interp(t1, t, y)]))
    return np.trapezoid(yy, tt) / (t1 - t0)


def wmax(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return float(np.max(y[m])), float(np.min(y[m]))


def load(name):
    out = []
    for s in read_csdf(ROOT / "sim-runs" / name / f"{name}.csd"):
        t = np.real(np.asarray(s.x)).astype(float)
        X = np.asarray(s["V(X_OUT)"], float)
        Y = np.asarray(s["V(Y_OUT)"], float)
        D1 = np.asarray(s["V(D1)"], float)
        XD = np.asarray(s["V(X_DEM)"], float)
        win = (t >= TW) & (t <= TW + WIN)
        out.append(dict(
            step=s.step_value,
            X=tmean(t, X, TW, TW + WIN) * 1e3,                       # mV
            Xprev=tmean(t, X, PREV, TW) * 1e3,                       # mV
            Y=tmean(t, Y, TW, TW + WIN) * 1e3,                       # mV
            Yprev=tmean(t, Y, PREV, TW) * 1e3,                       # mV
            Xh1=tmean(t, X, TW, TW + HALF) * 1e3,
            Xh2=tmean(t, X, TW + HALF, TW + WIN) * 1e3,
            Yh1=tmean(t, Y, TW, TW + HALF) * 1e3,
            Yh2=tmean(t, Y, TW + HALF, TW + WIN) * 1e3,
            D1=wmax(t, D1, TW, TW + WIN),
            XDEM=wmax(t, XD, TW, TW + WIN),
            dtmax=float(np.max(np.diff(t[win]))) * 1e6,              # us
            t=t, X_arr=X, D1_arr=D1, XD_arr=XD,
        ))
    return out


def by_step(runs):
    return sorted(runs, key=lambda d: d["step"])


def region(vpa):
    return vpa - REG_LO_OFF, vpa - REG_HI_OFF


def where(v, lo, hi):
    if v < lo - 1e-9:
        return "below"
    if v <= hi + 1e-9:
        return "inside"
    return "above"


def main():
    a = by_step(load("P28a_lin"))
    b = by_step(load("P28b_lin5v"))
    c = by_step(load("P28c_zero"))
    dq = by_step(load("P28d_quad"))

    print(f"Window: {TW*1e3:.2f} ms to {(TW+WIN)*1e3:.2f} ms ({N_PER} periods, {WIN*1e3:.3f} ms); "
          f"reference {PREV*1e3:.2f} ms to {TW*1e3:.2f} ms; halves of {HALF*1e3:.3f} ms")
    print(f"max sample step inside the window: P28a {max(d['dtmax'] for d in a):.3f} us, "
          f"P28b {max(d['dtmax'] for d in b):.3f} us, P28c {max(d['dtmax'] for d in c):.3f} us, "
          f"P28d {max(d['dtmax'] for d in dq):.3f} us")

    # --- zero-signal offsets ---
    c0 = [d for d in c if abs(d["step"]) < 1e-12][0]
    X0, Y0 = c0["X"], c0["Y"]
    print(f"\n== P28c zero signal, vos_in = 0: X0 = {X0:.5f} mV, Y0 = {Y0:.5f} mV")
    print("vos(V)   X(mV)     Y(mV)     Xsettle(uV)  Ysettle(uV)  pred Xsettle  pred Ysettle  D1 mean(V)")
    u0 = PREV / TAU
    defic = TAU * ((u0 + 2) * np.exp(-u0) - ((TW / TAU) + 2) * np.exp(-TW / TAU)) / WIN
    imp = (T0 / 4) / WIN * (1 + u0) * np.exp(-u0)
    for d in c:
        vos = d["step"]
        xs = (d["X"] - d["Xprev"]) * 1e3
        ys = (d["Y"] - d["Yprev"]) * 1e3
        px = vos * (defic - imp) * 1e6          # uV
        py = vos * defic * 1e6                  # uV
        print(f"{vos:+6.2f}  {d['X']:+9.5f} {d['Y']:+9.5f}  {xs:+10.2f}  {ys:+10.2f}  {px:+10.2f}  {py:+10.2f}"
              f"   {d['D1'][0]:+.5f}")
    print(f"start-up deficit of the reference window (mean of the 3 ms pair) = {defic:.4e} of the final value")
    print(f"equivalent impulse term (T/4)/WIN (1+u0) exp(-u0) = {imp:.4e}")

    # --- P28a and P28b linearity and offset correction ---
    def xerr(runs):
        return np.array([d["step"] for d in runs]), np.array([d["X"] - K * d["step"] * 1e3 for d in runs])

    ain_a, e_a = xerr([d for d in a if d["step"] >= 0.1 - 1e-9])
    ain_b, e_b = xerr([d for d in b if d["step"] >= 0.1 - 1e-9])
    slope_a, icpt_a = np.polyfit(ain_a, e_a, 1)
    slope_b, icpt_b = np.polyfit(ain_b, e_b, 1)
    print(f"\n== Offset regression of the raw X error against ain (0.1 V to 3 V)")
    print(f"P28a: intercept {icpt_a:.6f} mV, slope {slope_a*1e3:+.4f} uV/V   (P28c X0 = {X0:.5f} mV)")
    print(f"P28b: intercept {icpt_b:.6f} mV, slope {slope_b*1e3:+.4f} uV/V   (no zero-signal run at 5.0 V)")

    for label, runs, off in (("P28a (4.6 V), offset from P28c", a, X0),
                             ("P28b (5.0 V), offset from regression intercept", b, icpt_b)):
        lo, hi = region(runs[0].get("vpa", 4.6)) if False else (None, None)
        print(f"\n== {label}")
        print("ain(V)  Xideal(mV)  Xmeas(mV)  raw err(%)  corrected err(%)  Y(mV)  Y corr(mV)  D1 max(V)  X_DEM max/min(V)")
        vpa = 4.6 if "P28a" in label else 5.0
        lo, hi = vpa - REG_LO_OFF, vpa - REG_HI_OFF
        corr_list = []
        for d in runs:
            ain = d["step"]
            xi = K * ain * 1e3
            raw = 100 * (d["X"] - xi) / xi
            cor = 100 * (d["X"] - off - xi) / xi
            ycorr = d["Y"] - Y0
            corr_list.append((ain, cor))
            print(f"{ain:6.3f}  {xi:10.4f}  {d['X']:9.4f}  {raw:+9.4f}  {cor:+12.5f}  {d['Y']:+7.4f}  "
                  f"{ycorr:+8.4f}  {d['D1'][0]:9.4f}  {d['XDEM'][0]:+.4f}/{d['XDEM'][1]:+.4f}  "
                  f"{where(d['D1'][0], lo, hi)}")
        first = [ain for ain, cor in corr_list if abs(cor) > 1.0]
        print(f"first ain with |corrected gain error| > 1 %: {first[0] if first else 'none'}")

    print("\n== P28b at 10 mV with the regression intercept")
    d10 = [d for d in b if abs(d["step"] - 0.01) < 1e-9][0]
    print(f"P28b 10 mV: corrected error {100*(d10['X'] - icpt_b - K*0.01*1e3)/(K*0.01*1e3):+.5f} %")

    # --- settling halves ---
    print("\n== Half-window settling check (second 10 periods minus first 10 periods, uV)")
    print("ain(V)   X half diff   Y half diff   (P28a)")
    for d in a:
        print(f"{d['step']:6.3f}  {(d['Xh2']-d['Xh1'])*1e3:+10.3f}  {(d['Yh2']-d['Yh1'])*1e3:+10.3f}")
    print("== Full-window settling check against the reference (uV), and the analytic reference deficit")
    for d in a:
        if d["step"] in (1.0, 3.0):
            meas = (d["X"] - d["Xprev"]) * 1e3
            pred = K * d["step"] * defic * 1e3 * 1e3
            print(f"ain {d['step']} V: measured {meas:+.2f} uV, analytic {pred:+.2f} uV, "
                  f"excess {100*(meas-pred)/pred:+.2f} %")
    res60 = (1 + TW / TAU) * np.exp(-TW / TAU)
    print(f"analytic residual of the 60 ms window = {res60:.3e} of the final value "
          f"({res60*K*1*1e6:.4f} uV at 1 V)")

    # --- Y at p = 0 and X at p = 90: three-term edge model ---
    # magnitude of the offset-corrected Y error, MAG = -E (V); model
    #   MAG = 4 f0 delta A + 4 f0 A^2 / SR - c   (delta: break-before-make lag, SR: rising slew rate,
    #   c: amplitude-independent recovery term from the X_DEM overshoot after each edge)
    A = np.array([d["step"] for d in a if d["step"] >= 0.1 - 1e-9])
    E = np.array([d["Y"] - Y0 for d in a if d["step"] >= 0.1 - 1e-9])
    MAG = -E * 1e-3                                      # V
    DEL_FIX, SR_FIX, C_FIX = 38.1e-9, 8.00e6, 0.109e-3   # V/s, V (values quoted in the review)
    print("\n== Y at p = 0 (offset-corrected, P28a): three-term edge model")
    d_lin = MAG[:2] / (4 * F0 * A[:2])
    print(f"delta from the 0.1 V and 0.4 V points (linear part only): "
          f"{d_lin[0]*1e9:.2f} ns and {d_lin[1]*1e9:.2f} ns")
    sel = A >= 1 - 1e-9
    Mx = np.vstack([A[sel], A[sel]**2, -np.ones(sel.sum())]).T
    (alpha, beta, cc), *_ = np.linalg.lstsq(Mx, MAG[sel], rcond=None)
    print(f"least squares over 1 V to 3 V: delta = {alpha/(4*F0)*1e9:.2f} ns, SR = {4*F0/beta*1e-6:.2f} V/us, "
          f"c = {cc*1e3:.4f} mV")
    print(f"fixed values used: delta = {DEL_FIX*1e9:.1f} ns, SR = {SR_FIX*1e-6:.2f} V/us, c = {C_FIX*1e3:.3f} mV")
    print("A(V)  Y corr meas(mV)  delta term(mV)  slew term(mV)  recovery(mV)  model MAG(mV)  "
          "resid, meas minus model (uV)")
    for ain, mag in zip(A, MAG):
        dl = 4 * F0 * DEL_FIX * ain
        sl = 4 * F0 * ain**2 / SR_FIX
        model = dl + sl - C_FIX
        print(f"{ain:5.3f}  {-mag*1e3:+12.4f}  {dl*1e3:+12.4f}  {sl*1e3:+12.4f}  {-C_FIX*1e3:+11.4f}  "
              f"{model*1e3:+12.4f}  {(mag-model)*1e6:+12.2f}")
    print("sign: a reference lag delta moves the output to (2/pi) A cos(p + omega delta), so the errors are"
          " negative at p = 0 (Y) and at p = 90 (X). The model is written for the magnitude.")
    print("The three terms act in sequence on each edge: X_DEM moves by less than 1 mV until D1 crosses"
          " 50 % (see the edge statistics), then it slews at the rising rate.")

    # --- P28d quadrature ---
    print("\n== P28d, p = 90 deg: X error (offset-corrected) and Y")
    for d in dq:
        ain = d["step"]
        xcor = d["X"] - X0
        bound = 0.2 / 100 * K * ain * 1e3
        yi = -K * ain * 1e3
        print(f"ain {ain} V: X {d['X']:+.5f} mV (corrected {xcor:+.5f} mV, {100*xcor/(K*ain*1e3):+.4f} % of R), "
              f"bound {bound:.4f} mV; Y {d['Y']:+.4f} mV vs {yi:+.4f} mV, diff {d['Y']-yi:+.4f} mV")
    # high-amplitude slew fit: E = b A^2 over 1.5 V to 3 V (the delay term is negligible there)
    hi = np.array([d["step"] for d in a if d["step"] >= 1.5 - 1e-9])
    Eh = np.array([d["Y"] - Y0 for d in a if d["step"] >= 1.5 - 1e-9])
    bh = np.sum(hi**2 * Eh) / np.sum(hi**4)
    print(f"\nslew-only fit over 1.5 V to 3 V: b = {bh:+.5f} mV/V^2, SR = 4 f0 / |b| = "
          f"{4*F0/abs(bh*1e-3)*1e-6:.2f} V/us")
    print("A(V)   slew-only fit (mV)  residual (mV)   delay-only (mV)  residual (mV)")
    for ain, meas in zip(A, E):
        sf = bh * ain**2
        dl = -K * OMEGA * DELAY * ain * 1e3     # mV
        print(f"{ain:5.3f}  {sf:+15.4f}  {meas-sf:+12.4f}  {dl:+15.4f}  {meas-dl:+12.4f}")

    # full-scale check at 1.98 V pk: the 2 V corrected error scaled with A^2 (slew-type term)
    fs = 1.98
    e2 = [d["Y"] - Y0 for d in a if abs(d["step"] - 2.0) < 1e-9][0]
    e_fs = e2 * (fs / 2.0) ** 2
    R_fs = K * fs * 1e3
    print(f"full scale 1.98 V pk: error {e_fs:+.4f} mV = {100*abs(e_fs)/R_fs:.4f} % of R = "
          f"{np.degrees(np.arctan(abs(e_fs)/R_fs)):.4f} deg quadrature leakage")
    mag3 = (4 * F0 * DEL_FIX * fs + 4 * F0 * fs**2 / SR_FIX - C_FIX) * 1e3
    print(f"full scale 1.98 V pk, three-term model: {-mag3:+.4f} mV = {100*mag3/R_fs:.4f} % of R = "
          f"{np.degrees(np.arctan(mag3/R_fs)):.4f} deg")

    # --- switch-edge charge check ---
    print("\n== Injected-charge check (estimate): dV = Q x f / C with Q = 0.4 pC, f = 0.3 of the edge, C = 12 pF")
    print(f"dV = {0.4e-12 * 0.3 / 12e-12 * 1e3:.2f} mV (compare with 9.96 mV excess on D1 at 0.4 V, 19.7 mV at 2 V)")

    # --- edge check ---
    print("\n== Edge check: peak times within the settled window (phase = fraction of a half period after the REF_X edge)")
    for name in ("P28a_lin", "P28d_quad"):
        for d in by_step(load(name)):
            if name == "P28a_lin" and abs(d["step"] - 2.0) > 1e-9:
                continue
            t = d["t"]
            m = (t >= TW) & (t <= TW + WIN)
            i1 = np.argmax(np.where(m, d["D1_arr"], -np.inf))
            ix = np.argmax(np.where(m, d["XD_arr"], -np.inf))
            print(f"  {name} ain {d['step']} V: D1 max {d['D1_arr'][i1]:.5f} V at phase {(t[i1]*F0)%0.5*2:.4f}; "
                  f"X_DEM max {d['XD_arr'][ix]:.5f} V at phase {(t[ix]*F0)%0.5*2:.4f}; "
                  f"X_DEM min {d['XDEM'][1]:+.5f} V")

    # --- P28d X and Y signs and the 0.2 % test already printed above ---
    print("\n== Summary of the one-line checks")
    print(f"regression intercepts: P28a {icpt_a:.5f} mV (P28c X0 {X0:.5f} mV), P28b {icpt_b:.5f} mV")


def _stat(name, vals, unit):
    if len(vals) == 0:
        print(f"  {name}: no edges")
        return
    v = np.asarray(vals)
    print(f"  {name}: n = {v.size}, mean {v.mean():.4g} {unit}, min {v.min():.4g} {unit}, max {v.max():.4g} {unit}, "
          f"std {v.std(ddof=0):.3g} {unit}")


def edge_stats():
    """Edge timing in P28d (p = 90 deg). REF_X edges at k T/2 inside the settled window.

    D1 mid-level crossing: first time D1 passes the mid level between its level 5 ns before and 150 ns
    after the edge. Overshoot: largest |D1 - post| between 45 ns and 150 ns after the edge.
    Break: largest |D1 - D1(edge + 5 ns)| between 5 ns and 35 ns after the edge.
    X_DEM slope: secant between the two samples that bracket the mid crossing (the adaptive step
    is too coarse for a +/-60 ns fit on the ramp).
    """
    print()
    print("== Edge statistics, P28d_quad (REF_X edges at k T/2 inside 60 ms to 98.61 ms)")
    T2 = T0 / 2
    for d in by_step(load("P28d_quad")):
        t = d["t"]
        D1 = d["D1_arr"]
        XD = d["XD_arr"]
        ain = d["step"]
        ks = range(int(np.ceil((TW + 0.0005) / T2)), int(np.floor((TW + WIN - 0.0005) / T2)) + 1)
        t50, tov, eov, brk, slopes, ovs, xb = [], [], [], [], [], [], []
        for k in ks:
            te = k * T2
            pre = np.interp(te - 5e-9, t, D1)
            post = np.interp(te + 150e-9, t, D1)
            m = (t >= te) & (t <= te + 150e-9)
            if abs(post - pre) > 0.5 * ain:
                mid = 0.5 * (pre + post)
                idx = np.where((D1[m] - mid) * np.sign(post - pre) >= 0)[0]
                if idx.size:
                    t50.append((t[m][idx[0]] - te) * 1e9)
                mo = (t >= te + 45e-9) & (t <= te + 150e-9)
                jj = int(np.argmax(np.abs(D1[mo] - post)))
                tov.append((t[mo][jj] - te) * 1e9)
                eov.append((D1[mo][jj] - post) * 1e3)
            ref = np.interp(te + 5e-9, t, D1)
            mb = (t >= te + 5e-9) & (t <= te + 35e-9)
            if mb.any():
                brk.append((D1[mb][int(np.argmax(np.abs(D1[mb] - ref)))] - ref) * 1e3)
            xpre = np.interp(te - 5e-9, t, XD)
            xpost = np.interp(te + 1e-6, t, XD)
            mx = (t >= te + 5e-9) & (t <= te + 38e-9)
            if mx.any():
                xb.append((XD[mx][int(np.argmax(np.abs(XD[mx] - xpre)))] - xpre) * 1e3)
            if abs(xpost - xpre) > 0.5 * ain:
                xmid = 0.5 * (xpre + xpost)
                m2 = (t >= te) & (t <= te + 1e-6)
                idx2 = np.where((XD[m2] - xmid) * np.sign(xpost - xpre) >= 0)[0]
                if idx2.size:
                    tm = t[m2][idx2[0]]
                    w = (t >= tm - 60e-9) & (t <= tm + 60e-9)
                    i1 = int(np.searchsorted(t, tm))
                    if 1 <= i1 < t.size:
                        slopes.append((XD[i1] - XD[i1 - 1]) / (t[i1] - t[i1 - 1]) * 1e-6)
                    ovs.append(float(np.max(XD[(t >= te) & (t <= te + 2e-6)]) - ain))
        print(f"-- ain = {ain} V")
        _stat("D1 passes its mid level, time after the REF_X edge", t50, "ns")
        _stat("D1 overshoot peak (45 ns to 150 ns), time after the edge", tov, "ns")
        _stat("D1 overshoot peak (45 ns to 150 ns), signed size relative to the post-edge level", eov, "mV")
        _stat("D1 excursion in the break (5 ns to 35 ns), largest magnitude", brk, "mV")
        _stat("X_DEM slope through the mid ramp (secant of the bracketing samples)", slopes, "V/us")
        _stat("X_DEM overshoot above ain within 2 us after the edge", ovs, "V")
        _stat("X_DEM excursion in the first 38 ns after the edge (before D1 reaches 50 %)", xb, "mV")
    d = by_step(load("P28d_quad"))[-1]
    t = d["t"]
    kmid = int(np.floor(TW / T2)) + 5
    te = kmid * T2
    m = (t >= te - 2e-9) & (t <= te + 20e-9)
    offs = (t[m] - te) * 1e9
    print("sample offsets after one REF_X edge (ns, P28d 2 V):", np.round(offs, 3).tolist())


if __name__ == "__main__":
    main()
    edge_stats()
