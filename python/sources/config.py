"""
Typed experiment configuration, optionally overridden from a small TOML file.

Each dataclass's defaults equal today's previously-hardcoded values, so a run
given no ``--config`` behaves exactly as before. A TOML file only needs to
specify the fields it wants to override.
"""

import tomllib
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

import ATE
import numpy as np

T = TypeVar("T")

# Single point of truth for which PSU heater channel heats which transistor
# (measured by which SCU). Validated on hardware, see "PSU Channel /
# Transistor Mapping" in python/FSD.md. SCU1 = active, SCU2 = blind/reference.
HEATER_CHANNEL_FOR_SCU: dict[str, int] = {"SCU1": 1, "SCU2": 3}


@dataclass
class HeaterConfig:
    """PSU voltage/current for a heater channel (ch1 or ch3)."""

    voltage: float
    current: float


@dataclass
class ATEConfig:
    """Shared ATE setup policy applied by ``SetupBase.setup_ate``.

    ESD (ch2) and fan (ch4) are always idempotently ensured on — asserting the
    same values on an already-enabled channel is a no-op. Heater channels
    (ch1/ch3) are left untouched unless explicitly configured here.

    If ``debug_device_io`` is set, every SCPI command sent to (and response
    read from) an instrument is logged — including every ``set_voltage``,
    ``enable_output``/``disable_output``, etc. — which is useful for
    confirming from a run's log alone (e.g. over a remote session) whether a
    channel was actually turned on.
    """

    esd_voltage: float = 5.0
    esd_current: float = 0.7
    fan_voltage: float = 7.0
    fan_current: float = 1.5
    heater1: HeaterConfig | None = None
    heater3: HeaterConfig | None = None
    debug_device_io: bool = False


@dataclass
class Sweep:
    """Describes a vector of values as start/stop/num instead of a literal list.

    Expanded into an explicit list at config-load time via ``to_list()``:
    ``scale="linear"`` uses ``np.linspace(start, stop, num)``, ``scale="log"``
    uses ``np.logspace(log10(start), log10(stop), num)``. In a TOML file this
    is written as a sub-table, e.g.::

        [experiment.frequencies]
        start = 0.1
        stop = 40.0
        num = 10
        scale = "log"
    """

    start: float
    stop: float
    num: int
    scale: str = "linear"

    def to_list(self) -> list[float]:
        if self.scale == "linear":
            values = np.linspace(self.start, self.stop, self.num)
        elif self.scale == "reverse-linear":
            values = np.flip(np.linspace(self.start, self.stop, self.num))
        elif self.scale == "log":
            values = np.logspace(np.log10(self.start), np.log10(self.stop), self.num)
        else:
            raise ValueError(
                "Sweep.scale must be 'linear', 'log' or 'reverse-linear' "
                f"got {self.scale!r}"
            )
        return [round(float(v), 6) for v in values]


# Field names allowed to be given as a ``Sweep`` sub-table in TOML, in addition
# to a literal list.
_SWEEP_FIELDS = (
    "frequencies",
    "scu_voltages",
    "heater_voltages",
    "lia_offsets",
    "psu_voltages",
    "scu_bias_voltages",
)


@dataclass
class LIAInstrumentConfig:
    """LIA + SCU bias configuration shared by the readout and snap-capture modes.

    Defaults match the settings recorded in a known-good run's CSV snapshot
    (e.g. ``Results/LIAMeasurementSetup/July2/510Hz.csv``).
    """

    v_scu1: float = 2.01
    v_scu2: float = 2.0
    scu_compliance: float = 1e-4
    offset: float = 0.955
    amplitude: float = 5e-3
    sensitivity: ATE.Sensitivity = ATE.Sensitivity.MV500
    filter_slope: ATE.FilterSlope = ATE.FilterSlope.DB24
    time_constant: ATE.TimeConstant = ATE.TimeConstant.MS100
    input_coupling: ATE.InputCoupling = ATE.InputCoupling.DC
    input_source: ATE.InputSource = ATE.InputSource.A
    input_range: ATE.InputRange = ATE.InputRange.V1


