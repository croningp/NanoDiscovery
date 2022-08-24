"""
Module for handling Raman spectroscopic data

.. moduleauthor:: Artem Leonov, Graham Keenan
"""
import logging
import os

import numpy as np
from scipy import signal

from ...analysis import AbstractSpectrum
from ...analysis.utils import interpolate_to_index

LASER_POWER = 785

MIN_X = 780
MAX_X = 1006

def _convert_wavelength_to_wavenumber(data):
    """Converts x from spectrometer to Raman shift in wavenumbers

    Arguments:
        data (iterable): Wavelength data to convert

    Returns:
        (:obj: np.array): Wavenumbers data
    """

    wavenumbers = [(10**7 / LASER_POWER) - (10**7 / wv) for wv in data]

    return np.array(wavenumbers)

class RamanSpectrum(AbstractSpectrum):
    """Defines methods for Raman spectroscopic data handling

    Args:
        path(str, optional): Valid path to save the spectral data.
            If not provided, uses .//raman_data
    """

    AXIS_MAPPING = {
        'x': 'wavelength',
        'y': 'intensities',
    }

    INTERNAL_PROPERTIES = {
        'reference',
        'original',
        'baseline',
    }

    def __init__(self, path=None, autosaving=True):

        if path is not None:
            path = os.path.join('.', 'raman_data')

        self.logger = logging.getLogger(
            'oceanoptics.spectrometer.raman.spectrum')

        super().__init__(path, autosaving)

    def find_peaks_iteratively(self, limit=10, steps=100):
        """Finds all peaks iteratively moving the threshold

        Args:
            limit (int): Max number of peaks found at each iteration to stop
                after.
            steps (int): Max number of iterations.
        """

        gradient = np.linspace(self.y.max(), self.y.min(), steps)
        pl = [0,] # peaks length

        # Looking for peaks and decreasing height
        for i, n in enumerate(gradient):
            peaks, _ = signal.find_peaks(self.y, height=n)
            pl.append(len(peaks))
            diff = pl[-1] - pl[-2]
            if diff > limit:
                self.logger.debug('Stopped at iteration %s, with height %s, \
diff - %s', i+1, n, diff)
                break

        # Final peaks at previous iteration
        peaks, _ = signal.find_peaks(self.y, height=gradient[i-1])

        # Updating widths
        pw = signal.peak_widths(self.y, peaks, rel_height=0.95)
        peak_xs = self.x.copy()[peaks][:, np.newaxis]
        peak_ys = self.y.copy()[peaks][:, np.newaxis]
        peaks_ids = np.around(peak_xs)
        peaks_left_ids = interpolate_to_index(self.x, pw[2])[:, np.newaxis]
        peaks_right_ids = interpolate_to_index(self.x, pw[3])[:, np.newaxis]

        # Packing for peak array
        self.peaks = np.hstack((
            peaks_ids,
            peak_xs,
            peak_ys,
            peaks_left_ids,
            peaks_right_ids,
        ))

        return peaks_ids

    def load_spectrum(self, spectrum, timestamp, reference=False):
        """Loads the spectral data

        Args:
            spectrum (tuple): Tuple containing spectrum x and y as numpy arrays.
                Example: (array(x), array(y))
            timestamp (float): time.time() for the measured spectra
            reference (bool, optional): True if the supplied spectra should be
                stored as a reference (background)
        """

        super().load_spectrum(spectrum[0], spectrum[1], timestamp)
        self.original = spectrum[1]
        if reference:
            self.reference = spectrum[1]

    def subtract_reference(self):
        """Subtracts reference spectrum and updates the current one"""

        if self.reference is None:
            raise ValueError('Please upload the reference first')

        self.y -= self.reference

    def default_processing(self):
        """Dummy method for quick processing. Returns spectral data!"""

        self.correct_baseline()
        self.smooth_spectrum()
        self.find_peaks_iteratively()

        return self.x, self.y, self.timestamp
