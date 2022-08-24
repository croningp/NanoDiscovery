import time
from typing import Dict, List
from .DrDAQ.pH_module import DrDaqPHModule

class DrDAQDriver:
    def __init__(self, calibrations: Dict[str, float]):
        self.driver = DrDaqPHModule(calibrations=list(calibrations.values()))

    @property
    def calibrations(self):
        return self.driver.calibrations

    def update_calibrations(self, calibrations: List[float]):
        """Updates the pH calibrations of the pH driver

        Args:
            calibrations (List[float]): Calibrations for the driver
        """

        self.driver.update_calibrations(calibrations)

    def measure_raw_value(self) -> float:
        """Measures the raw value in mV from DrDAQ

        Returns:
            float: Raw value in mV
        """

        # Just take the mean, ignore stddev
        mean, _ = self.driver.measure_analog_values()

        return mean

    def measure_pH(self, threshold: float = 0.5, max_time: float = 10) -> float:
        """Measures the pH until it is stable

        Args:
            threshold (float, optional): Change threshold between readings.
            Defaults to 0.5.

            max_time (float, optional): Max time to sample for. Defaults to 10.

        Returns:
            float: Measured pH
        """

        # Log start time and current pH
        start_time = time.time()
        current_reading = self.driver.measure_pH()

        # Run until stable or timeout reached
        while (time.time() - start_time) < max_time:
            # Get the next reading and keep old reading
            prev_reading = current_reading
            current_reading = self.driver.measure_pH()

            # pH is stable, break out
            if abs(current_reading - prev_reading) < threshold:
                break

        # Get the measured signal by comparing current and previous reading
        signal = (current_reading + prev_reading) / 2

        # Return the measured pH
        return signal
