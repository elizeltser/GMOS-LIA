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

# PC link is isolated; cable power is open

<span class="tag tag-proposed">PROPOSED: owner may drop</span>

- `ISO6721` isolates the board from the external FTDI cable.
- UART (universal asynchronous receiver-transmitter) link: text commands, 24-byte frames.
- 921 600 baud (bit/s): 1000 frames/s uses 26 % of the link.
- Open (D-21): cable's 5 V VCC on the isolated side.
- Owner decides: §5.6 `SET EXC 518.0 5.0` vs §F.7 `EXC FREQ <Hz>`.
- Not in docs: why the link is isolated.

Source: schematics/LIA-board/docs/requirements.md DG-4; schematics/LIA-board/docs/schematic_overview.md §5.4, §5.6; schematics/LIA-board/docs/firmware.md §F.2.3, §F.7; schematics/LIA-board/docs/README.md §9.1 D-21

<!-- Facts: S05-F01, S05-F02, S05-F03, S05-F06, S05-F07, S05-F08, S05-F13, S05-F14, S05-C01, S05-NF01. Say: The PC link is UART through an ISO6721 isolator, with the isolated side powered by the external FTDI cable. Its 5 V VCC is open (D-21): a 3.3 V LDO, 5 V-tolerant parts or TTL-232R-5V are the options. The link runs at 921 600 baud; 1000 frames/s of 24 bytes uses 26 % of it. The command sets in schematic_overview §5.6 and firmware §F.7 conflict; the owner decides. Isolation rationale is not in the docs. -->
