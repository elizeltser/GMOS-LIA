---
marp: true
html: true
theme: default
size: 16:9
paginate: true
footer: 'GMOS LIA Board · Status 1 · Eli Zeltser · 29 Oct 2026'
style: |
  section { font-size: 26px; padding: 40px 56px; }
  section h1 { font-size: 40px; }
  section table { font-size: 20px; }
  .risk-green  { background: #d4edda; font-weight: bold; }
  .risk-orange { background: #ffe0b2; font-weight: bold; }
  .risk-red    { background: #f8d7da; font-weight: bold; }
  .tag { font-size: 16px; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
  .tag-hard { background: #d4edda; }
  .tag-fluid { background: #fff3cd; }
  .tag-proposed { background: #e2e3f5; }
---

# Band-pass filter: tuned or wide? Open question

Filter fixed at 518 Hz; firmware sets frequency. ORANGE = medium risk.

| Option | Change needed | Risk | Mitigation |
|---|---|---|---|
| Fixed, 518 Hz | Outside band: new R and C | <span class="risk-orange">ORANGE: medium; re-tune outside band</span> | In band: calibrate gain and phase |
| Switchable | Design and add preset filter sets | <span class="risk-orange">ORANGE: medium; not designed yet</span> | Design and simulate each preset |
| Wide, Q 0.707 | No re-tune; 318–843 Hz band | <span class="risk-orange">ORANGE: medium; more mains, harmonics</span> | Bench harmonic check |

Source: schematics/LIA-board/docs/requirements.md AN-1, AN-21; schematics/LIA-board/docs/measurement_principles.md §2.8; schematics/LIA-board/docs/README.md §9.2 item 6

<!-- Facts: S24-F01, S24-F07, S24-F11, S24-F12, S24-F14, S24-F16, S24-F18, S24-F20, S24-F22, S24-F23, S24-NF04. Say: Inside the band, a frequency change needs only gain and phase calibration; outside it, new R and C are needed. Wide (Q 0.707) gives a 318–843 Hz band with no re-tune, a 2.9 degree phase change per ±1 % against 4.6 degree for Q 1, and a lower edge above the 1/f corner. It has 7 dB less attenuation at 50 Hz. Switchable has no design in the docs. Grades are the author's reading of the docs, with no recommendation. -->

---

# Band-pass filter: tuned or wide? (cont.)

| Unknown or conflict | Side one | Side two |
|---|---|---|
| Usable range | ≈400–700 Hz (requirements) | 305–700 Hz (firmware) |
| Range wanted | 100 Hz–10 kHz, draft (design-context) | ≈400–700 Hz (requirements) |
| Not in docs | Re-tune procedure, part count, time | Switchable filter design |
| Not in docs | Wider filter "may still work" (owner) | Wide-band noise or harmonic results |

Open question to the team: how wide a band is needed, and is a wider filter acceptable?

Source: schematics/LIA-board/docs/requirements.md AN-1, FW-4; schematics/LIA-board/docs/firmware.md F.6; simulations/design-context.md §3; simulations/design-issues.md DI-16

<!-- Facts: S24-C01, S24-C03, S24-F07, S24-F08, S24-F29, S24-NF01, S24-NF02, S24-NF04, S24-NF05, S24-NF07. Say: Two ranges disagree. AN-1 and README give about 400–700 Hz, while firmware F.6 accepts 305–700 Hz. The design-context draft says 100 Hz to 10 kHz, which is still a draft. The owner's "may still work", the re-tune procedure, the switchable design and wide-band noise results are not in the docs. No recommendation. -->
