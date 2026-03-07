"""
Noise Measurement using LIA setup.
"""

import csv
import os
import threading
import time

import ATE

from . import SetupBase


class NoiseMeasurement(SetupBase):
    def __init__(self, duration=500e-3) -> None:
        super().__init__()
        self.duration = duration

    @SetupBase.setup_ate
    def run(self):
        data_file = os.path.join(self.results_dir, 'noise_data.csv')

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU('SCU1', rm=self.rm) as scu:
            lia.reset()
            scu.reset()

            # Setup LIA for streaming
            # Assuming streaming commands, but SR860 supports VXI-11 streaming

            # Start daemon to capture data
            stop_event = threading.Event()
            def capture_data():
                with open(data_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['time', 'X', 'Y'])
                    start_time = time.time()
                    while not stop_event.is_set():
                        x, y = lia.snap(0, 1)
                        writer.writerow([time.time() - start_time, x, y])
                        time.sleep(0.01)  # 100 Hz

            thread = threading.Thread(target=capture_data)
            thread.start()

            time.sleep(self.duration)
            stop_event.set()
            thread.join()

        # Process data for PSD, but for now just save