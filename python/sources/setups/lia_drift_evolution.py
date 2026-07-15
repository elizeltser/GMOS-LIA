"""
Analyze how R-drift rate evolves across an already-captured sweep folder.

Pure post-processing over stored digest CSVs: no instruments are touched.
"""

import glob
import logging
import os

from config import ATEConfig, LIADriftEvolutionConfig
from plotting import LIADriftEvolutionCompiler

from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class LIADriftEvolution(SetupBase):
    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: LIADriftEvolutionConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: LIADriftEvolutionConfig = config or LIADriftEvolutionConfig()

    def run(self) -> None:
        csv_paths = sorted(glob.glob(os.path.join(self.config.digest_dir, "*.csv")))
        if not csv_paths:
            raise ValueError(f"no CSVs found in {self.config.digest_dir!r}")

        logger.info(f"Analyzing drift evolution across {len(csv_paths)} CSV(s) in "
                    f"{self.config.digest_dir}")
        out_path = LIADriftEvolutionCompiler(
            csv_paths, interval_s=self.config.interval_s, out_name=self.output_name,
        ).compile()
        logger.info(f"Plot saved to: {out_path}")
