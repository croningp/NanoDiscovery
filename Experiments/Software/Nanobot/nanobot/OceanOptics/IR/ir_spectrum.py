"""
.. module:: ir_spectrum
    :synopsis: Module for representing an IR spectrum
    :platforms: Unix, Windows

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

.. note:: Edit as needed, this is a skeletal implementation that can be improved
"""

import json
import time
import numpy as np
import matplotlib.pyplot as plt

def _write_json(data: dict, filename: str):
    """Write data out to a JSON file

    Args:
        data (dict): Data to write
        filename (str): Path to save JSON file
    """

    with open(filename, "w") as f_d:
        json.dump(data, f_d, indent=4)


def _load_json(filename: str) -> dict:
    """Loads a JSON file from disk

    Args:
        filename (str): Name of the file to load

    Returns:
        dict: JSON data
    """

    with open(filename) as f_d:
        return json.load(f_d)

def _ensure_serializable(data: dict) -> dict:
    """Ensures the output data is serializable

    Args:
        data (Dict): Data to check
    
    Returns:
        Dict: Serializable data
    """

    for k,v in data.items():
        if isinstance(v, np.ndarray):
            data[k] = v.tolist()
        elif isinstance(v, dict):
            data[k] = _ensure_serializable(v)
    return data

def trim_data(self, data: list, lower_range: int, upper_range: int) -> np.ndarray:
    """Trims data within a certain range
    Returns valid indexes that can be used to trim X and Y data

    Args:
        data (list): Data to trim within the range
        lower_range (int): Lower end of the range (Minimum value)
        upper_range (int): Upper end of the range (Maximum value)

    Returns:
        np.ndarray: Indexes to use for trimming data
    """

    above_ind = np.array(data) > lower_range
    below_ind = np.array(data) < upper_range

    return np.logical_and(above_ind, below_ind)


class IRSpectrum:
    """Class representing an IR spectrum.
    Spectrum can be a reference spectrum or a measured spectrum

    Args:
        wavelengths (list): Wavelengths of the spectrum
        intensities (list): Intensities of the spectrum
        ref (dict, optional): Reference spectrum if available
    """

    def __init__(self, wavelengths: list, intensities: list, ref: dict = {}):
        self.wavelengths = wavelengths
        self.intensities = intensities
        self.reference = ref
        self.wavenumbers = []
        self.transmittance = []

        if self.reference:
            self.convert_intensities_to_transmittance()
            self.convert_wavelength_to_wavenumber()


    @classmethod
    def load_spectrum(cls, filepath: str):
        """Class method for loading spectrum data from a file

        Args:
            filepath (str): Path to  spectrum data

        Returns:
            IRSpectrum: IRSpectrum with spectral data from file
        """

        data = _load_json(filepath)
        return cls(data["wavelength"], data["intensities"], ref=data["reference"])


    def convert_intensities_to_transmittance(self):
        """Converts intensities to transmittance
        """

        self.transmittance = list(reversed([
            (s / r) * 100 for (s, r) in zip(self.intensities, self.reference["intensities"])
        ]))


    def convert_wavelength_to_wavenumber(self):
        """Converts Wavelengths to Wavenumbers
        """

        self.wavenumbers = list(reversed([
            (10 ** 7) / nm for nm in self.wavelengths
        ]))


    def plot_spectrum(
        self,
        display: bool = False,
        savepath: str = "",
        limits: tuple = ()
    ):
        """Plots the spectral data

        Args:
            display (bool, optional): Display the spectrum on screen. Defaults to False.
            savepath (str, optional): Path to save the spectrum graph to disk. Defaults to "".
        """

        # Clear any previous plots/data
        plt.clf()
        plt.cla()

        # TODO::GAK -- Implement limit checks

        # Already have a reference set, measured spectrum
        if self.reference:
            plt.xlabel("Wavenumber (cm-1)")
            plt.ylabel("Transmittance (%)")
            plt.title("IR Spectrum")
            plt.plot(
                self.wavenumbers,
                self.transmittance,
                color="black",
                linewidth=0.5
            )

        # No reference set, reference spectrum
        else:
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Intensities")
            plt.title("Reference IR Spectrum")
            plt.plot(
                self.wavelengths,
                self.intensities,
                color="black",
                linewidth=0.5
            )

        # Set limits after plotting
        plt.gca().set_ylim(bottom=0)

        # Save plot to disk
        if savepath:
            plt.savefig(savepath)

        # Display the plot on screen
        if display:
            plt.show()


    def dump_spectrum(self, filename: str):
        """Dump spectral data out to disk

        Args:
            filename (str): Path to save file (JSON)
        """

        out = {
            "wavenumbers": self.wavenumbers,
            "transmittance": self.transmittance,
            "wavelength": self.wavelengths,
            "intensities": self.intensities,
            "reference": self.reference,
            "timestamp": time.strftime("%d_%m_%Y_%H:%M:%S")
        }

        out = _ensure_serializable(out)

        _write_json(out, filename)
