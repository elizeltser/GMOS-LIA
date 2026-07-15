"""
Digest an already-captured LIA frequency-sweep folder and compile summary plots.

Pure post-processing over stored CSVs: no instruments are touched.
"""

import glob
import logging
import os

from config import ATEConfig, LIADigestSweepConfig
from plotting import LIAFrequencyResponseCompiler, LIASnapDigest

from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class LIADigestSweep(SetupBase):
    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: LIADigestSweepConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: LIADigestSweepConfig = config or LIADigestSweepConfig()

    def run(self) -> None:
        csv_paths = sorted(glob.glob(os.path.join(self.config.sweep_dir, "*.csv")))
        if not csv_paths:
            raise ValueError(f"no CSVs found in {self.config.sweep_dir!r}")

        logger.info(f"Digesting {len(csv_paths)} snap CSV(s) in "
                    f"{self.config.sweep_dir}")
        digest_paths = []
        for path in csv_paths:
            digest = LIASnapDigest(path, baseline=self.config.baseline)
            digest_paths.append(digest.compile())
            digest.plot_timeseries()

        out_paths = LIAFrequencyResponseCompiler(
            digest_paths, out_name=self.output_name,
            phase_shift_deg=self.config.phase_shift_deg,
        ).compile()
        for p in out_paths:
            logger.info(f"Plot saved to: {p}")
