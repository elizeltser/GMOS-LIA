"""Expected drain-referred noise for P-30 (afe_eval_P30.cir), with the drain node of the netlist.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-30_expected.py

Drain node model (afe_eval.cir): each side has R_D (330 kOhm, stiff bias behind it) to the drain, a node
capacitance to ground of 70 pF (cnode 50 pF + cmux 10 pF + INA828 C_CMN 10 pF), and the INA828 C_DIFF of 1 pF
between the two drains. The pixel noise is the shot noise as a resistor R_SH = 2kT/(qI) in parallel with
each pixel sink, so its noise current PSD is 4kT/R_SH = 2qI. The R_D thermal noise enters as a Norton
current with PSD 4kT/R_D. All sources are independent. T is the PSpice resistor temperature, 27 C = 300.15 K.
"""
import numpy as np

kB, q = 1.380649e-23, 1.602176634e-19
f0 = 518.0
w = 2 * np.pi * f0
ID = 7.5e-6
RD = 330e3
RSH = 2 * 0.025852 / ID          # 6.894 kOhm (not MOhm), kT/q at 300 K as in the netlist; compensated, so only its noise is kept
C_SELF = 70e-12                  # per drain node to ground
C_DIFF = 1e-12                   # between the drains
K = 2.0
RG = 5.62e3
G_INA = 1 + 50e3 / RG
T_SIM = 300.15


def drain_matrix(RD, RSH, Cs, Cd, f):
    """Nodal admittance matrix of the two drains, and the inverse (V = Zm i)."""
    w = 2 * np.pi * f
    G = 1 / RD  # the pixel resistor is compensated (G_CSA, G_CSB): no DC or AC load from R_SH
    Y = np.array([[G + 1j * w * (Cs + Cd), -1j * w * Cd],
                  [-1j * w * Cd, G + 1j * w * (Cs + Cd)]])
    return np.linalg.inv(Y)


def noise(T, RD, RSH, Cs, Cd, f):
    Zm = drain_matrix(RD, RSH, Cs, Cd, f)
    S_pix = 4 * kB * T / RSH           # noise current PSD of the pixel, equal to 2qI_D
    S_rd = 4 * kB * T / RD
    hd = Zm[1] - Zm[0]                       # V_B - V_A per unit current
    diff_pix = np.sqrt(np.sum(np.abs(hd) ** 2) * S_pix)
    diff_rd = np.sqrt(np.sum(np.abs(hd) ** 2) * S_rd)
    side_pix = np.sqrt(np.abs(Zm[0, 0]) ** 2 * S_pix + np.abs(Zm[0, 1]) ** 2 * S_pix)
    side_rd = np.sqrt(np.abs(Zm[0, 0]) ** 2 * S_rd + np.abs(Zm[0, 1]) ** 2 * S_rd)
    return side_pix, side_rd, diff_pix, diff_rd, Zm


def hpf(f, R1=9.31e3, R2=9.31e3, C1=33e-9, C2=33e-9, k=K):
    s = 2j * np.pi * f
    return k * s ** 2 / (s ** 2 + s * (1 / (R2 * C1) + 1 / (R2 * C2) + (1 - k) / (R1 * C1)) + 1 / (R1 * R2 * C1 * C2))


def lpf(f, R1=9.31e3, R2=9.31e3, C1=33e-9, C2=33e-9, k=K):
    s = 2j * np.pi * f
    wq = 1 / (R1 * R2 * C1 * C2)
    return k * wq / (s ** 2 + s * (1 / (R1 * C1) + 1 / (R2 * C1) + (1 - k) / (R2 * C2)) + wq)


def front(f):
    return G_INA * hpf(f) * lpf(f)


def sk_post(f, R=200e3, C=1.5e-6):
    s = 2j * np.pi * f
    wq = 1 / (R * R * C * C)
    return wq / (s ** 2 + s * 2 / (R * C) + wq)


def fold_ideal(H=front):
    tot = 0.0
    for n in range(1, 400, 2):
        tot += (4 / (n * np.pi)) ** 2 / 2 * abs(H(n * f0)) ** 2
    return np.sqrt(tot) / abs(H(f0))


if __name__ == "__main__":
    print(f"R_SH = {RSH/1e3:.4f} kOhm (compensated), C_self = {C_SELF*1e12:.0f} pF, C_diff = {C_DIFF*1e12:.0f} pF, T = {T_SIM} K")
    print("\n== Entry model (330 kOhm, no R_SH, 50 pF per node) at 300 K, for the check of the entry values")
    Z_entry = 330e3 / (1 + 1j * w * 330e3 * 50e-12)
    print(f"  shot per side  sqrt(2qI) RD = {np.sqrt(2*q*ID)*RD*1e9:.1f} nV/rtHz")
    print(f"  R_D per side   sqrt(4kT RD) = {np.sqrt(4*kB*300*RD)*1e9:.1f} nV/rtHz")
    print(f"  differential, entry = {np.sqrt(2*(np.sqrt(2*q*ID)*RD)**2 + 2*(np.sqrt(4*kB*300*RD))**2)*1e9:.1f} nV/rtHz")

    print("\n== Corrected drain model, T = 300.15 K")
    side_pix, side_rd, diff_pix, diff_rd, Zm = noise(T_SIM, RD, RSH, C_SELF, C_DIFF, f0)
    print(f"  Z_A (self) = {abs(Zm[0,0])/1e3:.2f} kOhm, Z_AB = {abs(Zm[0,1])/1e3:.2f} kOhm (entry node: 330 kOhm with 50 pF, |Z| = {abs(Z_entry)/1e3:.2f} kOhm)")
    print(f"  shot per side (pixel R_SH)  = {side_pix*1e9:.2f} nV/rtHz")
    print(f"  R_D per side                = {side_rd*1e9:.2f} nV/rtHz")
    print(f"  (Z_A over 330 kOhm alone with 70 pF = {abs(drain_matrix(RD, None, C_SELF, C_DIFF, f0)[0,0])/1e3:.2f} kOhm)")
    print(f"  differential shot           = {diff_pix*1e9:.2f} nV/rtHz")
    print(f"  differential R_D            = {diff_rd*1e9:.2f} nV/rtHz")
    sensor = np.sqrt(diff_pix**2 + diff_rd**2)
    print(f"  differential sensor total   = {sensor*1e9:.2f} nV/rtHz")
    amp_budget = sensor * np.sqrt(0.1 / 0.9)
    print(f"  amplifier budget (10 % of power) = {amp_budget*1e9:.2f} nV/rtHz")
    print(f"  total at the budget = {np.hypot(sensor, amp_budget)*1e9:.2f} nV/rtHz")
    sens_entry = np.sqrt(2 * (np.sqrt(2*q*ID)*RD)**2 + 2*(np.sqrt(4*kB*300*RD))**2)
    print(f"  ratio corrected / entry sensor = {sensor/sens_entry:.4f}")

    print("\n== Fold-down and X_OUT noise (ideal front end, unity post-filter)")
    fold = fold_ideal()
    print(f"  fold-down factor (ideal front end) = {fold:.4f}")
    fq = np.linspace(0, 50, 2000001)
    enbw = np.trapezoid(np.abs(sk_post(fq)) ** 2, fq)
    print(f"  post-filter ENBW = {enbw:.4f} Hz")
    vn = sensor * abs(front(f0)) * fold * np.sqrt(enbw)
    print(f"  X_OUT noise from the sensor, corrected = {vn*1e6:.2f} uV rms (entry 16.83 uV rms, 731 nV basis)")
    print(f"  |front(f0)| = {abs(front(f0)):.4f} V/V")
