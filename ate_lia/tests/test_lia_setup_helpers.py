"""
Tests for setups.lia_setup.sigma_phase_zero.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from mcp_server.errors import PhaseZeroError
from setups.lia_setup import sigma_phase_zero


class _FakeLIA:
    """Fake LIA whose theta output improves (lower sigma) after each
    auto_phase() call, scripted via a list of per-iteration sample lists."""

    def __init__(self, theta_sequences):
        self._sequences = list(theta_sequences)
        self._current = None
        self.auto_phase_calls = 0

    def auto_phase(self):
        self.auto_phase_calls += 1
        self._current = iter(self._sequences[self.auto_phase_calls - 1])

    def snap(self, *_params):
        theta = next(self._current)
        return 0.0, 0.0, theta


def test_sigma_phase_zero_converges_after_improving_iterations():
    # First attempt: noisy (high sigma). Second attempt: tight (low sigma).
    lia = _FakeLIA([[1.0, -1.0, 1.0, -1.0], [0.05, -0.05, 0.05, -0.05]])
    result = sigma_phase_zero(
        lia, n_samples=4, sample_interval=0.0, sigma_tolerance_deg=0.2, max_iterations=5
    )
    assert result["converged"] is True
    assert result["iterations"] == 2
    assert result["sigma_deg"] <= 0.2
    assert lia.auto_phase_calls == 2


def test_sigma_phase_zero_raises_after_max_iterations_without_convergence():
    lia = _FakeLIA([[5.0, -5.0, 5.0, -5.0]] * 3)
    with pytest.raises(PhaseZeroError) as exc_info:
        sigma_phase_zero(
            lia,
            n_samples=4,
            sample_interval=0.0,
            sigma_tolerance_deg=0.2,
            max_iterations=3,
        )
    assert exc_info.value.iterations == 3
    assert lia.auto_phase_calls == 3
