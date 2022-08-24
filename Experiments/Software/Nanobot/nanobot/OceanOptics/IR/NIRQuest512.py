"""
.. module:: NIRQuest512
    :synopsis: Module representing the NIRQUest512 Near-IR spectrometer
    :platforms: Unix, Windows

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

.. note:: Edit as needed. This is a skeletal implementation for minimal
            functionality.

"""

import json
from pathlib import Path
from typing import Union, Dict
from .ir_spectrum import IRSpectrum
from ..oceanoptics import OceanOpticsSpectrometer

class NoReferenceException(Exception):
    """Exception for calling spectrum without a reference
    """

class NIRQuest512(OceanOpticsSpectrometer):
    """Class representing the NIRQuest512 Near-IR spectrometer

    Inherits:
        OceanOpticsSpectrometer
    """

    def __init__(self):
        super().__init__("IR", name="NIRQuest512 IR Spectrometer")
        self.reference = {}
        self.__ref_called = False

    def load_reference(self, ref: Union[str, Dict]):
        """Loads a pre-existing reference from disk or from dict.

        Args:
            ref (Union[str, Dict]): Reference as either a dictionary
            or JSON filepath
        """

        # Filepath, load and set
        if isinstance(ref, str) or isinstance(ref, Path):
            with open(ref) as fd:
                self.reference = json.load(fd)
                self.__ref_called = True

        # Dict, set
        elif isinstance(ref, dict):
            self.reference = ref
            self.__ref_called = True
        
        # Not supported
        else:
            self.logger.warning(
                f'Reference {ref} is unsupported. Not loading'
            )

    def obtain_reference_spectrum(self) -> IRSpectrum:
        """Obtain a reference spectrum

        Returns:
            IRSpectrum: Reference IR spectrum
        """

        wavelength, intensities = self.scan()
        self.reference["wavelength"] = wavelength
        self.reference["intensities"] = intensities
        self.__ref_called = True

        return IRSpectrum(wavelength, intensities)

    def obtain_spectrum(self) -> IRSpectrum:
        """Obtain an IR spectrum of a sample.

        Raises:
            NoReferenceException: Attempting to measure a sample without#
            reference data.

        Returns:
            IRSpectrum: Sample IR spectrum.
        """

        if not self.__ref_called:
            raise NoReferenceException(
                "Attempting to call a spectrum without a valid reference."
            )

        wavelength, intensities = self.scan()
        return IRSpectrum(wavelength, intensities, ref=self.reference)
