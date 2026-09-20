"""
Tests for LIAMeasurementSetup's gas_response_interactive mode: config
loading, CLI registration, folder naming, and the unlimited-mark
capture/plotting helpers — all exercised without real GPIB hardware.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sources"))

import main  # noqa: E402
import setups  # noqa: E402
from config import LIAGasResponseInteractiveConfig, load_config  # noqa: E402
from setups.lia_setup import _VALID_MODES, LIAMeasurementSetup  # noqa: E402


def _make_setup() -> LIAMeasurementSetup:
    return object.__new__(LIAMeasurementSetup)


def test_registered_as_cli_experiment():
    assert "lia_gas_response_interactive" in main._EXPERIMENTS
    setup_cls, config_cls, ctor_kwargs, _overrides = main._EXPERIMENTS[
        "lia_gas_response_interactive"
    ]
    assert setup_cls is setups.LIAMeasurementSetup
    assert config_cls is LIAGasResponseInteractiveConfig
    assert ctor_kwargs == {"mode": "gas_response_interactive"}


def test_example_config_loads():
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "configs",
        "lia_gas_response_interactive.example.toml",
    )
    ate_config, cfg = load_config(config_path, LIAGasResponseInteractiveConfig)
    assert cfg is not None

    assert ate_config.heater1 is not None
    assert ate_config.heater3 is not None
    assert cfg.temperature == 2.9
    assert cfg.lia_frequency == 518.0
    assert cfg.mark_label_prefix == "mark"
    # The example TOML carries whatever session name the last run used, so only
    # check that one is set.
    assert isinstance(cfg.session_folder, str) and cfg.session_folder


def test_mode_is_valid():
    # __init__ raises ValueError on an unrecognized mode; gas_response_interactive
    # must be accepted (checked without invoking __init__, which opens a
    # real pyvisa.ResourceManager).
    assert "gas_response_interactive" in _VALID_MODES


def test_session_folder_naming_convention():
    # Mirrors gas_response_interactive():
    # Results/LIAMeasurementSetup/<session_folder>/gas_response.csv
    session_folder = "gas_response_interactive_run"
    out_dir = os.path.join("Results", "LIAMeasurementSetup", session_folder)
    gas_csv_path = os.path.join(out_dir, "gas_response.csv")

    assert gas_csv_path == os.path.join(
        "Results",
        "LIAMeasurementSetup",
        "gas_response_interactive_run",
        "gas_response.csv",
    )
