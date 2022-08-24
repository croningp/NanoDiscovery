"""
.. module:: pH_module
    :synopsis: pH module using the Dr DAQ device to obtain pH values from a
                series of calibrations.
    :platform: Unix, Windows

.. moduleauthor:: Graham Keenan (Cronin Lab 2020).
"""

import time
import numpy as np
from typing import Tuple
from ._core import DrDAQDriver


def _init_driver() -> DrDAQDriver:
    """Initialise the Dr DAQ unit.

    Returns:
        DrDAQDriver: Dr DAQ unit
    """

    dvr = DrDAQDriver()

    # Set RGB to green
    dvr.set_rgb(0, 255, 0)

    return dvr


class DrDaqPHModule:
    """Dr DAQ pH meaurement device.
    Allows measurement of pH by fitting according to calibrations

    Args:
        calibrations (list, optional): Calibrations for the pH measurements.
    """

    def __init__(self, calibrations: list = [400., 700., 1000.]):
        self.driver = _init_driver()
        self.calibrations = calibrations

    def __del__(self):
        """Kill the connection to the device.
        """

        self.close_device()

    def close_device(self):
        """Close the connection to the device.
        """

        # Set RGB to red.
        self.driver.set_rgb(255, 0, 0)
        self.driver.close_unit()

    def update_calibrations(self, calibrations: list):
        """Update the current calibrations for the measurements.

        Args:
            calibrations (list): New calibrations
        """

        self.calibrations = calibrations

    def fit_measurement(self, value: float) -> float:
        """Fits the measurement based on calibrations.
        Converts the mV to human-readable pH values.

        Args:
            value (float): Measurement in mV.

        Returns:
            float: pH value of the measurement.
        """

        x = np.array(self.calibrations, dtype=np.float64)
        y = np.array([4., 7., 10.], dtype=np.float64)
        fit = np.polyfit(x, y, 1)

        return float(value) * fit[0] + fit[1]

    def measure_analog_values(self) -> Tuple[float]:
        """Obtains the analog readings from the pH driver

        Returns:
            Tuple[float]: Mean and Standard Deviation of analog readings
        """

        # Set RGB to blue to indicate we're currently measuring.
        self.driver.set_rgb(0, 0, 255)

        # Obtain measurement from the device.
        self.driver.run_single_shot()
        self.driver.sampling_done()
        time.sleep(1.)
        self.driver.sampling_done()

        # Obtain the raw sample form the device
        samples = self.driver.get_sampled_values()
        self.driver.stop_sampling()

        # Set RGB to green indicating that we're done
        self.driver.set_rgb(0, 0, 255)

        # Return mean and std dev of analog readings
        return np.mean(samples), np.std(samples)

    def measure_pH(self) -> float:
        """Obtain a pH measurement from the device.

        Returns:
            float: Measured pH value.
        """

        # Get the analog readings from the pH driver
        mean_samples, _ = self.measure_analog_values()

        # Convert the mV measurement to a pH value.
        return self.fit_measurement(mean_samples)
