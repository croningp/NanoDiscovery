"""
.. module:: drdaq_driver
    :synopsis: Driver for interfacing with the Dr DAQ Picoscope for pH
    measurements

    :platforms: Unix, Windows

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

.. note:: Code is adapted from code written by Abhishek Sharma (Cronin Lab 2018)

"""

import sys
import ctypes
import logging
import numpy as np

def _load_library() -> ctypes.CDLL:
    """Loads the appropriate library for USB Dr DAQ dependent on operating
    system.

    Raises:
        NotImplementedError: Not implemented because no idea where the Windows
        DLL is stored.

        OSError: Operating system is not supported (macOS).

    Returns:
        Union[ctypes.CDLL, ctypes.WinDLL]: Loaded USB Dr DAQ library
    """

    # Load for Windows
    if "win" in sys.platform:
        bit = " (x86)" if sys.platform == "win32" else ""
        windows_path = (
            f"C:\\Program Files{bit}\\Pico Technology\\SDK\\lib\\usbdrdaq.dll"
        )
        return ctypes.windll.LoadLibrary(windows_path)

    # Load for Linux
    elif sys.platform == "linux":
        return ctypes.cdll.LoadLibrary("/opt/picoscope/lib/libusbdrdaq.so")

    # MacOS
    else:
        raise OSError("OS is not supported for USB Dr DAQ!")


class DrDAQDriver:
    """Driver for the USB Dr DAQ Picoscope for pH measurements
    """

    def __init__(self):
        # Set the appropriate variables for measurements
        self.recording_block = ctypes.c_int16(200000)
        self.no_of_samples = ctypes.c_int16(20000)
        self.channel = ctypes.c_int16(5)
        self.no_of_active_channels = ctypes.c_int16(1)
        self.measurement_results = (ctypes.c_short * 20000)()

        # Load the library
        self.lib = _load_library()

        # Create a logger
        self.logger = logging.getLogger("DrDAQDriver")

        # Open the Dr DAQ unit to obtain the handler
        self.handle = self.open_unit()

        # Set the interval for scanning
        self.set_DAQ_interval()

        # Enable control of the RGB LED
        self.enable_rgb()

    def open_unit(self) -> ctypes.c_int16:
        """Open the Dr DAQ unit for measurements.

        Returns:
            ctypes.c_int16: Handle to the device
        """

        hdl = ctypes.c_int16()
        status = self.lib.UsbDrDaqOpenUnit(ctypes.byref(hdl))
        self.logger.debug(f"Pico Status: {status}.")
        self.logger.debug(f"Handle: {hdl.value}.")

        return hdl

    def close_unit(self):
        """Close connection to the Dr DAQ unit.
        """

        self.logger.debug("Closing Dr DAQ unit.")
        try:
            result = self.lib.UsbDrDaqCloseUnit(self.handle)
            self.logger.debug(f"Pico Status: {result}.")
        except Exception:
            self.logger.critical("Unable to close Dr DAQ unit.")

    def enable_rgb(self):
        """Enable usage of the RGB LED on the Dr DAQ unit.
        """

        self.lib.UsbDrDaqEnableRGBLED(self.handle, ctypes.c_short(1))

    def set_rgb(self, r: int, g: int, b: int):
        """Set the RGB value of the LED on the Dr DAQ unit.

        Args:
            r (int): Red value (0-255)
            g (int): Green value (0-255)
            b (int): Blue value (0-255)
        """

        self.lib.UsbDrDaqSetRGBLED(
            self.handle,
            ctypes.c_ushort(r),
            ctypes.c_ushort(g),
            ctypes.c_ushort(b)
        )

    def set_DAQ_interval(self) -> int:
        """Set the sampling rate of the Dr DAQ unit.

        Returns:
            int: Result of the operation
        """

        self.logger.debug("Setting Dr DAQ sampling rate.")
        result = self.lib.UsbDrDaqSetInterval(
            self.handle,
            ctypes.byref(self.recording_block),
            self.no_of_samples,
            ctypes.byref(self.channel),
            self.no_of_active_channels
        )
        self.logger.debug(f"Status of Dr DAQ interval setting: {result}.")

        return result

    def run_single_shot(self) -> int:
        """Perform a single shot run of the Dr DAQ unit.

        Returns:
            int: Result of the operation
        """

        result = self.lib.UsbDrDaqRun(
            self.handle, self.no_of_samples, ctypes.c_int16(1)
        )
        self.logger.debug("Initialising Dr DAQ single show run.")
        self.logger.debug(f"Status of Dr DAQ single shot run: {result}.")

        return result

    def sampling_done(self):
        """Determine if the sampling has finished for the Dr DAQ unit.

        Returns:
            bool: Sampling is done or not
        """

        done = ctypes.c_bool(0)
        result = self.lib.UsbDrDaqReady(self.handle, ctypes.byref(done))
        self.logger.debug("Checking if Dr DAQ sampling is done.")
        self.logger.debug(f"Pico Status: {result}.")
        self.logger.debug(f"Dr DAQ sampling is: {done}")

        if result == 0:
            return bool(done)

        return False

    def stop_sampling(self):
        """Stop current sampling on the Dr DAQ unit.

        Returns:
            int: Result of the operation
        """

        result = self.lib.UsbDrDaqStop(self.handle)
        self.logger.debug("Dr DAQ stopping sampling.")
        self.logger.debug(f"Pico Status: {result}")

        return result

    def get_sampled_values(self) -> np.array:
        """Get the values sampled form the Dr DAQ unit.

        Returns:
            np.array: Measured values or empty list if none available
        """

        no_of_values = self.no_of_samples
        overflow = ctypes.c_int16(0)

        result = self.lib.UsbDrDaqGetValues(
            self.handle,
            ctypes.byref(self.measurement_results),
            ctypes.byref(no_of_values),
            ctypes.byref(overflow),
            None
        )

        self.logger.debug(f"Pico Status sampling: {result}")
        self.logger.debug(
            f"Dr DAQ number of samples measured: {self.no_of_samples}"
        )
        self.logger.debug(f"Dr DAQ Channel with overflow: {overflow}")

        if result == 0:
            samples = np.ctypeslib.as_array(self.measurement_results)
            self.logger.debug(f"Dr DAQ Sample Values: {samples}")
            return samples

        return []
