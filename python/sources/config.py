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
            raise ValueError(f"Sweep.scale must be 'linear', 'log' or 'reverse-linear' got {self.scale!r}")
        return [round(float(v), 6) for v in values]


# Field names allowed to be given as a ``Sweep`` sub-table in TOML, in addition
# to a literal list.
_SWEEP_FIELDS = ("frequencies",)


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
    amplitude: float = 25e-3
    sensitivity: ATE.Sensitivity = ATE.Sensitivity.MV500
    filter_slope: ATE.FilterSlope = ATE.FilterSlope.DB24
    time_constant: ATE.TimeConstant = ATE.TimeConstant.MS100
    input_coupling: ATE.InputCoupling = ATE.InputCoupling.DC
    input_source: ATE.InputSource = ATE.InputSource.A
    input_range: ATE.InputRange = ATE.InputRange.V1


@dataclass
class BiasCalibrationConfig:
    """Closed-loop calibration of heater voltages (PSU ch1/ch3) and SCU bias
    voltages (v_scu1/v_scu2) toward target SCU drain currents.

    Disabled by default. When enabled, ``LIAMeasurementSetup.snap_sweep`` runs
    this once, on the first frequency point only, after the initial thermal
    settle and before auto-phase. Heater ch1 is paired with SCU2's current and
    heater ch3 is paired with SCU1's current (cross-paired, confirmed against
    the physical setup — not matched by channel number).

    Phase 1 (coarse): hill-climbs each heater's voltage, alternating between
    the two, re-measuring the paired SCU's current after each
    ``heater_settle_time`` thermal settle, until within ``current_tolerance``
    or ``heater_max_steps``/``max_rounds`` are exhausted.

    Phase 2 (fine): hill-climbs each SCU's own bias voltage in
    ``scu_voltage_step`` increments (near-instant settle) until within
    ``final_current_tolerance`` or ``scu_max_steps`` is exhausted.
    """
    enabled: bool = False
    target_current_scu1: float = 4.5e-6
    target_current_scu2: float = 4.5e-6
    current_tolerance: float = 1e-6
    final_current_tolerance: float = 5e-7
    heater_step_voltage: float = 0.01
    heater_min_step_voltage: float = 0.001
    heater_settle_time: float = 1.0
    heater_max_steps: int = 40
    heater1_min_voltage: float = 2.5
    heater1_max_voltage: float = 3.0
    heater3_min_voltage: float = 2.5
    heater3_max_voltage: float = 3.0
    max_rounds: int = 5
    scu_voltage_step: float = 10e-6
    scu_settle_time: float = 0.5
    scu_max_steps: int = 200


@dataclass
class LIASnapConfig(LIAInstrumentConfig):
    """Parameters for LIAMeasurementSetup's snap_only / snap_sweep modes.

    If ``configure_instruments`` is ``True``, the LIA + SCU bias settings
    above are applied (without a ``*RST``) before capturing; otherwise the
    live instrument configuration is left untouched, as if it were set up by
    hand beforehand.

    ``first_settle``, ``first_auto_phase`` and ``first_autophase_settle`` only
    apply to snap_sweep's first frequency point: if bias auto-calibration is
    enabled it runs right after the initial frequency/bias is applied, then
    it waits ``first_settle`` (thermal settling), then optionally triggers an
    LIA auto-phase followed by a further ``first_autophase_settle`` wait, and
    only then starts capturing. Every subsequent frequency just waits
    ``settle`` before capturing.
    """
    duration: float = 60.0
    sample_interval: float = 1.0
    sweep_folder: str | None = None
    frequencies: list[float] = None
    settle: float = 20.0
    first_settle: float = 60.0
    first_auto_phase: bool = False
    first_autophase_settle: float = 60.0
    configure_instruments: bool = False
    calibration: BiasCalibrationConfig = field(default_factory=BiasCalibrationConfig)


@dataclass
class LIAReadoutConfig(LIAInstrumentConfig):
    """Parameters for LIAMeasurementSetup's readout / scan_noise modes.

    ``lia_frequency`` is used by readout mode (single reference frequency);
    ``frequencies`` is used by scan_noise mode (frequency sweep).
    """
    lia_frequency: float = 1.0
    frequencies: list[float] = field(
        default_factory=lambda: [round(n, 3) for n in np.logspace(np.log10(0.1), np.log10(10e3), num=10)]
    )


@dataclass
class LIAGasResponseConfig(LIAInstrumentConfig):
    """Parameters for LIAMeasurementSetup's gas_response mode.

    A manually-gated single-frequency capture for actual gas dosing runs.
    After configuring the LIA/SCU bias and (optionally) running closed-loop
    bias auto-calibration, the operator presses Enter three times: once the
    setup has settled to start baseline recording, once the instant gas is
    inserted (ending the baseline capture and starting the gas-exposure
    capture), and once to stop recording. Output is two CSVs
    (``baseline.csv``, ``gas.csv``) in the same snap format as
    ``snap_only``/``snap_sweep``.
    """
    lia_frequency: float = 510.0
    auto_phase: bool = True
    autophase_settle: float = 0.0
    settle: float = 60.0
    sample_interval: float = 1.0
    session_folder: str | None = None
    calibration: BiasCalibrationConfig = field(default_factory=BiasCalibrationConfig)


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
    baseline: bool = True
    phase_shift_deg: float = 0.0


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
# ``heater1``/``heater3`` are HeaterConfig; ``calibration`` is BiasCalibrationConfig.
_NESTED_DATACLASS_FIELDS: dict[str, type] = {
    "heater1": HeaterConfig,
    "heater3": HeaterConfig,
    "calibration": BiasCalibrationConfig,
}


def _dataclass_from_table(default: Any, table: dict[str, Any]) -> Any:
    """Layer a TOML table onto a default dataclass instance via dataclasses.replace.

    Unknown keys raise TypeError (fail loud on typos rather than silently
    dropping them). Fields listed in ``_NESTED_DATACLASS_FIELDS`` (e.g.
    ``heater1``/``heater3``/``calibration``) accept a sub-table that is
    recursively layered onto that nested dataclass's own defaults (so a TOML
    file only needs to specify the fields it wants to override, not the whole
    nested table). Fields listed in ``_SWEEP_FIELDS`` (e.g. ``frequencies``)
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
        if isinstance(field_type, type) and issubclass(field_type, Enum) and isinstance(value, str):
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
        experiment_config = _dataclass_from_table(experiment_cls(), data.get("experiment", {}))

    return ate_config, experiment_config
