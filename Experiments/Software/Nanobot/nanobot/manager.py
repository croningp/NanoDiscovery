"""
.. module:: nanobot.manager
    :platforms: Unix, Windows
    :synopsis: Main controller of the Nanobot system

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)
"""

# System imports
import time
from typing import Union, Dict, List, Optional

# Nanobot imports
import nanobot.constants as cst
from .operations.cleaning import clean_vial_protocol, acid_purge

# Cronin Imports
from modularwheel.utils import Reagent
from modularwheel import ModularManager
# from croningpslackbot import SlackbotNotifier
from .OceanOptics.UV.QEPro2192 import QEPro2192
from .OceanOptics.IR.NIRQuest512 import NIRQuest512
from .OceanOptics.Raman.raman_control import OceanOpticsRaman

class NanobotManager(ModularManager):
    """Manager class for controlling the Nanobot system

    Args:
        config (Union[str, Dict]): Platform configuration file
        debug (Optional[bool]): Debug flag

    Inherits:
        ModularManager: Core of the ModularWheel systems
    """
    def __init__(
        self,
        config: Union[str, Dict],
        logfile: Optional[str] = "",
        debug: Optional[bool] = False
    ):
        super().__init__(config, logfile=logfile, debug=debug)

        # Spectrometer controllers
        self.uv, self.ir, self.raman = None, None, None

        # Check for spectrometers in config
        if 'spectrometers' in self.config["modules"]:
            self._initialise_spectrometers()

        # Slackbot for notifications
        # self.slackbot = SlackbotNotifier()

        # Home all motors
        self.home_all_motors()

    def _initialise_spectrometers(self):
        """Initialises the spectrometers if they are defined in the config
        """

        self.logger.debug('Initialising spectrometers')
        spectrometer_cfg = self.config['spectrometers']

        # UV controller
        if 'uv' in spectrometer_cfg:
            uv_config = spectrometer_cfg['uv']
            self.uv = QEPro2192()
            self.uv.set_integration_time(uv_config['integration_time'])
            self.logger.info('Registered UV spectrometer')

        # IR Controller
        if 'ir' in spectrometer_cfg:
            ir_config = spectrometer_cfg['ir']
            self.ir = NIRQuest512()
            self.ir.set_integration_time(ir_config['integration_time'])
            self.logger.info('Registered IR spectrometer')

        # Raman Controller
        if 'raman' in self.config['spectrometers']:
            self.raman = OceanOpticsRaman()
            self.logger.info('Registered Raman spectrometer')

        self.logger.debug('Finished initialising spectrometers')

    def reference_spectra_taken(self) -> bool:
        """Check if references have been taken for UV and IR

        Returns:
            bool: If the references have been called or not
        """

        refs_taken = []

        if self.uv is not None:
            self.logger.debug('Checking for UV reference')
            refs_taken.append(self.uv.reference)

        if self.ir is not None:
            self.logger.debug('Checking for IR reference')
            refs_taken.append(self.ir.reference)

        if self.raman is not None:
            self.logger.debug('Checking for Raman reference')
            refs_taken.append(self.raman.reference)

        if not refs_taken:
            self.logger.warning(
                'No spectrometers found when checking for reference'
            )
            return

        return all(refs_taken)

    def create_reagent(
        self,
        name: str,
        volume: Optional[float] = 1.0,
        in_valve: Optional[str] = cst.EXTRA,
        out_valve: Optional[str] = cst.INLET
    ) -> Reagent:
        """Create a reagent specific for the Nanobot system

        Args:
            name (str): Name of the Reagent
            volume (Optional[float], optional): Reagent volume. Defaults to 1.0.

        Returns:
            Reagent: Reagent object to dispense
        """

        return Reagent(name, volume, in_valve=in_valve, out_valve=out_valve)

    def home_all_motors(self):
        """Homes all motors on the Nanobot platform
        """

        self.logger.info('Homing all motors')
        self.wheel.home_motor(cst.SAMPLE_MODULE)
        self.wheel.home_motor(cst.PH_VERT_MODULE)
        self.wheel.home_motor(cst.PH_HORZ_MODULE)

    def call_spectrometers(self, reference: bool = False):
        """Calls on the spectrometers to obtain eithe reference spectra
        or experimental spectra.
        """

        uv_spectrum, ir_spectrum = None, None

        # Get the UV spectrum
        if self.uv is not None:
            self.logger.info('Obtaining UV spectrum')
            uv_spectrum = (
                self.uv.obtain_reference_spectrum() if reference
                else self.uv.obtain_spectrum()
            )

        # Get the IR spectrum
        if self.ir is not None:
            self.logger.info('Obtaining IR spectrum')
            ir_spectrum = (
                self.ir.obtain_reference_spectrum() if reference
                else self.ir.obtain_spectrum()
            )

        # Return obtained spectra
        return uv_spectrum, ir_spectrum

    def obtain_uv_ir_spectra(
        self, sample_volume: float = 5, reference: bool = False
    ):
        """Obtains both a UV and IR spectrum of a solution.
        If reference flag is set, just takes a reference sample.

        Args:
            vial_volume (float, optional): Volume of the vial. Defaults to 10
            reference (bool, optional): Taking UV/IR reference.
                                        Defaults to False.

        Returns:
            UVSpectrum, IRSpectrum: UV and IR spectrum objects
        """
        self.logger.debug('Obtaining Spectra')

        # TODO::Deal with Raman at some point - 14/07/20

        # No spectrometers, do not process
        if self.uv is None and self.ir is None:
            self.logger.error(
                'Attempting to obtain spectra when no spectrometers present'
            )
            return

        # 80% of vial volume used as an output volume
        # Prevents air going through the UV/IR cells
        sample_volume = round(sample_volume, 2)
        sample_output_volume = round((sample_volume / 5) * 4, 2)

        self.logger.debug(f'Sample volume: {sample_output_volume}')

        # Lower the wheel into position
        self.logger.debug('Moving sample driver to lower position')
        self.wheel.move_motor_to_position(
            cst.SAMPLE_MODULE, cst.SAMPLE_MODULE_LOWER
        )

        # Taking reference, dispense water into vial
        if reference:
            self.logger.info('Reference spectra collection.')
            reference_volume = sample_volume * 2
            self.dispense(
                cst.WATER_PUMP,
                reference_volume,
                in_valve=cst.WATER_STOCK,
                out_valve=cst.WATER_TO_SAMPLE
            )
        else:
            self.logger.info('Experimental spectra collection.')

        # Take the sample and pass through UV/IR lines
        self.logger.debug('Moving sample through lines')

        # Full dispense first to ensure little air in the lines
        self.dispense(
            cst.SAMPLE_PUMP,
            sample_volume,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=27000
        )

        # Dispense sample to be measured
        residual_vol = self.partial_dispense(
            cst.SAMPLE_PUMP,
            volume_in=sample_volume,
            volume_out=sample_output_volume,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=27000
        )

        residual_vol = round(residual_vol, 2)

        # Wait for 5 seconds after dispensing, then take the UV-Vis
        time.sleep(5)

        # Obtain the spectra
        uv_spectrum, ir_spectrum = self.call_spectrometers(reference=reference)

        # Push remaining volume in sample syringe back through lines
        self.logger.debug('Moving remaining liquid through lines')
        self.partial_dispense(
            cst.SAMPLE_PUMP,
            volume_out=residual_vol,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED
        )

        # Home the sample motor
        self.logger.debug('Homing sample driver')
        self.wheel.home_motor(cst.SAMPLE_MODULE)

        # Return both spectra
        return uv_spectrum, ir_spectrum

    def obtain_uv_ir_spectra2(
        self, sample_volume: float = 5, reference: bool = False
    ):
        """Obtains both a UV and IR spectrum of a solution.
        If reference flag is set, just takes a reference sample.

        Args:
            vial_volume (float, optional): Volume of the vial. Defaults to 10
            reference (bool, optional): Taking UV/IR reference.
                                        Defaults to False.

        Returns:
            UVSpectrum, IRSpectrum: UV and IR spectrum objects
        """
        self.logger.debug('Obtaining Spectra')

        # TODO::Deal with Raman at some point - 14/07/20

        # No spectrometers, do not process
        if self.uv is None and self.ir is None:
            self.logger.error(
                'Attempting to obtain spectra when no spectrometers present'
            )
            return

        # 80% of vial volume used as an output volume
        # Prevents air going through the UV/IR cells
        uv_spectrum_ref, ir_spectrum_ref = self.call_spectrometers(reference=True)

        sample_output_volume = (sample_volume / 5) * 4
        self.logger.debug(f'Sample volume: {sample_output_volume}')

        # Lower the wheel into position
        self.logger.debug('Moving sample driver to lower position')
        self.wheel.move_motor_to_position(
            cst.SAMPLE_MODULE, cst.SAMPLE_MODULE_LOWER
        )

        # Taking reference, dispense water into vial
        if reference:
            self.logger.info('Reference spectra collection.')
            reference_volume = sample_volume * 2
            self.dispense(
                cst.WATER_PUMP,
                reference_volume,
                in_valve=cst.WATER_STOCK,
                out_valve=cst.WATER_TO_SAMPLE
            )
        else:
            self.logger.info('Experimental spectra collection.')

        # Take the sample and pass through UV/IR lines
        self.logger.debug('Moving sample through lines')

        # Full dispense first to ensure little air in the lines
        self.dispense(
            cst.SAMPLE_PUMP,
            sample_volume,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED
        )

        # Dispense sample to be measured
        residual_vol = self.partial_dispense(
            cst.SAMPLE_PUMP,
            volume_in=sample_volume,
            volume_out=sample_output_volume,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED
        )

        # Wait for 5 seconds after dispensing, then take the UV-Vis
        time.sleep(5)

        # Obtain the spectra
        uv_spectrum, ir_spectrum = self.call_spectrometers(reference=True)

        # Push remaining volume in sample syringe back through lines
        self.logger.debug('Moving remaining liquid through lines')
        self.partial_dispense(
            cst.SAMPLE_PUMP,
            volume_out=residual_vol,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED
        )

        # Home the sample motor
        self.logger.debug('Homing sample driver')
        self.wheel.home_motor(cst.SAMPLE_MODULE)

        # Return both spectra
        return uv_spectrum, ir_spectrum, uv_spectrum_ref, ir_spectrum_ref
        
    def obtain_sample_ph(self) -> float:
        """Measures the pH of the sample using the DrDAQ potentiostat

        Returns:
            float: Measured pH
        """

        # Move pH modular drivers into position
        self.wheel.move_motor_to_position(
            cst.PH_HORZ_MODULE, cst.PH_HORZ_SAMPLE_POSITION
        )
        self.wheel.move_motor_to_position(
            cst.PH_VERT_MODULE, cst.PH_VERT_SAMPLE_POSITION
        )

        # Measure and log the pH of solution
        pH = self.pH_module.measure_pH()
        self.logger.info(f"Measured pH: {pH}")

        # Home the pH modular drivers
        self.wheel.home_motor(cst.PH_VERT_MODULE)
        self.wheel.home_motor(cst.PH_HORZ_MODULE)

        return pH

    def clean_vial(self):
        """Cleans the sampling vial. Performs an acid clean followed
        by water cleaning.
        """
        self.logger.info('Beginning clean cycle')

        self.logger.debug('Moving sample driver to lower position')
        self.wheel.move_motor_to_position(
            cst.SAMPLE_MODULE, cst.SAMPLE_MODULE_LOWER
        )

        clean_vial_protocol(self.dispense, cycles=5)
        # clean_vial_protocol(self.dispense, cycles=1)

        self.logger.debug('Homing sample driver')
        self.wheel.home_motor(cst.SAMPLE_MODULE)

        self.turn_wheel(cst.WHEEL_NAME)

    def acid_system_clean(self):
        """Cleans the system lines with Aqua Regia and water
        """

        self.logger.info('Cleaning lines with Aqua Regia and Water')

        self.wheel.move_motor_to_position(
            cst.SAMPLE_MODULE, cst.SAMPLE_MODULE_LOWER
        )

        acid_purge(self.dispense)

        self.wheel.home_motor(cst.SAMPLE_MODULE)

        self.turn_wheel(cst.WHEEL_NAME)

    def remove_residues(self, *pump_names: str, cycles: int = 2):
        """Removes any residues from the given pumps using water.

        Args:
            pump_names (str): Pumps to remove residues from.
            cycles (int, optional): Removal cycles. Defaults to 2.
        """

        self.logger.info('Removing residue from the lines')

        # Volume of water to remove residue
        residue_vol = 0.5

        # Iterate through all given pumps
        for pump in pump_names:
            self.logger.debug('Removing residue from \"pump\"')
            # Perform removal X times
            for _ in range(cycles):
                # Take in small amount of water
                self.dispense(
                    pump, residue_vol, in_valve=cst.OUTLET, out_valve=cst.EXTRA
                )

                # Dispense small amount of water through valve
                self.dispense(
                    pump, residue_vol, in_valve=cst.OUTLET, out_valve=cst.INLET
                )

    def convert_params_dict_to_reagents(self, params: Dict) -> List:
        """Converts a dictionary of experimental parameters to a list of
        Reagent objects

        Args:
            params (Dict): Experimental parameters ({name: vol, name: vol, etc})

        Returns:
            List: List of Reagents converted to Params
        """

        return [
            self.create_reagent(name, volume)
            for name, volume in params.items()
        ]

    def send_slack_message(self, msg: str):
        """Send a slack message to users concerned

        Args:
            msg (str): Message to send
        """

        # msg = f'Nanobot::{msg}'
        # self.slackbot.post_multiple_user_messages(msg, cst.SLACK_IDS)
