"""
.. module:: spectra_analyser
    :platform: Unix
    :synopsis: Analyses spectra in order to obtain a shape metric

.. moduleauthor:: Yibin Jiang (Cronin Lab 2020)

"""

# System Imports
from typing import Dict, Tuple

# Platform Imports
import nanobot.constants as cst

# Libraries
import numpy as np
import scipy.signal as signal
from scipy.interpolate import interp1d
from scipy.signal import find_peaks, peak_widths, peak_prominences


def low_pass_filter(
    wavelengths: np.array, intensities: np.array, freq: int
) -> np.array:
    """Perform a low pass filter over the wavelength and intensity data

    Args:
        wavelengths (np.array): Wavelengths (nm)
        intensities (np.array): Intensities (arbitary)
        freq (int): Frequency

    Returns:
        np.array: Filtered data
    """

    samp_freq = wavelengths.shape[0]  # Sampling frequency
    w = freq / (samp_freq / 2)  # Normalise frequency

    b, a = signal.butter(5, w, 'low')
    series = signal.filtfilt(b, a, intensities)

    return series


def obtain_prominance(
    x: float, a: float = 1.0, b: float = 70.0, c: float = 0.4
) -> float:
    """Obtains the prominance of a peak. More sensitive when X is small.

    Args:
        x (float): Tuning Parameter
        a (float, optional): Tuning Parameter. Defaults to 1.0.
        b (float, optional): Tuning Parameter. Defaults to 70.0.
        c (float, optional): Tuning Parameter. Defaults to 0.4.

    Returns:
        float: Peak Prominance
    """

    return (
        (np.tanh((x - 0.05) * 100) + 1) / 2 * 0.2
        if x < 0.05 else
        (a * x + c * (1 / (1 + np.exp(-b * x)) - 1 / 2)) / 1.2
    )


def peak_binary(
    prominence: float, b: float = 100.0, threshold: float = 0.05
) -> float:
    """Binarise a peak according to its prominence

    Args:
        x (float): X

    Returns:
        float: Peak binary
    """
    return (np.tanh((prominence - threshold) * b) + 1) / 2


def normalise_data(series_data: np.array) -> np.array:
    """Normalises data between the min and max of thje series

    Args:
        series_data (np.array): Series data

    Returns:
        np.array: Normalised data
    """
    return (
        (series_data - np.min(series_data))
        / (np.max(series_data) - np.min(series_data))
    )


def calculate_smoothness(x: np.array) -> float:
    """Calculate smoothness of data

    Args:
        x (np.array): Data input

    Returns:
        float: Smoothness
    """

    return np.std(np.diff(x)) / abs(np.mean(np.diff(x)))


def process_spectrum(
    self, data: Dict, freq: int = 8
) -> Tuple[np.array, np.array]:
    """Processes a spectrum to obtain an interpolated spectrum and
    assess the quality of the data

    Args:
        data (Dict): Spectral data
        freq (int): Filter frequency

    Returns:
        Tuple[np.array, np.array]: Interpolated UV & Quality of spectrum
    """

    # Get spectrum data
    ref = data[cst.REFERENCE]

    # Reference wavelengths
    ref_wv = np.array(ref[cst.WAVELENGTH])

    # Wavelength and absorbances of samples
    wavelengths, absorbance = (
        np.array(data[cst.WAVELENGTH]), np.array(data[cst.ABSORBANCE])
    )

    # Trim absorbances
    absorbance = normalise_data(
        absorbance[ref_wv > cst.UV_LIMITS[0] & ref_wv < cst.UV_LIMITS[1]]
    )

    # Get normalised filtered data
    filter_abs = low_pass_filter(wavelengths, absorbance, freq=freq)
    normalised_absorbance = normalise_data(filter_abs)

    # Calculate the quality of the spectrum
    quality = abs(normalised_absorbance - absorbance).mean()

    # Get interpolated UV
    interpolated_uv = interp1d(
        wavelengths, normalised_absorbance, kind='cubic'
    )

    return interpolated_uv, quality


def obtain_metrics(
    seed_data: Dict, sample_data: Dict
) -> Tuple[np.array, float]:
    """Obtain a series of scores for the given spectra

    Scores:
        score1: Multiplied peak prominences with corresponding peak
                positions and sum the result.
        score2: Averaged value of prominences * peak position
        score3: Dot product of seed and sample UV-Vis
        score4: Wavelength at which dot product and seed UV-Vis is maximised
        score5: Summation of processed prominences

    Args:
        seed_data (Dict): Seed data
        sample_data (Dict): Sample data

    Returns:
        Tuple[np.array, float]: Scores and half-width
    """

    # Declare scores
    score1, score2, score3, score4, score5 = 0, 0, 0, 0, 0

    # Process the UV of the seed
    seed_uv, _ = process_spectrum(seed_data)

    # Process the UV of the sample
    sample_uv, quality = process_spectrum(sample_data)
    wavelengths = np.linspace(*cst.UV_LIMITS)

    # Get the series data of the sample and seed
    series = sample_uv(wavelengths)
    series_seed = seed_uv(wavelengths)

    # Calculate dot product
    score3 = np.dot(series_seed, series)

    # Get the peak positions and prominance of the peaks for the sample
    peaks, _ = find_peaks(series, prominence=0)
    prominences = peak_prominences(series, peaks)[0]

    # Calculate half-width maxiuma
    half_width = peak_widths(series, peaks, rel_height=0.5)

    # Iterate through each peak
    for pos, _ in enumerate(peaks):
        # Get the prominance
        peak_prominence = prominences[pos]

        # Calculate score1 and score5
        score1 += (
            obtain_prominance(peak_prominence) * wavelengths[peaks[pos]]
        )
        score5 += obtain_prominance(peak_prominence)

    # Score5 valid, calculate score2
    if score5 != 0:
        score2 = score1 / score4

    # Score 4: Distance observed from seed
    corr = np.correlate(series, series_seed, 'full')
    score4 = (corr.argmax() - len(corr) - 1) / 2

    # Return scores and half-width maxima
    return np.array([score1, score2, score3, score4, score5]), half_width
