"""Base module for interfacing with OceanOptics Spectrometers

.. moduleauthor:: Artem Leonov, Graham Keenan
"""
import time
import logging
import numpy as np
import seabreeze
seabreeze.use('cseabreeze')
import seabreeze.spectrometers as sb

# Spectrometer Types:
SPECS = {
    "UV": "2192",
    "RAMAN": "QE-PRO",
    "IR": "NIRQUEST"
}

class UnsupportedSpectrometer(Exception):
    """Exception for unsupported spectrometer types
    """


class NoSpectrometerDetected(Exception):
    """Exception for when no spectrometer is detected
    """


def _get_spectrometer(spec_type: str) -> str:
    """Gets the Spectrometer from Seabreeze that matches given type

    Arguments:
        spec_type {str} -- Type of spectrometer to look for

    Raises:
        UnsupportedSpectrometer -- If the spec_type is not present

    Returns:
        str -- Name of the spectrometer
    """

    devices = sb.list_devices()

    if not devices:
        raise NoSpectrometerDetected("Are the spectrometers plugged in?")
    if spec_type in SPECS.keys():
        for dev in devices:
            if SPECS[spec_type] in str(dev):
                return dev
    raise UnsupportedSpectrometer("Spectrometer {} unsupported!".format(spec_type))

class OceanOpticsSpectrometer():
    """Base class for interfacing with OceanOptics Spectrometers"""

    def __init__(self, spec_type, name=None):
        """
        Args:
            spec_type (str): The type of spectrometer, e.g. 'IR', 'raman', etc.
            name (str, optional): Device name for easier access
        """
        self.integration_time = 0.01 # in seconds
        self.__spec = _get_spectrometer(spec_type)
        self._spectrometer = sb.Spectrometer(self.__spec)
        self.name = name
        self._delay = 0.01

        self.logger = logging.getLogger('oceanoptics.spectrometer')
        self.logger.setLevel(logging.INFO)
        # Removing default handlers
        self.logger.handlers = []
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s ; %(module)s ; %(name)s ; %(message)s")
        ch.setFormatter(console_formatter)
        self.logger.addHandler(ch)
        self.set_integration_time(self.integration_time)

    def set_integration_time(self, integration_time):
        """Sets the integration time for the spectrometer

        Args:
            integration_time (float): Desired integration time in seconds!
        """

        self._spectrometer.open()
        self.integration_time = integration_time
        integration_time *= 1000 * 1000 # converting to microseconds
        self.logger.debug('Setting the integration time to %s microseconds', integration_time)
        self._spectrometer.integration_time_micros(integration_time)
        self._spectrometer.close()

    def scan(self, n=3):
        """Reads the spectrometer and returns the spectrum

        Args:
            n (int, opitonal): Number of 'scans'

        Returns:
            (Tuple): Tuple containing spectrum wavelengths and intensities as numpy arrays
                Example: (array(wavelengths), array(intensities))
        """

        i_mean = []
        self.logger.debug('Scanning')
        self._spectrometer.open()
        for i in range(n):
            wavelengths, intensities = self._spectrometer.spectrum()
            i_mean.append(intensities)
            time.sleep(self._delay)

        intensities = np.mean(i_mean, axis=0)
        self._spectrometer.close()
        return (wavelengths, intensities)
