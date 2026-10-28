# PSpice workflow for the TI-PSPICE project

This guide describes the files in this project, how OrCAD Capture and PSpice for TI 23.1 use them, and how to run and read simulations from the command line.

Paths are relative to the project root, `ti-pspice/`, unless they start with `C:\`. The facts come from files read in the project and from commands run on 2026-10-26. Section 8 lists what is still open.

## 1. Project layout

The git repository root is `GMOS-LIA/`, two levels above the project folder (`../..` from `ti-pspice/`). The general simulation documents (`simulation-index.md`, `design-context.md`, `design-issues.md`, `design-review/`) are one level up, in `simulations/`, and the simulation subagents are in the repository root `.claude/agents/`. The tree below skips `.git`. Each item has one of these tags:

- `[source]` a file written by hand or kept as a project input.
- `[generated, kept]` a file written by Capture or PSpice that `.gitignore` does not match. Git keeps these files.
- `[generated, ignored]` a file written by Capture, PSpice or the tools and matched by `.gitignore`.

```
ti-pspice/
├── .gitattributes                  [source] Marks *.dsn and *.olb as binary for git.
├── .gitignore                      [source] Ignore rules. See the notes below the tree.
├── CLAUDE.md                       [source] Project instructions for AI agents.
├── TI-PSPICE.DSN                   [source] Capture schematic database, binary. Holds all pages.
├── TI-PSPICE_0.DBK                 [generated, ignored] Capture backup of the .DSN.
├── TI-PSPICE.png                   [generated, ignored] Screenshot of the LIA schematic page.
├── ti-pspice.opj                   [source] Capture project file, text. Lists designs and profiles.
├── ti-pspice_pspmetadata.db        [generated, ignored] Capture metadata, binary. Not SQLite.
├── options.inc                     [source] PSpice solver options. Included by the LIA circuit file.
├── circuits/                       [source] Hand-written test circuits. Run them by path.
│   └── *.cir                       For example spdt_prec_select_test.cir, a SPDT_PREC polarity test.
├── archive/                        Frozen copies of GUI results worth keeping, one folder per run, each with a README.
├── tools/
│   ├── run_sim.py                  [source] Runs a profile or a circuit headless and collects CSDF results.
│   └── csdf.py                     [source] Reads CSDF (.csd) waveform files.
├── docs/
│   ├── pspice-workflow.md          [source] This guide.
│   ├── simulation-quirks.md        [source] Running log of simulation traps.
│   └── sim-results/                [source] One summary per index entry, with scripts/ and plots/.
├── sim-runs/                       [generated, ignored] Output of tools/run_sim.py, one folder per run name.
│                                   While a run is active it also holds the lock file .pspice.lock.
├── vendor/                         [ignored, except README] Third-party model and symbol libraries.
│   ├── README.md                   [source, tracked] Describes the vendor models.
│   ├── sbom862f/                   OPAx192 op amp: OPAx192.LIB, its signature OPAx192.LIBsig, OPAx192.OLB symbols, test project.
│   ├── sbom862f.zip                Archive of the sbom862f folder.
│   └── tmux6136/                   TMUX6136 switch: TMUX6136_BEH.LIB model library and symbol library. No .LIBsig file.
└── ti-pspice-PSpiceFiles/          Capture and PSpice output, one folder per design.
    ├── LIA/                        Design LIA (schematic page "lia").
    │   ├── LIA.als                 [generated, ignored] Alias map for the LIA netlist.
    │   ├── LIA.net                 [generated, ignored] Netlist of the LIA design.
    │   ├── LIA_sch.prp             [generated, kept] Schematic parameter to PSpice parameter map.
    │   ├── lia_sanity.sim          [generated, kept] Simulation profile "lia_sanity".
    │   └── lia_sanity/             Run folder for profile lia_sanity.
    │       ├── lia_sanity.cir      [generated, ignored] Circuit file for the profile.
    │       ├── lia_sanity.out      [generated, ignored] Text log of the last run.
    │       ├── lia_sanity.out.1    [generated, ignored] The log before the last run.
    │       ├── lia_sanity.dat      [generated, ignored] Binary Probe waveforms.
    │       ├── lia_sanity.1OP      [generated, ignored] Binary bias point file.
    │       ├── lia_sanity.json     [generated, kept] Run summary.
    │       ├── lia_sanity.mif      [generated, kept] Model library index.
    │       ├── lia_sanity.mrk      [generated, kept] Binary marker data.
    │       └── lia_sanity.prb      [generated, kept] Probe window settings.
    ├── differential-amplifier/     Design with two profiles.
    │   ├── differential-amplifier.als      [generated, ignored] Alias map.
    │   ├── differential-amplifier.net      [generated, ignored] Netlist.
    │   ├── differential-amplifier_sch.prp  [generated, kept] Parameter map.
    │   ├── frequency_analysis.sim  [generated, kept] AC profile.
    │   ├── time_analysis.sim       [generated, kept] Transient profile with a parameter step.
    │   ├── frequency_analysis/     Run folder. .cir, .out, .dat, .1OP and .out.1 are ignored.
    │   └── time_analysis/          Run folder. Same pattern as above.
