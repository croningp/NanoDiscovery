"""
.. module:: core.core_experiment
    :platform: Unix
    :synopsis: Base class for experimental scripts

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

# System imports
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

# Platform imports
import nanobot.constants as cst
from nanobot import NanobotManager
from modularwheel.utils import read_json

# Path setup
HERE = Path('.').absolute()
DATA = HERE.joinpath('..', 'data').absolute()

# Platform config file
PLATFORM_CONFIG = HERE.joinpath('configs', 'platform_configuration.json')

# Experimental Info file
EXPERIMENTAL_INFO = HERE.joinpath('configs', 'experimental_information.json')

class MethodNotImplemented(Exception):
    """Raised when a method has not been implemented in inheriting class
    """
    pass

def generate_experiment_path(experiment_info: Dict) -> str:
    """Generates the path for the experiment dependent on algorithm class

    Args:
        experiment_info (Dict): Experimental info

    Returns:
        str: Path to experiment folder
    """

    # Extract info from experiment info
    seed = str(experiment_info[cst.SEED])
    title = experiment_info[cst.TITLE]
    algorithm = experiment_info[cst.ALGORITHM]

    # Using Genetic Algorithm
    if algorithm == 'GA':
        return DATA.joinpath('GA', title, seed).absolute()

    # Using a basic experiment
    if algorithm == 'basic':
        return DATA.joinpath('basic', title).absolute()

    if algorithm == 'bayes':
        return DATA.joinpath('bayes', title).absolute()

    if algorithm == 'custom':
        return DATA.joinpath('custom', title).absolute()

def generate_spectra_filenames(
    xp_path: str, reference: bool = False
) -> Tuple[str]:
    """Generate filenames for the UV and IR spectra dependent of refernce flag

    Args:
        xp_path (str): Experiment path
        reference (bool, optional): Reference filenames or not.
                                    Defaults to True.

    Returns:
        Tuple[str]: UV and IR names
    """

    if reference:
        uv_img = xp_path.joinpath(cst.REF_UV_IMG)
        uv_raw = xp_path.joinpath(cst.REF_UV_JSON)

        ir_img = xp_path.joinpath(cst.REF_IR_IMG)
        ir_raw = xp_path.joinpath(cst.REF_IR_JSON)
    else:
        uv_img = xp_path.joinpath(cst.UV_IMG)
        uv_raw = xp_path.joinpath(cst.UV_JSON)

        ir_img = xp_path.joinpath(cst.IR_IMG)
        ir_raw = xp_path.joinpath(cst.IR_JSON)

    return uv_img, uv_raw, ir_img, ir_raw


class CoreExperiment(object):
    """Base class for an experiment run file.
    Inheriting class provides new methods and implementations for
    the reaction_protocol and process_protocol methods.
    """

    def __init__(self):
        # Load configurations
        self.info = read_json(EXPERIMENTAL_INFO)
        self.hardware_config = read_json(PLATFORM_CONFIG)

        # Set root experimental folder
        self.root_xp_folder = generate_experiment_path(self.info)

        # Initialise the platform controller
        logfile = self.root_xp_folder / f"{time.strftime('%d_%m_%y')}.log"
        self.manager = NanobotManager(self.hardware_config, logfile=logfile)

    def __del__(self):
        """
        Kill all stirrers when closing the experiment
        """

        self.kill_ring_stirrers()
        self.manager.wheel.home_all_motors()

    def preflush_pumps(self, *pumps: str, vol: float = 2):
        """Preflushes the pumps to prevent dead volumes in the tubing

        Args:
            pumps (str): Pumps to preflush
            vol (float, optional): Volume to preflush tubing with.
                                    Defaults to 3.
        """

        preflush = [
            self.manager.create_reagent(*pump)
            if isinstance(pump, tuple)
            else self.manager.create_reagent(pump, volume=vol)
            for pump in pumps
        ]

        ans = input('Do you wish to preflush the pumps? (y/n) ')
        if str(ans).lower() == 'y':
            self.manager.logger.info(f'Preflushing pumps: {preflush}')
            for reagent in preflush:
                if reagent.name == 'NaOH':
                    self.manager.dispense(
                    reagent.name,
                    reagent.volume,
                    in_valve=cst.OUTLET,
                    out_valve=cst.INLET,
                    speed_out=cst.FAST_SPEED)

                else:
                    self.manager.dispense(
                        reagent.name,
                        reagent.volume,
                        reagent.in_valve,
                        reagent.out_valve,
                        speed_out=cst.FAST_SPEED
                    )

            self.manager.turn_wheel(cst.WHEEL_NAME)
            input("Replace the vial and press enter.")

    def preflush_pumps2(self, *pumps: str, vol: float = 2):
        """Preflushes the pumps to prevent dead volumes in the tubing

        Args:
            pumps (str): Pumps to preflush
            vol (float, optional): Volume to preflush tubing with.
                                    Defaults to 3.
        """

        preflush = [
            self.manager.create_reagent(*pump)
            if isinstance(pump, tuple)
            else self.manager.create_reagent(pump, volume=vol)
            for pump in pumps
        ]
        
        ans = 'y'
        if str(ans).lower() == 'y':
            self.manager.logger.info(f'Preflushing pumps: {preflush}')
            for reagent in preflush:
                if reagent.name == 'NaOH':
                    self.manager.dispense(
                    reagent.name,
                    reagent.volume,
                    in_valve=cst.OUTLET,
                    out_valve=cst.INLET,
                    speed_out=cst.FAST_SPEED)

                else:
                    self.manager.dispense(
                        reagent.name,
                        reagent.volume,
                        reagent.in_valve,
                        reagent.out_valve,
                        speed_out=cst.FAST_SPEED
                    )

            self.manager.turn_wheel(cst.WHEEL_NAME)
            
    def prime_reductant(self, flush: float = 1.5):
        """ Asks the user if they wish to re-flush the reductant pump

        Args:
            flush (float): Flush volume (Default = 1.5)
        """

        ans = input("Re-flush reductant? (y/n) ")

        if str(ans).lower() == "y":
            self.manager.logger.info(f"Re-flushing reductant: {flush}ml")
            self.manager.dispense(
                'reductant',
                volume=flush,
                in_valve=cst.EXTRA,
                out_valve=cst.INLET
            )

        self.manager.turn_wheel(cst.WHEEL_NAME)
        input("Replace vial and press enter.")

    def ask_for_system_purge(self):
        """Prompts the user if they wish to clean with acid
        """

        # Prompt user if they wish to perform an acid clean afterwards
        ans = input('Perform acid clean cycle? (y/n) ')
        self.manager.send_slack_message('Acid clean reposnse requested!')
        if ans.lower() == 'y':
            self.manager.acid_system_clean()

    def activate_ring_stirrer(self, speed: int = 25):
        """
        Activates the stirrers on the Ring

        Args:
            speed (int): Speed of the stirrers (0-255)
        """

        self.manager.set_stir_rate(cst.RING, speed)

    def kill_ring_stirrers(self):
        """
        Kills the stirrers on the ring
        """

        self.manager.set_stir_rate(cst.RING, 0)

    def take_reference(self):
        """Takes a reference spectrum if not already taken
        """

        # Filepaths to check for pre-existing reference spectra
        ref_uv = self.root_xp_folder.joinpath(cst.REF_UV_JSON)
        ref_ir = self.root_xp_folder.joinpath(cst.REF_IR_JSON)

        # UV ref exists
        if ref_uv.exists():
            self.manager.uv.load_reference(ref_uv)

        # IR ref exists
        if ref_ir.exists():
            self.manager.ir.load_reference(ref_ir)

        # Already taken log and return
        if self.manager.reference_spectra_taken():
            self.manager.logger.info(
                f'Reference already logged for {self.root_xp_folder}'
            )
            return

        # Take reference spectra if absent from generation
        self.manager.logger.info(
            f"Obtaining reference for {self.root_xp_folder}"
        )
        uv, ir = self.manager.obtain_uv_ir_spectra(reference=True)
        self.save_spectra(uv, ir, self.root_xp_folder, reference=True)
        self.manager.turn_wheel(cst.WHEEL_NAME)

    def save_spectra(
        self, uv_spectrum, ir_spectrum, xp_path: str, reference: bool = False
    ):
        """Saves the UV and IR spectra to disk

        Args:
            uv_spectrum (UVSpectrum): UV spectrum object
            ir_spectrum (IRSpectrum): IR spectrum object
            xp_path (str): Folder to save to
        """

        # Get spectra filenames
        uv_img, uv_raw, ir_img, ir_raw = generate_spectra_filenames(
            xp_path, reference=reference
        )

        # Save raw data to JSON and plot
        if uv_spectrum is not None:
            # uv_spectrum.plot_spectrum(savepath=uv_img, limits=cst.UV_LIMITS)
            uv_spectrum.dump_spectrum(uv_raw)

        if ir_spectrum is not None:
            # ir_spectrum.plot_spectrum(savepath=ir_img, limits=cst.IR_LIMITS)
            ir_spectrum.dump_spectrum(ir_raw)

    def reaction_protocol(self):
        raise MethodNotImplemented("This method needs a definition!")

    def process_protocol(self):
        raise MethodNotImplemented("This method needs a definition!")

    def full_protocol(self):
        raise MethodNotImplemented("This method needs a definition!")