@dataclass
class LIASnapConfig(LIAInstrumentConfig):
    """Parameters for LIAMeasurementSetup's snap_only / snap_sweep modes.

    If ``configure_instruments`` is ``True``, the LIA + SCU bias settings
    above are applied (without a ``*RST``) before capturing; otherwise the
    live instrument configuration is left untouched, as if it were set up by
    hand beforehand.

    ``first_settle``, ``first_auto_phase`` and ``first_autophase_settle`` only
    apply to snap_sweep's first frequency point: it waits ``first_settle``
    (thermal settling), then optionally triggers an LIA auto-phase followed
    by a further ``first_autophase_settle`` wait, and only then starts
    capturing. Every subsequent frequency just waits ``settle`` before
    capturing.
    """

    duration: float = 60.0
    sample_interval: float = 1.0
    sweep_folder: str | None = None
    frequencies: list[float] | None = None
    settle: float = 20.0
    first_settle: float = 60.0
    first_auto_phase: bool = False
    first_autophase_settle: float = 60.0
    configure_instruments: bool = False


@dataclass
class LIAReadoutConfig(LIAInstrumentConfig):
    """Parameters for LIAMeasurementSetup's readout / scan_noise modes.

    ``lia_frequency`` is used by readout mode (single reference frequency);
    ``frequencies`` is used by scan_noise mode (frequency sweep).
    """

    lia_frequency: float = 1.0
    frequencies: list[float] = field(
        default_factory=lambda: [
            round(n, 3) for n in np.logspace(np.log10(0.1), np.log10(10e3), num=10)
        ]
    )


@dataclass
class LIAGasResponseInteractiveConfig(LIAInstrumentConfig):
    """Parameters for LIAMeasurementSetup's gas_response_interactive mode.

    A manually-gated continuous capture at a fixed (``temperature``,
    ``lia_frequency``) operating point: sampling starts immediately after the
    initial Enter press, then every subsequent Enter press marks the current
    row as ``f"{mark_label_prefix}_N"`` (N = 1, 2, 3, ...) without stopping
    the capture, and pressing Esc stops recording and moves straight into
    plotting/analysis. Useful for runs with an unknown or variable number of
    gas insertions/removals.

    ``temperature`` (heater ch1/ch3 voltage) is applied once, before
    ``settle``. ``v_scu1_start``/``v_scu2_start`` optionally set an explicit
    SCU1/SCU2 starting bias; left as ``None``, SCU bias starts from
    ``v_scu1``/``v_scu2`` (from ``LIAInstrumentConfig``).
    """

    lia_frequency: float = 510.0
    temperature: float = 2.5
    settle: float = 60.0
    sample_interval: float = 1.0
    session_folder: str | None = None
    v_scu1_start: float | None = None
    v_scu2_start: float | None = None
    mark_label_prefix: str = "mark"


@dataclass
class DifferentialCalibrationConfig(LIAInstrumentConfig):
    """Parameters for DifferentialCalibration: find a heater-voltage (PSU
    ch1/ch3) operating point where the LIA's demodulated X output is both
    phase-locked (auto-zeroed) and drift-free, before a differential-method
    measurement run.

    Startup mirrors ``gas_response_interactive``: heater ch1/ch3 set to
    ``temperature``, LIA reference from ``LIAInstrumentConfig``, then
    ``initial_settle``. Phase auto-zero (``APHS``) is retried up to
    ``phase_zero_max_retries`` times, waiting ``phase_zero_wait`` and
    checking ``abs(theta) <= theta_tolerance_deg`` after each attempt;
    exceeding the retry cap aborts the run.

    Once phase-locked, X/Y/theta are sampled every ``sample_interval`` into
    one continuous CSV for the whole run. Every ``window_duration`` seconds
    the slope of X vs time is fit; if ``abs(slope) > slope_threshold_v_per_s``,
    a bounded coordinate-descent search adjusts PSU ch1 then ch3 (increase
    then decrease) in ``psu_step`` increments up to ``psu_step_max`` away
    from ``temperature``, re-running phase auto-zero and a new window after
    every step, until the slope converges or the search space is exhausted.

    Once the search settles (converged or best-effort), a final
    ``final_validation_duration`` (default 600s / 10 min) observation-only
    window runs at the resulting voltage: X/Y/theta keep being sampled and
    the slope is fit and logged, but no further PSU adjustment is made — this
    is purely to confirm the chosen operating point holds up over a longer
    horizon than the 30s search windows.
    """

    lia_frequency: float = 510.0
    temperature: float = 2.5
    initial_settle: float = 60.0
    phase_zero_wait: float = 5.0
    theta_tolerance_deg: float = 0.6
    phase_zero_max_retries: int = 3
    window_duration: float = 30.0
    sample_interval: float = 0.5
    slope_threshold_v_per_s: float = 0.5e-6
    psu_step: float = 0.005
    psu_step_max: float = 0.025
    final_validation_duration: float = 600.0
    session_folder: str | None = None


