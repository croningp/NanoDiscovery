import pickle
import os
import logging

from abc import ABC, abstractmethod

import numpy as np
import matplotlib.pyplot as plt

from scipy import (sparse,
                   signal,
                   interpolate,
                   integrate,
                   )

from .utils import interpolate_to_index, find_nearest_value_index


class AbstractSpectrum(ABC):
    """General class for handling spectroscopic data

    Contains methods for data manipulation (load/save) and basic processing
    features, such as baseline correction, smoothing, peak picking and
    integration.

    All data processing happens in place!
    """

    # for plotting
    AXIS_MAPPING = {
        'x': 'x_data',
        'y': 'y_data',
    }

    # list of properties to be saved
    PUBLIC_PROPERTIES = {
        'x',
        'y',
        'peaks',
        'timestamp',
    }

    # list of internal properties to be dumped during new data loading
    INTERNAL_PROPERTIES = {
        'baseline',
    }

    def __init__(self, path=None, autosaving=True):
        """Default constructor, loads properties into instance namespace.

        Can be redefined in ancestor classes.

        Args:
            path (Union[str, bool], optional): Valid path to save data to.
                If omitted, uses ".//spectrum". If False - no folder created.
            autosaving (bool, optional): If the True (default) will save the
                spectrum when the new one is loaded. Will drop otherwise.
        """

        self.autosaving = autosaving

        # loading public properties
        for prop in self.PUBLIC_PROPERTIES:
            setattr(self, prop, None)

        # loading internal properties
        for prop in self.INTERNAL_PROPERTIES:
            setattr(self, prop, None)

        # creating data path
        if path is None:
            self.path = os.path.join('.', 'spectrum')
            os.makedirs(self.path, exist_ok=True)
        else:
            try:
                os.makedirs(path, exist_ok=True)
                self.path = path
            except TypeError: # type(path) -> bool
                self.path = '.'

        # creating logger
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(self.__class__.__name__)

    def _dump(self):
        """Dummy method to dump all spectral data. Used before loading new data.
        """

        self.__init__(path=self.path, autosaving=self.autosaving)

    @abstractmethod
    def load_spectrum(self, x, y, timestamp):
        """Loads the spectral data.

        This method must be redefined in ancestor classes.

        Args:
            x (:obj: np.array): An array with data to be plotted as "x" axis.
            y (:obj: np.array): An array with data to be plotted as "y" axis.
            timestamp (float): Timestamp to the corresponding spectrum.
        """

        try:
            assert x.shape == y.shape
        except AssertionError:
            raise ValueError('X and Y data must have same dimension.') from None

        if self.x is not None:
            if self.autosaving:
                self.save_data()
            self._dump()

        self.x = x
        self.y = y
        self.timestamp = timestamp

    def save_data(self, filename=None, verbose=False):
        """Saves the data to given path using python pickle module.

        Args:
            filename (str, optional): Filename for the current spectrum. If
                omitted, using current timestamp.
            verbose (bool, optional): If all processed data needs to be saved as
                well. Default: False.
        """
        if filename is None:
            filename = f'{self.timestamp}.pickle'
        else:
            # file extension used from python 3. documentation
            filename += '.pickle'

        path = os.path.join(self.path, filename)

        data = {
            prop: self.__dict__[prop]
            for prop in self.PUBLIC_PROPERTIES
            if self.__dict__[prop] is not None
        }

        if verbose:
            data.update({
                prop: self.__dict__[prop]
                for prop in self.INTERNAL_PROPERTIES
                if self.__dict__[prop] is not None
            })

        with open(path, 'wb') as f:
            pickle.dump(data, f)

        self.logger.info('Saved in %s', path)

    def load_data(self, path):
        """Loads the data from saved pickle file.

        Data is loaded in place, so instance attributes are overwritten.

        Args:
            path (str): Valid path to pickle file.
        """

        if self.x is not None:
            self._dump()

        # TODO add exception handling
        with open(path, 'rb') as f:
            data = pickle.load(f)

        self.__dict__.update(data)

    def trim(self, xmin, xmax, in_place=True):
        """Trims the spectrum data within specific X region

        Args:
            xmin (int): Minimum position on the X axis to start from.
            xmax (int): Maximum position on the X axis to end to.
            in_place (bool): If trimming happens in place, else returns new
                array as trimmed copy.

        Returns:
            (bool): True if trimmed in place.
            (Tuple[np.array, np.array]): Trimmed copy of the original array as
                tuple with X and Y points respectively.
        """

        # Creating the mask to map arrays
        above_ind = self.x > xmin
        below_ind = self.x < xmax
        full_mask = np.logical_and(above_ind, below_ind)

        # Mapping arrays if they are supplied
        if in_place:
            self.y = self.y[full_mask]
            self.x = self.x[full_mask]
            if self.baseline is not None and self.baseline.shape == full_mask.shape:
                self.baseline = self.baseline[full_mask]
            return True
        else:
            return (self.x.copy()[full_mask], self.y.copy()[full_mask])

    def show_spectrum(
            self,
            filename=None,
            title=None,
            label=None,
    ):
        """ Plots the spectral data using matplotlib.pyplot module.

        Args:
            filename (str, optional): Filename for the current plot. If omitted,
                file is not saved.
            title (str, optional): Title for the spectrum plot. If omitted, no
                title is set.
            label (str, optional): Label for the spectrum plot. If omitted, uses
                the spectrum timestamp.
        """
        if label is None:
            label = f'{self.timestamp}'

        fig, ax = plt.subplots(figsize=(12, 8))

        ax.plot(
            self.x,
            self.y,
            color='xkcd:navy blue',
            label=label,
        )

        ax.set_xlabel(self.AXIS_MAPPING['x'])
        ax.set_ylabel(self.AXIS_MAPPING['y'])

        if title is not None:
            ax.set_title(title)

        # plotting peaks if found
        if self.peaks is not None:
            plt.scatter(
                self.peaks[:, 1],
                self.peaks[:, 2],
                label='found peaks',
                color='xkcd:tangerine',
            )

        ax.legend()

        if filename is None:
            fig.show()

        else:
            path = os.path.join(self.path, 'images')
            os.makedirs(path, exist_ok=True)
            fig.savefig(os.path.join(path, f'{filename}.png'), dpi=150)

    def find_peaks(self, threshold=0.1, min_width=2, min_dist=None, area=None):
        """Finds all peaks above the threshold with at least min_width width.

        Args:
            threshold (float, optional): Relative peak height with respect to
                the highest peak.
            min_width (int, optional): Minimum peak width.
            min_dist (int, optional): Minimum distance between peaks.
            area (Tuple(int, int), optional): Area to search peaks in. Supplied
                as min, max X values tuple.

        Return:
            (:obj: np.array): An array of peaks ids as rounded peak_x coordinate
                value. If searching within specified area, full peak information
                matrix is returned, see below for details.

        Also updates the self.peaks attrbiute (if "area" is omitted) as:
            (:obj: np.array): An (n_peaks x 5) array with peak data as columns:
                peak_id (float): Rounded peak_x coordinate value.
                peak_x (float): X-coordinate for the peak.
                peak_y (float): Y-coordinate for the peak.
                peak_left_x (float): X-coordinate for the left peak border.
                peak_right_x (float): X-coordinate for the right peak border.

        Peak data is accessed with indexing, e.g.:
            self.peaks[n] will give all data for n's peak
            self.peaks[:, 2] will give Y coordinate for all found peaks
        """

        # only dumping if area is omitted
        if self.peaks is not None and not area:
            self.peaks = None

        # trimming
        if area is not None:
            spec_y = self.trim(area[0], area[1], False)[1]
        else:
            spec_y = self.y.copy()

        threshold *= (self.y.max() - self.y.min())
        peaks, _ = signal.find_peaks(
            spec_y,
            height=threshold,
            width=min_width,
            distance=min_dist
        )

        # obtaining width for full peak height
        # TODO deal with intersecting peaks!
        # TODO deal with incorrect peak width
        pw = signal.peak_widths(spec_y, peaks, rel_height=0.95)

        # converting all to column vectors by adding extra dimension along 2nd
        # axis. Check documentation on np.newaxis for details
        peak_xs = self.x.copy()[peaks][:, np.newaxis]
        peak_ys = self.y.copy()[peaks][:, np.newaxis]
        peaks_ids = np.around(peak_xs)
        peaks_left_ids = interpolate_to_index(self.x, pw[2])[:, np.newaxis]
        peaks_right_ids = interpolate_to_index(self.x, pw[3])[:, np.newaxis]

        if area is None:
            # updating only if area is not specified
            self.peaks = np.hstack((
                peaks_ids,
                peak_xs,
                peak_ys,
                peaks_left_ids,
                peaks_right_ids,
            ))
            return peaks_ids

        return np.hstack((
            peaks_ids,
            peak_xs,
            peak_ys,
            peaks_left_ids,
            peaks_right_ids,
        ))

    def correct_baseline(self, lmbd=1e3, p=0.01, n_iter=10):
        """Generates and subtracts the baseline for the given spectrum.

        Based on Eilers, P; Boelens, H. (2005): Baseline Correction with
            Asymmetric Least Squares Smoothing.

        Default values chosen arbitrary based on processing Raman spectra.

        Args:
            lmbd (float): Arbitrary parameter to define the smoothness of the
                baseline the larger lmbd is, the smoother baseline will be,
                recommended value between 1e2 and 1e5.
            p (float): An asymmetric least squares parameter to compute the
                weights of the residuals, chosen arbitrary, recommended values
                between 0.1 and 0.001.
            n_iter (int, optional): Number of iterations to perform the fit,
                recommended value between 5 and 10.
        """

        # generating the baseline first
        L = len(self.y)
        D = sparse.csc_matrix(np.diff(np.eye(L), 2))
        w = np.ones(L)
        for _ in range(n_iter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lmbd * D.dot(D.transpose())
            z = sparse.linalg.spsolve(Z, w * self.y)
            w = p * (self.y > z) + (1 - p) * (self.y < z)

        # updating attribute for future use
        self.baseline = z

        # subtracting the baseline
        # TODO update peak coordinates if peaks were present
        self.y -= z
        self.logger.info('Baseline corrected')

    def integrate_area(self, area, rule='trapz'):
        """Integrate the spectrum within given area

        Args:
            area (Tuple[float, float]): Tuple with left and right border (X axis
                obviously) for the desired area.
            rule (str): Method for integration, "trapz" - trapezoidal
                rule (default), "simps" - Simpson's rule.
        Returns:
            float: Definite integral within given area as approximated by given
                method.
        """

        # closest value in experimental data and its index in data array
        _, left_idx = find_nearest_value_index(self.x, area[0])
        _, right_idx = find_nearest_value_index(self.x, area[1])

        if rule == 'trapz':
            return integrate.trapz(
                self.y[left_idx:right_idx+1],
                self.x[left_idx:right_idx+1]
            )

        elif rule == 'simps':
            return integrate.simps(
                self.y[left_idx:right_idx+1],
                self.x[left_idx:right_idx+1]
            )

        else:
            raise ValueError('Only trapezoidal "trapz" or Simpson\'s "simps" \
rules are supported!')

    def integrate_peak(self, peak, rule='trapz'):
        """Calculate an area for a given peak

        Args:
            peak (float): (rounded) peak Y coordinate. If precise peak position
                was not found, closest is picked.
            rule (str): Method for integration, "trapz" - trapezoidal
                rule (default), "simps" - Simpson's rule.
        Returns:
            float: Definite integral within given area as approximated by given
                method.
        """

        if self.peaks is None:
            self.find_peaks()

        true_peak, idx = find_nearest_value_index(self.peaks[:, 0], peak)
        _, _, _, left, right = self.peaks[idx]

        self.logger.debug('Integrating peak found at %s, borders %.02f-%.02f',
                          true_peak, left, right)

        return self.integrate_area((left, right), rule=rule)

    def smooth_spectrum(self, window_length=15, polyorder=7, in_place=True):
        """Smoothes the spectrum using Savitsky-Golay filter.

        For details see scipy.signal.savgol_filter.

        Default values for window length and polynomial order were chosen
        arbitrary based on Raman spectra.

        Args:
            window_length (int): The length of the filter window (i.e. the
                number of coefficients). window_length must be a positive odd
                integer.
            polyorder (int): The order of the polynomial used to fit the
                samples. polyorder must be less than window_length.
            in_place (bool, optional): If smoothing happens in place, returns
                smoothed spectrum if True.
        """

        if in_place:
            self.y = signal.savgol_filter(
                self.y,
                window_length=window_length,
                polyorder=polyorder
            )
            return True

        return signal.savgol_filter(
            self.y,
            window_length=window_length,
            polyorder=polyorder,
        )

    def default_processing(self):
        """Dummy method to return spectral data.

        Normally redefined in ancestor classes to include basic processing for
            specific spectrum type.

        Returns:
            Tuple[np.array, np.array, float]: Spectral data as X and Y
                coordinates and a timestamp.
        """

        return self.x, self.y, self.timestamp

    @classmethod
    def from_data(cls, data):
        """ Class method to instantiate the class from the saved data file.

        Args:
            data (str): Path to spectral data file (as pickle).

        Returns:
            New instance with all data inside.
        """

        if 'pickle' not in data:
            raise AttributeError('Only .pickle files are supported')

        path = os.path.abspath(os.path.dirname(data))

        spec = cls(path)
        spec.load_data(data)

        return spec

    def copy(self):
        """ Dummy class to return a new instance with the same data as the
        current.

        Returns:
            (:obj:SpinsolveNMRSpectrum): New object with the same data.
        """

        # creating new instance
        spec = self.__class__(self.path, self.autosaving)

        # loading attributes
        for prop in self.PUBLIC_PROPERTIES.union(self.INTERNAL_PROPERTIES):
            setattr(spec, prop, getattr(self, prop))

        return spec
