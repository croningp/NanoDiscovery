"""
.. module:: uv_spectrum
    :synopsis: Module representing a UV spectrum
    :platforms: Unix, Windows

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

.. note:: Feel free to edit. This is a skeletal implementation.

"""

import time
import json
import numpy as np
import matplotlib.pyplot as plt


def _write_json(data: dict, filename: str):
    """Writes out data to a JSON file

    Args:
        data (dict): Data to write
        filename (str): Path to save to
    """

    with open(filename, "w") as f_d:
        json.dump(data, f_d, indent=4)


def _load_json(filename: str) -> dict:
    """Load  JSON file from disk

    Args:
        filename (str): Path to JSON file

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


def trim_data(data: list, lower_range: int, upper_range: int) -> np.ndarray:
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


class UVSpectrum:
    """Class representing a UV spectrum.
    Spectrum can be a reference spectrum or measured spectrum.

    Args:
        wavelengths (list): Wavelengths of the spectrum
        intensities (list): Intensities of the spectrum
        ref (dict): Reference spectrum data (Defaults to {})

    """

    def __init__(self, wavelengths: list, intensities: list, ref: dict = {}):
        self.wavelengths = np.array(wavelengths)
        self.intensities = np.array(intensities)
        self.reference = ref
        self.absorbances = []
        self.max_peak = 0

        # If we have a reference, generate absorbances using Beer-Lambert relation
        if self.reference:
            self.beer_lambert()


    @classmethod
    def load_spectrum(cls, filepath: str):
        """Class method for loading spectrum data from file

        Args:
            filepath (str): Path to spectrum JSON file

        Returns:
            UVSpectrum: UVSpectrum instance
        """

        data = _load_json(filepath)
        return cls(data["wavelength"], data["intensities"], ref=data["reference"])


    def beer_lambert(self):
        """Beer-Lambert relation.
        Converts intensities to absorbances for a UV spectrum
        """

        for ref, measured in zip(self.reference["intensities"], self.intensities):
            try:
                if ref == 0 or measured == 0:
                    continue
                self.absorbances.append(np.log10(ref / measured))
            except Exception:
                break

        # Set absorbances
        self.absorbances = np.array(self.absorbances)

        # Find the maximum peak
        self.max_peak = self.wavelengths[np.argmax(self.absorbances)]


    def plot_spectrum(
        self,
        display: bool = False,
        legend: bool = False,
        savepath: str = "",
        limits: tuple = ()
    ):
        """Plot spectrum.

        Args:
            display (bool, optional): Display the spectra on screen. Defaults to False.
            legend (bool, optional): Display a legend or not for maximum peak. Defaults to False.
            savepath (str, optional): Path to save the image to. Defaults to "".
            limits (tuple, optional): Trims data within a certain range. Defaults to ().
        """

        # Clear any previous plots/data
        plt.clf()
        plt.cla()

        # Set X label
        plt.xlabel("Wavelength (nm)")

        # Trim data within a certain range
        if limits:
            trimmed = trim_data(self.wavelengths, *limits)
            self.wavelengths = self.wavelengths[trimmed]
            self.intensities = self.intensities[trimmed]

            # Trim absorbances if they're present
            if len(self.absorbances) > 0:
                self.absorbances = self.absorbances[trimmed]


        # Display different labels for Measured spectrum
        # We have a reference spectrum already, means this is a measured sample
        if self.reference:
            plt.ylabel("Absorbances")
            plt.title("UV/Vis Reference Spectrum")
            plt.plot(self.wavelengths, self.absorbances, color="black", linewidth=0.5)

        # Display different labels for Reference
        # No reference means this should be a reference
        else:
            plt.ylabel("Intensities")
            plt.title("UV/Vis Spectrum")
            plt.plot(self.wavelengths, self.intensities, color="black", linewidth=0.5)

        # Display legend
        if legend:
            leg_label = f"Maximum Peak: {self.max_peak:.2f}nm"
            plt.vlines(
                x=self.max_peak,
                ymin=0,
                ymax=max(self.absorbances),
                color="g",
                zorder=3,
                label=leg_label
            )
            leg = plt.legend()
            for legobj in leg.legendHandles:
                legobj.set_linewidth(5.0)

        # Set limits after plotting
        plt.gca().set_ylim(bottom=0)

        # Save if savepath is defined
        if savepath:
            plt.savefig(savepath)

        # SHow the spectrum on screen
        if display:
            plt.show()


    def dump_spectrum(self, filename: str):
        """Dump spectrum data to JSON file

        Args:
            filename (str): Path to save JSON file
        """

        out = {
            "wavelength": self.wavelengths,
            "absorbances": self.absorbances,
            "intensities": self.intensities,
            "reference": self.reference,
            "max_peak": self.max_peak,
            "timestamp": time.strftime("%d_%m_%Y_%H:%M:%S")
        }

        out = _ensure_serializable(out)

        _write_json(out, filename)