@dataclass
class LIADigestSweepConfig:
    """Digest an already-captured LIA frequency-sweep folder and compile the
    R/theta/drift-vs-frequency summary plots. Touches no instruments.

    ``sweep_dir`` holds the per-frequency raw snap CSVs written by
    ``LIAMeasurementSetup``'s snap_sweep mode (see ``LIASnapConfig.sweep_folder``).
    ``phase_shift_deg`` is a constant offset added to every point's theta in the
    summary plot only (the underlying digest CSVs are unaffected) — e.g. if the
    first point's raw theta is 0 deg and ``phase_shift_deg`` is set to X, that
    point is displayed as X deg and a point with raw theta 5 deg is displayed
    as 5+X deg.
    """

    sweep_dir: str = ""
    baseline: bool = False
    phase_shift_deg: float = 0.0


@dataclass
class HeaterSlopeTableConfig:
    """Recompute heater-sensitivity points and slopes from stored monitor CSVs
    (``monitor_*.csv`` from the MCP operating-point session). Touches no
    instruments.

    Each measurement note in a monitor CSV becomes one point: the settled
    window is the last ``window_s`` seconds of the dwell since the previous
    logged setpoint change. Points are flagged ``short_settle`` (dwell below
    ``min_settle_s``), ``over_range`` (mean R above ``overrange_fraction`` of
    ``full_scale_v``), ``phase_suspect`` (last phase auto-zero happened at
    R below ``phase_min_r_v``), ``drifting`` (|drift| above
    ``settled_drift_uv_per_s``) and ``vd_low`` (a noted Vd below
    ``vd_flag_v``). ``heater_resolution_v`` is the PSU readback resolution,
    treated as a uniform quantization error on each ch1 value.
    """

    monitor_csvs: list[str] = field(default_factory=list)
    window_s: float = 300.0
    min_settle_s: float = 240.0
    full_scale_v: float = 1.0
    overrange_fraction: float = 0.95
    phase_min_r_v: float = 0.2
    settled_drift_uv_per_s: float = 20.0
    vd_flag_v: float = 0.150
    heater_resolution_v: float = 0.001


@dataclass
class DwellAnalysisConfig:
    """Quantify per-session R drift and cold-start-to-cold-start shift from
    isolated-dwell monitor CSVs (see ``setups/dwell_analysis.py``). Touches
    no instruments.

    Each CSV in ``dwell_csvs`` must contain one 'ISOLATED START' and one
    'ISOLATED END' note event; the linear drift of X = R cos(theta) is fit
    over that window only. ``local_slope_v_per_v`` (from a
    ``heater_slope_table`` run at the same Vgs/heater point) converts the
    cold-start X shift into an equivalent heater-voltage shift; leave 0 to
    skip that conversion.
    """

    dwell_csvs: list[str] = field(default_factory=list)
    block_s: float = 1800.0
    local_slope_v_per_v: float = 0.0


@dataclass
class LIADriftEvolutionConfig:
    """Analyze how a sweep folder's per-file R-drift rate evolves over the
    course of capture. Touches no instruments.

    ``digest_dir`` holds already-compiled ``*_digest.csv`` files (or raw snap
    CSVs) from one sweep, one per frequency point, captured sequentially
    starting at the lowest frequency. ``interval_s`` is the wall-clock time
    between the start of consecutive captures.
    """

    digest_dir: str = ""
    interval_s: float = 240.0


@dataclass
class OperatingPointSweepConfig(LIAInstrumentConfig):
    """Parameters for OperatingPointSweep: locate the GMOS's optimal DC
    operating point by characterizing SCU1/SCU2 IV curves across the LIA's
    DC reference offset and the heater temperature (PSU ch1/ch3).

    For every ``heater_voltages`` x ``lia_offsets`` combination, SCU1 and
    SCU2 are each swept independently through ``scu_voltages`` (log scale):
    while one channel is swept, the other is held at its own configured
    baseline (``v_scu1``/``v_scu2`` from ``LIAInstrumentConfig``), then reset
    to that baseline before the other channel's sweep starts. ``heater_settle``
    applies after every heater voltage change, ``offset_settle`` after every
    LIA offset change, and ``point_settle`` before each SCU voltage-step
    measurement.

    ``plot_offset_value`` names the single ``lia_offsets`` value used for the
    "IV plot for every heater voltage" comparison plot (the nearest swept
    offset is used if it doesn't match exactly).
    """

    heater_voltages: list[float] = field(default_factory=lambda: [2.5, 2.7, 3.0])
    lia_offsets: list[float] = field(default_factory=lambda: [0.8, 0.9, 1.0])
    scu_voltages: list[float] = field(
        default_factory=lambda: [
            round(float(v), 6) for v in np.logspace(np.log10(0.01), np.log10(2.0), 20)
        ]
    )
    heater_settle: float = 60.0
    offset_settle: float = 5.0
    point_settle: float = 0.1
    session_folder: str | None = None
    plot_offset_value: float = 0.9