```

The `.gitignore` rules decide which files git ignores. The rules `*.dat`, `*.out`, `*.out.*`, `*.[0-9]OP`, `*.net`, `*.als`, `*.cir`, `*.DBK`, `*.png`, `*_pspmetadata.db`, `vendor/*` and `sim-runs/` cover most generated files. Two exceptions keep files tracked: `!circuits/*.cir` keeps the hand-written test circuits, and `!vendor/README.md` keeps the vendor note. The comments in `.gitignore` call `*.mif` and `*.json` unsure. These files are not ignored, and git tracks the copies in the differential-amplifier run folders. The `.prb` and `.mrk` files are not ignored either.

All `[source]` files are tracked by git.

The `vendor/` model files are ignored by git. A clean clone needs them restored before any profile runs, because the `.cir` files refer to them with relative paths such as `../../../vendor/sbom862f/opax192.lib`.

The `sim-runs/` folder can hold runs made by other users or sessions. Do not delete runs that you did not make, and do not delete `sim-runs/.pspice.lock` while another run is active.

## 2. How Capture and PSpice fit together

`TI-PSPICE.DSN` is the Capture database. It holds the schematic pages. A design is one schematic page or group of pages. The project has two designs: `LIA` (page `lia`) and `differential-amplifier`. The project file `ti-pspice.opj` lists the designs and profiles and records the active profile, which is `lia_sanity.sim`.

A simulation profile is one set of analysis settings for a design. Capture stores each profile as a `.sim` file in the design folder. The `.sim` file names the netlist and the output files and lists the analyses. For example, `lia_sanity.sim` names `LIA.net` as its netlist and `lia_sanity.cir`, `lia_sanity.dat` and `lia_sanity.out` as its outputs.

Netlisting writes two files for each design. The `.net` file is the netlist. It lists every element and the nodes it connects. The `.als` file is the alias map. It links each netlist element to its schematic part and pin. Section 4 explains both files.

When a profile runs from the GUI, Capture writes the profile circuit file `<profile>.cir` into the run folder. This file does not hold the circuit itself. It holds the `.LIB` and `.INC` lines, the analysis lines, the `.PROBE64` lines and one `.INC` line that loads the design netlist. For `lia_sanity` this line is `.INC "..\LIA.net"`. The file header says the file is automatically generated and may be overwritten. The `.net` file reflects the schematic at the time of the last netlist.

The solver, `pspice.exe`, reads the `.cir` file and writes these outputs into the same run folder:

1. `.out`, a text log with the netlist echo, model parameters, warnings, the bias point when printed, and the job time.
2. `.dat`, the binary Probe waveform file.
3. `.1OP`, a binary bias point file.
4. `.json`, a run summary, and `.mif`, a model index.

Probe also writes `.prb` and `.mrk` files for its window settings and markers. When a profile runs again, PSpice keeps the previous log as `.out.1`. The `.out.1` files in this project show older settings than the matching `.out` files, so this is the likely meaning of the name.

The `.LIB` lines in each `.cir` file use paths relative to the run folder, such as `../../../vendor/sbom862f/opax192.lib`. The `.INC` line loads `../../../options.inc`. The header also says that PSpice adds `nom_pspti.lib` and `nom.lib` from the `[PSPICE NETLIST]` section of the installed `PSpice.ini`.

`ti-pspice.opj` still lists `schematic1\schematic1.net` under Outputs. That page no longer exists, and the entry is harmless.

## 3. File type reference

| Extension | Generated or source | Text or binary | Contents | How an agent should use it |
|---|---|---|---|---|
| `.opj` | Source | Text (S-expression) | Capture project: designs, profiles, folder layout, active profile. | Read to list profiles and the active profile. Change the project through Capture. |
| `.DSN` | Source | Binary | Capture schematic database, all pages. | Do not parse. Use Capture to change the schematic. |
| `.DBK` | Generated, ignored | Binary | Capture backup of the `.DSN`. Bytes differ from the current file. | Ignore. |
| `_pspmetadata.db` | Generated, ignored | Binary, not SQLite | Capture metadata. | Ignore. |
| `.png` | Generated, ignored | Image | Screenshot of the LIA page. | View to see the schematic layout and source values. |
| `options.inc` | Source | Text | `.OPTIONS` lines for the solver. | Read to see tolerances. The LIA circuit file includes it. |
| `.sim` | Generated, kept | Text | Profile: file names and analysis settings. | Read for the analysis settings. Change through Capture. |
| `.net` | Generated, ignored | Text | Netlist: elements, nodes, values, parameters. | Read for element values and connections. Capture regenerates it. |
| `.als` | Generated, ignored | Text | Map from netlist elements to schematic parts and pins. | Use it to find the schematic part behind a netlist name or node. |
| `_sch.prp` | Generated, kept | Text | Map from schematic parameters to PSpice parameters. | Read to find parameter values such as `RON`. |
| `.cir` | Generated, ignored | Text | Circuit file for one profile: includes, analyses, probes. | Read for analysis lines and includes. Do not edit by hand. Run it with `tools/run_sim.py`. |
| `.out` | Generated, ignored | Text | Solver log: netlist echo, warnings, bias point when printed, job time. | Main source for job status, warnings, errors and bias point. |
| `.out.1` | Generated, ignored | Text | The log before the last run. | Compare with `.out` after a rerun. Old errors can be here. |
| `.1OP` | Generated, ignored | Binary | Bias point values with node names. | Not read here. Use the bias table in `.out` when it exists. |
| `.dat` | Generated, ignored | Binary | Binary Probe waveform file. | Do not parse. Use a CSDF file made by `run_sim.py`. |
| `.json` | Generated, kept | Text | Run summary: time stamp, exit code, trace count, model files. | Check that `ExitCode` is `"0"`. |
| `.mif` | Generated, kept | Text | Library index: file, byte offset and size of each model. | Not needed for results. |
| `.mrk` | Generated, kept | Binary | Marker data for Probe windows. | Do not parse. |
| `.prb` | Generated, kept | Text | Probe window settings: analysis type, axes, traces, cursors. | Read to see which traces the GUI plots. |
| `.csd` | Generated, ignored | Text (CSDF) | Waveform export written by `run_sim.py` into `sim-runs/`. | Main numeric result for agents. See section 6. |
| `.pspice.lock` | Generated, ignored | Text (PID) | Lock file held by `run_sim.py` while one run is active. | Do not delete while a run is active. The script removes it when the run ends. |
| `.LIB` | Vendor, ignored | Text | Model library for a part. | Referenced by the `.cir` file. See section 5 for how `run_sim.py` rewrites it. |
| `.LIBsig` | Vendor, ignored | Not examined | Signature file next to a signed `.LIB`. | Its presence decides how `run_sim.py` treats the `.LIB` (section 5). |
| `.OLB` | Vendor, ignored | Binary | Symbol library. Marked binary in `.gitattributes`. | Do not parse. |

### Excerpts

The start of `lia_sanity.sim`:

```
@OrCAD Simulation Server Version: 1.0
@General:
ProfileName= "lia_sanity" 
Connectivity= "LIA.net" 
NetlistFile= "lia_sanity.cir" 
DataFile= "lia_sanity.dat" 
OutFile= "lia_sanity.out" 
```

Each `@Analysis: <index> <enabled>` block holds one analysis. In `time_analysis.sim`, the block `@Analysis: 0 1` holds the value `"25m"`, which matches `.TRAN 0 25m 0` in `time_analysis.cir`. In `frequency_analysis.sim`, the block `@Analysis: 1 1` holds `"100" "100" "1k"`, which matches `.AC DEC 100 100 1k`. The file is written by Capture, so change analysis settings in Capture.

One line of `LIA.als`:

```
R_R2            R2(1=N00890 2=N00610 ) CN @TI-PSPICE.LIA(sch_1):INS594@ANALOG.R.Normal(chips)
```

Section 4 explains this line.

The start of `lia_sanity.prb`:

```
[DISPLAYS]
BEGIN DISPLAY LAST SESSION
ANALYSIS TRANSIENT_ANALYSIS
SYMBOL ALWAYS
BEGIN CURSOR 1
CURSOR_X 1.9999995618658
CURSOR_Y 2.6504649571072
```

The `.prb` file of `frequency_analysis` names the analysis `AC_SWEEP` and plots traces such as `M(V(HPF)/V(Vdiff))`. The trace names show that the GUI plots ratios between nodes.

The first bytes of `frequency_analysis.mrk`, as hex:

```
07 00 00 00 00 00 00 00 00 00 00 00 09 00 00 00
07 00 00 00 0a 00 00 00 01 01 00 00 00 00 00 00
```

The file is binary. The `.prb` file refers to marker IDs such as `MARKERID 34`. The exact layout was not checked.

The start of `lia_sanity.json`, one line, shortened:

```
{"TimeStamp":"Mon Oct 26 16:26:28 2026\n","Circuits":{"ExitCode":"0","TraceCount":"25","Mode":"SPICE","Type":"TIFullMode","Models":[{"ModelName":"X_U2.X_U1.DVN","FileName":"c:\\users\\lw\\...\\vendor\\sbom862f\\opax192.lib", ...}]}}
```

The `Models` list gives the library file for each model. The file is read only for the summary.

The `.1OP` and `.dat` files are binary. Readable fragments appear inside them. `lia_sanity.1OP` contains names such as `N00261`, `VDC`, `X_U2.VCC_B` and `pR1:1`. `lia_sanity.dat` contains the text `AnalysisName`, `Transient Analysis` and `CircuitName`, followed by the profile name. The numbers are binary.

## 4. Reading a netlist

The netlist in `LIA/LIA.net` is the best place to see the element format. Excerpt:

```
X_U1         N00890 REF N00695 N00261 VDC 0 SPDT_PREC PARAMS:  RON=120 CS=4P
+  CD=6P QINJ=0.4P TAU=30N ILK=0.5P VTH=1.4
V_V2         N00261 0  
+PULSE 0 5 0 {t_slope} {t_slope} {0.5/f_osc} {1/f_osc}
V_V4         N00890 N07229  
+SIN {Vdc/2+ost} {Vampl} {fin} 0 0 {p}
V_V7         N07229 0  
+SIN 0 {Vharm_ampl} {f_osc*n_harm} 0 0 {p}
V_V8         REF 0 {Vref}
R_R1         N00610 VX_DEMOD  10k TC=0,0 
C_C1         0 VX  10u  TC=0,0 
```

### Element names

Capture builds each netlist name from a prefix and the schematic reference designator. The prefixes in this project are `X_` for subcircuits, `R_` for resistors, `C_` for capacitors, `V_` for voltage sources and `D_` for diodes. For example, the `.als` line for `R_R2` shows that the schematic designator is `R2`. The `.net` file of `differential-amplifier` has the diode `D_D3`.

### Continuation lines and parameters

A line that starts with `+` continues the line above it. The `V_V2` source uses two lines. The `X_U1` subcircuit also uses two lines.

The `PARAMS:` keyword starts the parameter list of a subcircuit. The values after it, such as `RON=120`, are set for that instance. A parameter name that the subcircuit does not define triggers a warning, as shown in section 6.

The waveform keywords `PULSE` and `SIN` take values in a fixed order. The input `SIN` line in the current LIA netlist is `SIN {Vdc/2+ost} {Vampl} {fin} 0 0 {p}`. Its fields are offset, amplitude, frequency, delay, damping and phase, in that order. The values come from the `.PARAM` line. The GUI defaults give an offset of 2.5 V, an amplitude of 2 V and a frequency of 518 Hz. The order of the `PULSE` values was not checked against the PSpice manual.

### Parameter expressions with braces

Curly braces mark an expression that PSpice evaluates. In `differential-amplifier.net`:

```
V_V7         M_UN0001 0  
+SIN 250m 15m {f} 0 0 0
.PARAM  f=518
```

The `{f}` in the source uses the value defined by `.PARAM f=518`. The stepped profile `time_analysis.cir` contains `.STEP PARAM f LIST 50 300 500 518 550 800`. The run log shows `CURRENT STEP PARAM F = 800` for the last step.

### Node 0 and node names

Node `0` is ground. Every circuit needs it.

Named nets keep their label, such as `VDC`, `VX`, `VX_DEMOD`, `+5V` and `-5V`. Nets without a label get a generated name such as `N00890`. The generated numbers change when the schematic changes. Look them up in the `.als` file instead of storing them.

### Mapping netlist nodes to pins with the .als file

Each `.als` entry has three parts. The first token is the netlist element name. The second token is the schematic reference designator with its pin map in parentheses. The text after `@` gives the location in the Capture project.

Take this line:

```
R_R2            R2(1=N00890 2=N00610 ) CN @TI-PSPICE.LIA(sch_1):INS594@ANALOG.R.Normal(chips)
```

The element name is `R_R2`. The schematic part is `R2`. Pin 1 of `R2` is on net `N00890`, and pin 2 is on net `N00610`. In `LIA.net` the same element is written as `R_R2 N00890 N00610 10k TC=0,0`. The location `TI-PSPICE.LIA(sch_1)` names the project and the LIA page. `INS594` is the instance number. `ANALOG.R` is the library part. The meaning of `CN` and `Normal(chips)` was not checked.

The pin order in the `.als` file matches the node order in the `.net` file. For example, `X_U2` maps `+`, `-`, `V+`, `V-` and `OUT` to `N00695 N00610 VDC 0 VX_DEMOD`, in that order. Use this rule to match a node to a pin in a subcircuit.

Lines with `_` on both sides, such as `_    _(Vx=VX)`, appear to map a schematic net name to the name used in the netlist. This reading comes from the file layout and was not checked in Capture.

To find every pin on a net, search the `.als` file for the net name:

```
grep -n "N00890" ti-pspice-PSpiceFiles/LIA/LIA.als
```

## 5. Running simulations headless

### Why not run pspice.exe -r directly

`pspice.exe` is single-instance. If any PSpice window is open, a new launch hands its job to that window and exits after about 1 s without writing a `.out` file. This was observed several times while setting up the project. The `run_sim.py` script is built around it.

A direct `pspice.exe -r` run also keeps its window open after the job ends. A direct run also writes its outputs into the folder of the `.cir` file, next to the Capture files. `tools/run_sim.py` avoids all three problems.

### What run_sim.py does

Run the script from the project root. A relative `.cir` path is resolved from the current folder.

1. **Resolve the target.** A target `<design>/<profile>` maps to `ti-pspice-PSpiceFiles/<design>/<profile>/<profile>.cir`. An existing path that ends in `.cir` is used as given. If the file is missing, the script exits with code 1 and asks for a first run from Capture.
2. **Prepare the copy of the circuit.** The script reads the `.cir` file and writes a copy to `sim-runs/<name>/<name>.cir`. Each step is listed below.
   - Each `.LIB "..."` or `.INC "..."` line with a path that contains a slash is resolved against the source folder. When the file exists, the path becomes absolute. A missing file with a slash in its path stops the run. Bare names such as `nom.lib` stay unchanged, because PSpice finds them on its library path.
   - The library rule in the next subsection can change `.LIB` to `.INC`.
   - Every `.PROBE` line is removed. With `--analysis`, the `.TRAN`, `.AC`, `.DC`, `.NOISE` and `.STEP` lines are removed and the new lines are inserted.
   - Before the line `.END`, the script inserts the `--analysis` lines, then the `--extra` lines, then `.OPTIONS FILEMODELSEARCH` if no such line exists, then `.PROBE/CSDF` with the probe names. The script inserts these lines only before a line that is exactly `.END`.
   - Each probe `V(NAME)` becomes `V([NAME])`. PSpice reads a bare `V(NAME)` as a device voltage, and a node gives `ERROR(ORPSIM-16306): Must be a two terminal device`. The bracket form is needed for nodes.
   - Old `.out`, `.csd` and `.dat` files in the run folder are deleted.
3. **Take the lock.** The script creates `sim-runs/.pspice.lock` with its process ID. A second `run_sim.py` process waits for the lock. A lock older than the wait plus the timeout counts as stale, and the script removes it.
4. **Wait for other PSpice processes.** The script checks `tasklist` every 3 s until no `pspice.exe` runs. It prints one `waiting:` line. A user's own PSpice window also blocks the run. The script never closes a PSpice that it did not start. After `--wait` seconds, the status is `busy`.
5. **Start the solver.** It runs `pspice.exe -r <name>.cir` with the run folder as the working folder.
6. **Poll the run.** Each second the script checks the state. If the process has ended, the status is `exited`. If the `.out` file contains `Total job time`, the status is `done`, and the script waits 1 s so the `.csd` file can be written. If the `.out` file has not grown for 10 s and contains `ERROR`, the status is `error`. The check stops at `--timeout`, and the status is `timeout`.
7. **Close its own process.** If the process is still running, the script terminates it and waits up to 10 s. It uses its own process handle, not an image name.
8. **Release the lock** and print the status, the output paths and every line that contains `ERROR`. If the process exited without a `.out` file, the script prints a hint to close all PSpice windows.

Steps 2 to 4 were checked against the generated `.cir` files of the test runs. The copy contained absolute `.LIB` and `.INC` paths, the `.PROBE/CSDF` line before `.END`, the `.OPTIONS FILEMODELSEARCH` line, and no `.PROBE64` lines.

### Library rule: when .LIB becomes .INC

The script rewrites a `.LIB` line to `.INC` only when both conditions hold:

- the library file has no signature sibling. A sibling is a file with the same name and the extension `.LIBsig`, compared case-insensitively. The function is `_is_signed`.
- the library file has no `.ENDL` line. The function is `_has_lib_sections`.

Results of this rule for the two vendor libraries, checked with the script's own functions:

| Library | `.LIBsig` present | `.ENDL` present | Copy in sim-runs |
|---|---|---|---|
| `vendor/sbom862f/OPAx192.LIB` | Yes | No | stays `.LIB` |
| `vendor/tmux6136/TMUX6136_BEH.LIB` | No | No | becomes `.INC` |

The reasons are these:

- A batch run did not find the `SPDT_PREC` subcircuit through `.LIB` in the unsigned home-made library. It did find it through `.INC`. This is why the unsigned library is converted.
- A signed TI library such as `OPAx192.LIB` must stay `.LIB`. As `.INC`, the OPAx192 model fails with `ERROR(ORPSIM-16583): More than one imported model containing transistors or diodes`. This was observed in a LIA run (26 October 2026).
- A file with `.ENDL` sections keeps `.LIB`. The script does not state why, and the reason was not checked.

**Advice for hand-written circuits.** Use `.INC` for the home-made flat switch library, such as `tmux6136`. Use `.LIB` for TI signed libraries, such as `OPAx192`. The script converts an unsigned `.LIB` line anyway, but writing `.INC` directly says what you mean. Keep the signed library as `.LIB`, because `.INC` for it fails.

### Options

| Option | Meaning | Example |
|---|---|---|
| `target` | `<design>/<profile>`, or a path to a `.cir` file. | `differential-amplifier/frequency_analysis` |
| `--name NAME` | Run name. It sets the folder and file base name. The default is the profile name. | `--name fmt_test` |
| `--probe NAME ...` | Signals to save. `V(NODE)` and `V([NODE])` both work. Without it, the `.PROBE/CSDF` line has no names. | `--probe "V([VDIFF])" "V(HPF)"` |
| `--analysis LINE` | Replaces all analysis lines. Can be repeated. | `--analysis ".AC DEC 10 100 1k"` |
| `--extra LINE` | Adds a directive before `.END`. Can be repeated. A second `.PARAM` for a name the netlist already defines may conflict. | `--extra ".OPTIONS NOPAGE"` |
| `--timeout SEC` | Maximum simulation time in seconds. Default 600. | `--timeout 900` |
| `--wait SEC` | Maximum seconds to wait for other PSpice processes to close. Default 1800. | `--wait 3600` |
| `-h` | Shows the help text. | `python tools/run_sim.py -h` |

Set a maximum time step for switching circuits. The Capture profiles in this project use `.TRAN` without a fourth field. Without it, PSpice took only a few steps per half period. In this project the LIA demodulator output came out 5.6 percent low. The error disappears with a maximum step such as `5u`. Use `2u` when harmonics above the third matter. The syntax is `.TRAN <print step> <stop> <start save> <max step> [SKIPBP]`. For example, `--analysis ".TRAN 0 2 0 5u SKIPBP"`. The LIA README gives the details.

### Status values

| Status | Meaning |
|---|---|
| `done` | The `.out` file contains `Total job time`. |
| `exited` | PSpice ended before `Total job time` was written. Often another PSpice took the job. |
| `error` | The `.out` file stopped growing for 10 s and contains `ERROR`. |
| `timeout` | `--timeout` was reached. |
| `busy` | Another PSpice stayed open for `--wait` seconds. No simulation ran. |

### Exit code

The script exits with 0 when the status is `done` and no line of the `.out` file contains `ERROR`. It exits with 1 in all other cases. These cases include the statuses `exited`, `error`, `timeout` and `busy`, any `ERROR` line in the `.out` file, and a missing profile or include file.

Exit code 0 was seen for the AC runs and the transient runs in this session. Exit code 1 was seen for a missing profile and for runs that ended with status `exited`.

### Probe naming

Plain node names need the `V(NAME)` or `V([NAME])` form. The script normalises the first to the second. These probes were checked:

- `--probe "V(+5V)"` produced `.PROBE/CSDF V([+5V])`. The CSDF file names the node `V(+5V)` and lists its aliases.
- `--probe "V(D)" "V(SEL)"` produced `V([D])` and `V([SEL])`. The CSDF file names them `V(D)` and `V(SEL)`.

Current probes such as `I(...)` and voltage differences were not tested.

### Writing your own circuit

1. Put the file in `circuits/` with the extension `.cir`. The `.gitignore` rule `!circuits/*.cir` lets git track it.
2. Load the models with `.INC` or `.LIB`, following the library advice in this section. Paths are relative to the circuit file. For example, `.INC "../vendor/tmux6136/tmux6136_beh.lib"` works from `circuits/`.
3. Give an analysis line such as `.TRAN 0 3m 0 1u`. End the file with `.END` on its own line. The script inserts the probe line before `.END`, so a file without `.END` gets no probe line.
4. Name the probes `V(NODE)` or `V([NODE])`. For a node with a sign, such as `+5V`, use `V(+5V)` or `V([+5V])`.
5. Run it by path from the project root:

```
python tools/run_sim.py circuits/spdt_prec_select_test.cir --name spdt_test --probe "V(D)" "V(SEL)"
```

The results go to `sim-runs/<name>/`. Use `--analysis` to change the analysis without editing the file.

The file `circuits/spdt_prec_select_test.cir` has a `.TRAN 0 3m 0 1u` line. A run with `--analysis ".TRAN 0 3mm 0 1u"` gave 3077 points from 0 to 0.003 s, and `V(D)` between 0.99 V and 2.02 V.

### Run times

| Run | Analysis | Job time in .out | Wall time of the run |
|---|---|---|---|
| `LIA/lia_sanity` | Transient, 0 to 2 s | 63.66 s | not measured |
| `differential-amplifier/frequency_analysis` | AC, 100 Hz to 1 kHz | 14.49 s | 17 s |
| `differential-amplifier/time_analysis` | Transient, six steps | 2.39 s | 11 s |
| `circuits/spdt_prec_select_test.cir` | Transient, 0 to 3 ms | not measured | 9 s |

Runs can take seconds for AC and minutes for long transients. Use `--timeout` for long runs and `--wait` when other PSpice work is running.

## 6. Reading results

### CSDF file structure

A `.csd` file is text. Excerpt of the first lines of a real AC run, with the long title shortened:

```
#H
SOURCE='PSPICE' VERSION='PSpice 23.1.0 (Nov 2018)'
TITLE='** Profile: "differential-amplifier-frequency_analysis"  [ C:\...'
SUBTITLE=''
TIME='16:50:04' DATE='10/26/26' TEMPERATURE='2.700E01'
ANALYSIS='AC Sweep' SERIALNO='61413'
ALLVALUES='NO' COMPLEXVALUES='YES' NODES='1'
SWEEPVAR='Frequency' SWEEPMODE='LOG'
XBEGIN='1.000E02' XEND='1.000E03'
FORMAT='0 R_VOLTSorAMPS;EFLOAT / I_VOLTSorAMPS;EFLOAT : NODEorBRANCH;NODE  '
DGTLDATA='NO' 
#N 
'V(HPF)';'V(R22:1)';'V(R17:2)';'V(U2:-)';'V(U2:OUT)';'V(HPF)';'V1(R22)';'V2(R17)';'V1(X_U2.R_R2)';'V1(X_U2.X_U21.S1)';'VC1(X_U2.X_U21.S1)';
'V2(X_U2.X_U21.S2)';'VC2(X_U2.X_U21.S2)';'V2(X_U2.X_H1.VH_H1)' 
#C 1.0000000000E02 1
3.083E-25/-4.712E-24:1 
#C 1.0232929923E02 1
3.805E-25/-4.846E-24:1 
...
#;
```

The file has these parts:

- The `#H` line starts a header block. The header holds `KEY='value'` pairs. `ANALYSIS` gives the analysis type. `SWEEPVAR` gives the sweep variable, and `XBEGIN` and `XEND` give its range. `COMPLEXVALUES='YES'` means that each value is a complex number.
- The `#N` block lists the signal names. A name followed by `;` continues an alias group. A name without `;` ends the group. `NODES='1'` and the list above show one group of 14 names. The group holds all the names of one node.
- Each data point starts with `#C`, followed by the sweep value and a second token. The second token was `1` in every point of this file. Its meaning was not checked.
- The value line gives `real/imag:flag`. The `:1` flag appears on every value. Its meaning was not checked. `csdf.py` drops it.
- The file ends with `#;`.

The test AC file had 101 points for `.AC DEC 100 100 1k`.

### Stepped runs

A `.STEP` run writes one `#H` section for each step value. The test run `differential-amplifier/time_analysis` with `--probe "V(VSAMPLE)"` gave six sections for the steps 50, 300, 500, 518, 550 and 800. The header of the section for step 300 is:

```
#H
SOURCE='PSPICE' VERSION='PSpice 23.1.0 (Nov 2018)'
TITLE='** Profile: "differential-amplifier-time_analysis"  [ C:\...'
SUBTITLE='Step param f =  300   '
TIME='17:02:41' DATE='10/26/26' TEMPERATURE='2.700E01'
ANALYSIS='Transient Analysis' SERIALNO='61413'
ALLVALUES='NO' COMPLEXVALUES='NO' NODES='1'
SWEEPVAR='Time' SWEEPMODE='VAR_STEP'
XBEGIN='0.000E00' XEND='2.500E-02'
FORMAT='0 VOLTSorAMPS;EFLOAT : NODEorBRANCH;NODE  '
DGTLDATA='NO' 
#N
```

The step value is kept in the `SUBTITLE` key as text. There is no `STEPVALUE` key in these files. `Section.step` returns the stripped label, such as `Step param f =  300`. `Section.step_value` returns the number as a float, here `300.0`. It returns `None` for a run without steps. `csdf.py --list` prints the label. The transient sections have `COMPLEXVALUES='NO'`, and their `FORMAT` line has no `R_` prefix. The point count differs for each step: 123, 140, 164, 167, 178 and 224.

This script prints each step value with the peak of a transient signal. It was tested on a synthetic stepped file with two sections, where it printed 300.0 and 500.0 with peaks of 0.999 and 2.499.

```python
import sys; sys.path.insert(0, "tools")
from csdf import read_csdf
for s in read_csdf("sim-runs/NAME/NAME.csd"):
    print(s.step_value, s["V(VSAMPLE)"].max())
```

The peak uses `.max()`, which applies to real transient values. For complex AC values, use `np.abs(...)` first.

### tools/csdf.py command line

```
python tools/csdf.py FILE.csd --list
python tools/csdf.py FILE.csd --summary [--signals V(VX) V(VY)]
python tools/csdf.py FILE.csd --csv OUT.csv [--section 0] [--signals ...]
```

- `--list` prints each section with its analysis, sweep variable, point count and step label, followed by each alias group. With no `--summary` or `--csv` option, the script lists the file.
- `--summary` prints, for each signal, the minimum, maximum, mean and final value. For complex signals it prints the maximum magnitude, the frequency where it occurs, and the first and last magnitudes.
- `--csv` writes one section to a CSV file. Complex signals become a magnitude column and a phase column in degrees.
- `--section N` picks the section for `--csv`. The default is 0.
- `--signals` takes names exactly as they appear in an alias group. Any alias of the node works. A name that is not found raises `KeyError`, based on the code.

Output from a test run:

```
$ python tools/csdf.py sim-runs/NAME/NAME.csd --list
[0] AC Sweep  sweep=Frequency  points=101  
     V(HPF) = V(R22:1) = V(R17:2) = V(U2:-) = V(U2:OUT) = V(HPF) = V1(R22) = ...

$ python tools/csdf.py sim-runs/NAME/NAME.csd --summary --signals "V(HPF)"
[0] AC Sweep 
  V(HPF)               |max|=6.944e-21 at 1000  |first|=4.722e-24  |last|=6.944e-21

$ python tools/csdf.py sim-runs/NAME/NAME.csd --csv check.csv --signals "V(HPF)"
Frequency,|V(HPF)|,phase(V(HPF))
1.000000000000000000e+02,4.722075061876928698e-24,-8.625654776363718668e+01
```

The `V(HPF)` values in this run are about 1e-21 V. This is a circuit issue. Section 8 says where it is documented.

### Python use

Run the code from the project root.

```python
import sys
sys.path.insert(0, "tools")
from csdf import read_csdf

sections = read_csdf("sim-runs/NAME/NAME.csd")
s = sections[0]
s.header["ANALYSIS"]      # 'AC Sweep'
s.x                       # sweep array, frequency in Hz here
s["V(HPF)"]               # complex array. Any alias of the node works.
s.names                   # first alias of each node
"V(HPF)" in s             # True if the name is known
s.step                    # step label of a .STEP section, e.g. 'Step param f =  300'
s.step_value              # the same step as a float (300.0), or None
```

For AC runs, the values are complex. Use `np.abs` for magnitude and `np.angle` for phase.

### Example: gain in dB and -3 dB points

This script computes the gain in dB from a single-output AC sweep. It prints the reference gain at the lowest frequency and every -3 dB crossing. The AC source in `differential-amplifier` is `1Vac`, so `|V(node)|` equals the gain. For a ratio of two nodes in the same run, divide the two complex arrays first.

```python
import sys
import numpy as np
sys.path.insert(0, "tools")
from csdf import read_csdf

sec = read_csdf(sys.argv[1])[0]
f = sec.x
gain_db = 20 * np.log10(np.abs(sec[sys.argv[2]]))

ref = gain_db[0]              # reference: gain at the lowest frequency
target = ref - 3.0
print(f"reference gain {ref:.2f} dB at {f[0]:.4g} Hz, peak {gain_db.max():.2f} dB")

idx = np.where(np.diff(np.sign(gain_db - target)) != 0)[0]
for i in idx:                 # interpolate linearly in log10(f)
    x0, x1 = np.log10(f[i]), np.log10(f[i + 1])
    y0, y1 = gain_db[i], gain_db[i + 1]
    fc = 10 ** (x0 + (target - y0) * (x1 - x0) / (y1 - y0))
    print(f"-3 dB point near {fc:.4g} Hz")
if len(idx) == 0:
    print("no -3 dB crossing in the sweep")
```

Run it as `python script.py sim-runs/NAME/NAME.csd "V(HPF)"`.

The script was tested on a synthetic CSDF file with the layout of the real file above. The file had a single pole at 300 Hz and a DC gain of 10. The script printed a reference gain of 19.54 dB at 100 Hz and a -3 dB point near 330.5 Hz. The exact -3 dB point of that model is about 333 Hz. The small difference comes from the linear interpolation between sweep points. The test did not use a real simulation result.

### Bias point and errors in the .out file

Search the `.out` file with these patterns:

- `SMALL SIGNAL BIAS SOLUTION` starts the bias point table. The AC run `frequency_analysis.out` has it at line 195. The table lists each node voltage, such as `(  +5V)    4.9921`. The transient run `lia_sanity.out` has no such table. Its bias point is only in the binary `.1OP` file.
- `ERROR` finds errors. No current `.out` file contains an `ERROR` line. Older `.out.1` files do, and they are listed below.
- `WARNING(` finds warnings. The `lia_sanity.out` file has three. Lines 81 and 83 say that `<X_U1.VTH>` and `<X_U3.VTH>` are not subcircuit parameters. The `VTH=1.4` values in `LIA.net` do not appear to reach the model. Line 197 warns that a high ITL4 value may increase the job time.
- `INFO(` shows notes. The AC runs have one note, `ORPSIM-16573`, which says that AC analysis does not evaluate expressions at each frequency.
- `JOB CONCLUDED` marks the end of the solver work. `Total job time` marks the end of the log. `tools/run_sim.py` waits for this line.

The `.out.1` files hold errors from earlier runs:

- `differential-amplifier/time_analysis/time_analysis.out.1`, lines 69 to 75: `ORPSIM-15141` and `ORPSIM-15142`. Node `M_UN0001` and node `N11764` have fewer than two connections and are floating.
- `LIA/lia_sanity/lia_sanity.out.1`, line 199: `ORPSIM-15413`. The transient stop time 0.6 s is less than the print start time 1.4 s.

The first part of each `.out` file echoes the netlist used in the run, from `**** CIRCUIT DESCRIPTION` to `**** RESUMING`. Use this echo to see the netlist that was actually run, which can differ from the current `.net` file after a schematic edit.

## 7. PSpice syntax pitfalls

- **Scale suffixes.** The AC stop frequency `1k` became `XEND='1.000E03'` in the CSDF header, so `k` means 1000. The transient stop time `3mm` in `circuits/spdt_prec_select_test.cir` gave a last time point of 0.003 s. So `m` means milli, and the trailing `m` is ignored. The suffix `MEG` was not tested.
- **Probe form.** Write node probes as `V(NODE)` or `V([NODE])`. A bare `V(NODE)` on a node reads as a device voltage. `run_sim.py` converts it to the bracket form, but hand-written probe lines in `.cir` files need the bracket form.
- **Case.** PSpice treats names as case-insensitive. The schematic name `Vdc` appears as `VDC` in the netlist, and `LIA.als` maps `Vdc` to `VDC`. The CSDF names are upper case, such as `V(HPF)`. The `.prb` file keeps a mixed-case trace name, `V(Vx_demod)`.
- **Special characters in node names.** The names `+5V` and `-5V` are valid in this project. They appear in the netlist, such as `R_R14 N06938 +5V 3`, and in the bias table as `(  +5V)`. The probe `V(+5V)` works through `run_sim.py` and gives the CSDF name `V(+5V)`.
- **Pin aliases.** The CSDF file lists pin names as aliases, such as `V(U2:OUT)` and `V(U2:-)`. A name with a colon is a pin alias of the node in the same alias group.
- **Continuation lines.** A line that starts with `+` continues the line above. Put the `+` in the first column.
- **Comments.** Lines that start with `*` or `**` are comments.
- **Braces.** `{f}` evaluates an expression. It needs a `.PARAM` line that defines `f`.
- **Relative include paths.** A path such as `..\LIA.net` with a backslash works. The LIA log shows `**** INCLUDING LIA.net ****`.
- **Library type.** A signed TI library must stay `.LIB`. An unsigned flat library works through `.INC`. Section 5 gives the rule.
- **Unknown parameters.** A parameter that the subcircuit does not define gives a warning and has no effect, as shown by the `VTH` warnings in section 6.
- **Ground.** Node `0` is ground. A circuit without node `0` is not valid.
- **Transient maximum step.** A `.TRAN` line without a fourth field can let PSpice take steps that are too large for switching circuits. This gave wrong results in the LIA profile. Give a maximum step as the fourth field, for example `.TRAN 0 2 0 5u`. See section 5.
- **Output precision.** CSDF values use four significant digits by default, so a 2.5 V signal is resolved to 1 mV. `.OPTIONS NUMDGT=8` (for example `--extra ".OPTIONS NUMDGT=8"`) gives eight digits. The LIA README uses it to resolve a 0.3 mV ripple and a 58 uV DC error.
- **Value order in waveforms.** `PULSE` and `SIN` take their values in a fixed order. Check the order against the schematic labels or the PSpice manual before editing a source line.

## 8. Open items

- **The AC level of `V(HPF)` and `V(VDIFF)` is about 1e-21 V.** This is a circuit issue (the INA828 inputs have no DC reference). It is documented in `ti-pspice-PSpiceFiles/differential-amplifier/README.md`, with a corrected copy in `circuits/diffamp_ac_fixed.cir`.
- **Capture regeneration.** The statement that Capture rewrites `.cir` files on each GUI run comes from the file headers. It was not tested in the Capture GUI.
- **Unknown file fields.** The meaning of the second token on each `#C` line, the `:1` flag after each value, the `CN` and `Normal(chips)` tokens in `.als`, and the contents of `.1OP`, `.mif` and `.mrk` were not checked.
- **Other scale suffixes.** `MEG` was not tested.
- **Other probe forms.** Current probes such as `I(...)` were not tested.
- **Library rule.** The reason for keeping `.LIB` on files with `.ENDL` sections was not checked.