@dataclass
class OperatingPointOffsetSweepConfig(LIAInstrumentConfig):
    """Parameters for OperatingPointOffsetSweep: locate the GMOS's optimal LIA
    DC reference offset at a fixed SCU bias.

    Unlike ``OperatingPointSweep`` (which sweeps a list of SCU voltages),
    SCU1/SCU2 are held at their configured baseline voltages (``v_scu1``/
    ``v_scu2`` from ``LIAInstrumentConfig``) for the whole sweep: for every
    ``heater_voltages`` x ``lia_offsets`` combination, the current at that
    fixed bias is measured once. ``heater_voltages`` and ``lia_offsets`` each
    accept a ``Sweep`` sub-table (linear scale) or a literal list.
    ``heater_settle`` applies after every heater voltage change,
    ``offset_settle`` after every LIA offset change, and ``point_settle``
    before each current measurement.

    Produces one plot per channel of measured SCU current vs LIA offset,
    overlaying every heater voltage.
    """

    heater_voltages: list[float] = field(
        default_factory=lambda: [round(float(v), 6) for v in np.linspace(2.5, 3.0, 6)]
    )
    lia_offsets: list[float] = field(
        default_factory=lambda: [round(float(v), 6) for v in np.linspace(0.8, 1.0, 6)]
    )
    heater_settle: float = 60.0
    offset_settle: float = 5.0
    point_settle: float = 0.5
    session_folder: str | None = None


@dataclass
class LIAOffsetSensitivitySweepConfig(LIAInstrumentConfig):
    """Parameters for LIAOffsetSensitivitySweep: measure GMOS current
    sensitivity to a small heater-voltage (gate temperature) perturbation,
    at each point of a heater-voltage x SCU-bias x LIA-offset sweep, for
    the active and blind devices simultaneously (SCU/PSU-channel pairing:
    ``HEATER_CHANNEL_FOR_SCU``).

    The LIA reference is held fixed at ``amplitude``/``lia_frequency`` for
    the whole run (set once at startup); only the DC reference offset is
    swept via ``lia_offsets``. ``psu_voltages`` and ``scu_bias_voltages``
    are each applied identically to both channels (PSU ch1+ch3, SCU1+SCU2)
    at every outer/middle sweep step.

    For every ``psu_voltages`` x ``scu_bias_voltages`` x ``lia_offsets``
    combination, each channel is measured independently: ``n_measurements``
    repeated spot current reads are averaged (with their MSE recorded) as
    the baseline, then only that channel's own PSU heater voltage is bumped
    by ``psu_step``, held for ``step_settle``, and re-averaged as the
    perturbed reading, before being restored to the nominal
    ``psu_voltages`` value. ``initial_settle`` applies once, right after the
    LIA/SCU instruments are configured and before the sweep starts (lets the
    setup thermally/electrically settle from a cold start). ``heater_settle``
    applies after every ``psu_voltages`` change, ``bias_settle`` after every
    ``scu_bias_voltages`` change, and ``offset_settle`` after every LIA
    offset change.
    """

    amplitude: float = 5e-3
    lia_frequency: float = 517.0
    initial_settle: float = 60.0
    psu_voltages: list[float] = field(
        default_factory=lambda: [round(float(v), 6) for v in np.linspace(2.5, 3.0, 6)]
    )
    scu_bias_voltages: list[float] = field(
        default_factory=lambda: [round(float(v), 6) for v in np.linspace(1.8, 2.2, 5)]
    )
    lia_offsets: list[float] = field(
        default_factory=lambda: [
            round(float(v), 6) for v in np.linspace(0.975, 1.0, 11)
        ]
    )
    psu_step: float = 1e-3
    n_measurements: int = 10
    heater_settle: float = 60.0
    bias_settle: float = 5.0
    offset_settle: float = 5.0
    step_settle: float = 1.0
    session_folder: str | None = None


@dataclass
class HeaterResistanceConfig:
    """Parameters for HeaterResistanceSetup: estimate heater resistance of PSU
    ``channels`` from a linear I-V fit.

    Each ``heater_voltages`` step is applied, held for ``settle`` seconds, and
    then measured as the mean of ``n_samples`` V/I readings taken
    ``sample_interval`` seconds apart (a lower bound: GPIB queries may be
    slower). The whole sweep is repeated ``n_repeats`` times (``repeat_wait``
    seconds apart) so the plot's error bars can be estimated from the
    repeat-to-repeat spread. ESD/fan protection is enabled via ``[ate]``
    defaults; no other device is used.
    """

    channels: list[int] = field(default_factory=lambda: [1, 3])
    heater_voltages: list[float] = field(
        default_factory=lambda: [round(float(v), 6) for v in np.linspace(0.5, 5.0, 19)]
    )
    current_limit: float = 0.6
    settle: float = 1.0
    n_samples: int = 5
    sample_interval: float = 0.0005
    n_repeats: int = 3
    repeat_wait: float = 5.0
    session_folder: str | None = None


@dataclass
class IVSweepConfig:
    """Parameters for IVSweep."""

    scu_tag: str = "SCU1"
    start: float = 0.001
    stop: float = 4.0
    step: float = 0.01
    scale: str = "linear"
    mode: str = "voltage"
    compliance: float = 1e-3


# Field names that hold a nested dataclass in TOML, mapped to that dataclass.
# ``heater1``/``heater3`` are HeaterConfig.
_NESTED_DATACLASS_FIELDS: dict[str, type] = {
    "heater1": HeaterConfig,
    "heater3": HeaterConfig,
}


def _dataclass_from_table(default: Any, table: dict[str, Any]) -> Any:
    """Layer a TOML table onto a default dataclass instance via dataclasses.replace.

    Unknown keys raise TypeError (fail loud on typos rather than silently
    dropping them). Fields listed in ``_NESTED_DATACLASS_FIELDS`` (e.g.
    ``heater1``/``heater3``) accept a sub-table that is recursively layered
    onto that nested dataclass's own defaults (so a TOML file only needs to
    specify the fields it wants to override, not the whole nested table).
    Fields listed in ``_SWEEP_FIELDS`` (e.g. ``frequencies``)
    accept a ``Sweep`` sub-table (``start``/``stop``/``num``/``scale``)
    instead of a literal list, and are expanded into a list at load time.
    Fields typed as an ``Enum`` (e.g. the LIA/SCU instrument settings) accept
    the member name as a string, e.g. ``sensitivity = "MV500"``.
    """
    overrides = dict(table)
    for key, nested_cls in _NESTED_DATACLASS_FIELDS.items():
        if key in overrides and isinstance(overrides[key], dict):
            try:
                nested_default = nested_cls()
            except TypeError:
                # No-default dataclass (e.g. HeaterConfig): the sub-table must
                # supply every field directly rather than overriding defaults.
                overrides[key] = nested_cls(**overrides[key])
            else:
                overrides[key] = _dataclass_from_table(nested_default, overrides[key])
    for key in _SWEEP_FIELDS:
        if key in overrides and isinstance(overrides[key], dict):
            overrides[key] = Sweep(**overrides[key]).to_list()
    field_types = {f.name: f.type for f in fields(default)}
    for key, value in overrides.items():
        field_type = field_types.get(key)
        if (
            isinstance(field_type, type)
            and issubclass(field_type, Enum)
            and isinstance(value, str)
        ):
            overrides[key] = field_type[value]
    valid = set(field_types)
    unknown = set(overrides) - valid
    if unknown:
        raise TypeError(f"{type(default).__name__}: unknown key(s) {sorted(unknown)}")
    return replace(default, **overrides)


def load_config(
    path: str | Path,
    experiment_cls: type[T] | None = None,
) -> tuple[ATEConfig, T | None]:
    """Load ``[ate]`` and ``[experiment]`` tables from a TOML file.

    Returns ``(ate_config, experiment_config)``. ``experiment_config`` is
    ``None`` if ``experiment_cls`` is ``None`` (e.g. modes without a config
    struct yet) or the file has no ``[experiment]`` table.
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    ate_config = _dataclass_from_table(ATEConfig(), data.get("ate", {}))

    experiment_config: T | None = None
    if experiment_cls is not None:
        experiment_config = _dataclass_from_table(
            experiment_cls(), data.get("experiment", {})
        )

    return ate_config, experiment_config
