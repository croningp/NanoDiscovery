"""
.. module:: manager
    :platform: Unix
    :synopsis: Manager for controlling the modular wheel system

.. moduleauthor:: Graham Keenan (Cronin Lab 2019)

"""

# System imports
import time
from typing import Union, Optional

# Platform imports
import modularwheel.utils as utils
from .constants import common as cst

def _get_configuration(config: Union[str, dict]) -> dict:
    """Gets the hardware configuration.
    If it's a string, read the file and return
    Else, assume dict and return

    Args:
        config (Union[str, dict]): Config file path or actual config dict

    Returns:
        dict: Config dict
    """

    if isinstance(config, str):
        return utils.read_json(config)

    return config

class ModularManager:
    """Class for controlling the Drivers of the platform

    Args:
        config_file (str): Path to config file for the platform
        debug (Optional[bool]): Debug flag. Defaults to False.
    """

    def __init__(
        self,
        config: Union[str, dict],
        logfile: Optional[str] = "",
        debug: Optional[bool] = False
    ):
        # Platform configuration file
        self.config = _get_configuration(config)

        # Logger
        self.logger = utils.make_logger(
            self.name, filename=logfile, debug=debug
        )

        # Tricont controller
        self.triconts = None
        if 'triconts' in self.config['modules']:
            from .drivers import TricontDriver
            self.triconts = TricontDriver(self.config['triconts'])

        # Modular wheel controller
        self.wheel = None
        if 'commanduino' in self.config['modules']:
            from commanduinolabware import CommanduinoLabware
            self.wheel = CommanduinoLabware(
                config=self.config['commanduino']
            )

        # pH module
        self.ph_module = None
        if 'pH' in self.config['modules']:
            from .drivers import DrDAQDriver
            self.ph_module = DrDAQDriver(self.config['pH_calibrations'])

        # Camera module
        self.camera = None
        if 'camera' in self.config['modules']:
            from .drivers import CameraDriver
            self.camera = CameraDriver(self.config['camera'])

        # Vial position tracker
        self.vial_position = 0

        # Reverse flag
        self.wheel_reversed = False

    @property
    def name(self) -> str:
        """Gets the name of the Manager

        Returns:
            str: Manager name
        """

        return self.__class__.__name__

    def turn_wheel(self, wheel_name: str, n_turns: int = 1):
        """Turns the motor which represents the modular wheel N times

        Args:
            wheel_name (str): Name of the motor which acts as the wheel.
            n_turns (int, optional): Number of times to turn the wheel.
                                        Defaults to 1.
        """

        self.logger.debug(f"Turning wheel: {n_turns} times")
        self.wheel.turn_motor(wheel_name, n_turns)

        # Update the current vial position
        self._update_vial_position(n_turns)

    def _update_vial_position(self, positions: int):
        """Updates the current position of the vial

        Args:
            positions (int): Number of positions that the vial has moved
        """

        # Increment positions if wheel not reversed
        if not self.wheel_reversed:
            self.vial_position += positions

        # Decrement position if the wheel is reversed
        else:
            self.vial_position -= positions

        # Correct the position if the current position is outside 0-23 range
        if self.vial_position <= 0:
            self.vial_position += 24
        elif self.vial_position >= 24:
            self.vial_position -= 24

    def reverse_wheel(self, wheel_name: str):
        """Reverses the direction of the wheel

        Args:
            wheel_name (str): Reverses the direction of the wheel
        """

        self.wheel.reverse_motor_direction(wheel_name)
        self.wheel_reversed = not self.wheel_reversed

    def prime_pumps(
        self,
        prime_volume: Optional[float] = 2,
        default_in_valve: Optional[str] = 'I',
        default_out_valve: Optional[str] = 'O'
    ):
        """Primes the tubing for the pumps.
        Warning -- Tricont only.

        Args:
            prime_volume (Optional[float], optional): Default prime volume.
                                                    Defaults to 2.
            default_in_valve (Optional[str], optional): Default input valve.
                                                    Defaults to 'I'.
            default_out_valve (Optional[str], optional): Default output valve.
                                                    Defaults to 'O'.
        """

        if self.triconts is None:
            self.logger.warning(
                "Your system configuration does not support Tricont pumps."
            )
            return

        all_pumps = self.triconts.controller.get_all_pumps()
        self.logger.debug(f'Tricont pumps: {all_pumps}')

        for pump in all_pumps:
            self.logger.info(
                f"Priming pump {pump} with volume {prime_volume}mL."
            )

            self.dispense(
                pump,
                prime_volume,
                in_valve=default_in_valve,
                out_valve=default_out_valve
            )

    def dispense(
        self,
        pump: str,
        volume: float = 0,
        in_valve: str = "I",
        out_valve: str = "O",
        speed_in: int = cst.DEFAULT_PUMP_SPEED,
        speed_out: int = cst.DEFAULT_PUMP_SPEED,
        calibrations: dict = {}
    ):
        """Dispenses a single reagent from a pump
        Uses triconts if they're set up, else uses the Peri pumps
        via Commanduino

        Args:
            pump (str): Name of the pump
            volume (float, optional): Volume to dispense. Defaults to 0.
            in_valve (str, optional): In valve (Triconts only). Defaults to "I"
            out_valve (str, optional): Out valve (Triconts only).
                                        Defaults to "O".
            speed_int (int, optional): Draw speed of a Tricont
            speed_out (int, optional): Push speed of a Tricont
            calibrations (dict, optional): Calibrations if using peristaltics
        """

        if self.triconts is None:
            self.logger.debug('No Tricont controller, running from Peri Pumps')
            self.logger.info(f'Pump: {pump} Vol: {volume}ml')

            self.run_motor_pump_by_volume(
                pump, volume, calibrations=calibrations
            )
        else:
            self.logger.debug('Using Tricont controller')
            self.logger.info(
                f'Dispensing {volume}ml from pump \"{pump}\"\
 (In: {in_valve} Out: {out_valve})')

            self.triconts.transfer(
                pump,
                volume,
                in_valve=in_valve,
                out_valve=out_valve,
                speed_in=speed_in,
                speed_out=speed_out
            )

    def partial_dispense(
        self,
        name: str,
        volume_in: float = 0,
        volume_out: float = 0,
        in_valve: str = cst.INLET,
        out_valve: str = cst.OUTLET,
        speed_in: int = cst.DEFAULT_PUMP_SPEED,
        speed_out: int = cst.DEFAULT_PUMP_SPEED
    ) -> float:
        """Performs a partial dispense form a pump.
        Volume in differs from volume out.

        Tricont only.

        Args:
            name (str): Name of the pump
            volume_in (float, optional): Volume in. Defaults to 0.
            volume_out (float, optional): Volume out. Defaults to 0.
            in_valve (str, optional): In valve. Defaults to 'I'.
            out_valve (str, optional): Out Valve. Defaults to 'O'.
            speed_int (int, optional): Draw speed of a Tricont
            speed_out (int, optional): Push speed of a Tricont

        Returns:
            float: Volume remaining in the pump
        """

        if self.triconts is None:
            self.logger.warning('This operation requires Tricont pumps.')
            return

        residual_volume = self.triconts.partial_dispense(
            name,
            volume_in=volume_in,
            volume_out=volume_out,
            in_valve=in_valve,
            out_valve=out_valve,
            speed_in=speed_in,
            speed_out=speed_out
        )

        return residual_volume

    def run_motor_pump_by_volume(
        self,
        motor_name: str,
        volume: float,
        calibrations: dict
    ):
        """Runs a motor pump to dispense a given volume.
        Runtime for the pump is dependent on calibrations for the specific
        motor.

        Args:
            motor_name (str): Name of the motor pump
            volume (float): Volume to dispense
            calibrations (dict): Volume dispened per minute by each motor pump

        Raises:
            Exception: No calibrations or pump not in calibrations
        """

        if motor_name not in calibrations:
            self.logger.critical(
                f'Attempting to run motor \"{motor_name}\" with no calibrations'
            )
            raise Exception(
                f"Attempting to run motor {motor_name} with no calibrations."
            )

        # Get the volume dispensed per minute by the motor pump
        calibration = calibrations[motor_name]
        self.logger.debug(
            f'Calibration for pump \"{motor_name}\": {calibration}'
        )

        # Calculate runtime required to dispense given volume
        runtime = (volume / (calibration / cst.MINUTE))
        self.logger.debug(f'Calculated runtime: {runtime}')

        # Run the pump for the runtime
        self.logger.info(f'Dispensing {volume}mL from pump \"{motor_name}\"')
        self.wheel.run_motor(motor_name, runtime)

    def set_pump_speed(self, pump_name: str, new_speed: int):
        """Sets the speed of the pump

        Args:
            pump_name (str): Name of the pump
            new_speed (int): New speed to set
        """

        self.logger.info(f'Setting \"{pump_name}\" speed to {new_speed}')
        if self.triconts is None:
            self.wheel.set_motor_speed(pump_name, new_speed)
        else:
            self.triconts.set_pump_speed(pump_name, new_speed)

    def set_stir_rate(self, stir_pin: str, val: int):
        """Set the stir rate of the stirrers on the wheel

        Args:
            stir_pin (str): Name of the pin attached to the stirrers
            val (int): PWM value to set (0-255)
        """

        self.logger.info(f"Setting stir rate: {val}")

        # If value is less than 100, give the fans a kick first
        # then settle on value
        if 0 < val < 150:
            self.logger.debug(f'Value {val} below 100, ramping up speed first')
            self.wheel.write_analog(stir_pin, 255)
            time.sleep(5)

        # Set the actual value
        self.wheel.write_analog(stir_pin, val)

    def tune_pH_measurement(
        self,
        target_pH: float,
        acid_pump: str,
        base_pump: str,
        coeff: Optional[float] = 10.0,
        dilution_factor: Optional[float] = 1.0,
        default_vol: Optional[float] = 10 * (10 ** -3)
    ):
        """Tunes the pH of a solution dynamically.

        Args:
            target_pH (float): pH to aim for.

            acid_pump (str): Name of the acid pump.

            base_pump (str): Name of the base pump.

            coeff (Optional[float], optional): Tuning coefficient.
            Defaults to 10.0.

            dilution_factor (Optional[float], optional): Dilution factor.
            Defaults to 1.0.

            default_vol (Optional[float], optional): Default dispense volume.
            Defaults to 10*(10 ** -3).
        """

        # Initial pH measurement
        measured_pH = self.ph_module.measure_pH()

        # Direction of pH travel
        direction = ""

        # Loop until consensus reached
        while True:
            # Solution is too basic
            if target_pH < measured_pH:
                # Calculate error and dispensing volume
                error = measured_pH - target_pH
                volume = coeff * error * default_vol

                # Dispense the acid
                self.dispense(acid_pump, volume)

                # Update direction of travel
                direction = "acidic"

            # Solution is too acidic
            elif measured_pH < target_pH:
                # Calculate error and dispensing volume
                error = target_pH - measured_pH
                volume = coeff * error * default_vol

                # Dispense the base
                self.dispense(base_pump, volume)

                # Update direction of travel
                direction = "basic"

            # Wait for stabilisation and record pH
            time.sleep(5)
            measured_pH = self.ph_module.measure_pH()

            # pH is within range
            if measured_pH - 0.05 <= target_pH <= measured_pH + 0.05:
                # Wait to see if it is stable
                time.sleep(30)

                # Check range again and break if stable
                if measured_pH - 0.05 <= target_pH <= measured_pH + 0.05:
                    break

            # Overshot the target, reduce coefficient and repeat
            if (
                (direction == "acidic" and target_pH > measured_pH)
                or (direction == "basic" and target_pH < measured_pH)
            ):
                coeff /= 2

    def clean_pH_probe(
        self,
        buffer: utils.Reagent,
        water: utils.Reagent,
        waste: utils.Reagent,
        pH_driver: str,
        horz_driver: str,
        position: Optional[int] = 'home',
        low_driver_position: int = cst.DEFAULT_DRIVER_LOWER_POSITION
    ):
        """Clean the attached pH probe.

        This should be overridden in child classes
        if your platform deviates from the standard ModularWheel design or
        a more thorough cleaning method is required.

        Uses Reagents for the Buffer/Water/Waste as valve
        positions may be required.

        Args:
            buffer (Reagent): Pump for the pH buffer solution
            water (Reagent): Pump for the cleaning water
            waste (Reagent): Pump for waste disposal
            pH_driver (str): Motor the pH driver is attached to
            horz_driver (str): Motor that drives the horizontal movement for
                                the pH unit.
            position (Optional[int], optional): Position to move to for the
                                cleaning station. This could be the home
                                position of the motor or a specific position.
                                Defaults to 'home'.
            low_driver_position (int, optional): Position which is the lowest
                                point the pH driver should descend to.
                                Defaults to cst.DEFAULT_DRIVER_LOWER_POSITION.
        """

        self.logger.critical('Method required manual override in child class!')
        raise NotImplementedError(
            "This method is custom to each platform. Requires manual override\
 in child class!")

    def image(self, save_location: str):
        """Takes in image using the platform's camera, if present

        Args:
            save_location (str): Path to save image to
        """

        if self.camera is None:
            self.logger.warning('No camera detected for image capture')
            return

        self.camera.take_image(save_location)
        self.logger.debug(f'Image saved to: {save_location}')

    def record(self, save_location: str, duration: float, fps: int = 30):
        """Record a video using the platform's camera, if present

        Args:
            save_location (str): Path to save video to
            duration (float): Duration of the video
            fps (int, optional): Recording frame rate. Defaults to 30.
        """

        if self.camera is None:
            self.logger.warning('No camera detected for video recording')
            return

        self.logger.debug(
            f'Recording video at {fps} FPS for {duration}. Saving to:\
 {save_location}')

        self.camera.record_video(save_location, duration, fps)

    def send_emails(self, msg: str, emails: list = [], flag: int = 0):
        """Send an email to all parties

        Args:
            msg (str): Message to send
            flag (int, optional): Flag for type of email. Defaults to 0.
        """

        self.logger.debug(f'Sending {msg} to emails: {emails}')
        utils.notify_all(cst.PLATFORM_NAME, emails, msg, flag=flag)

    def initialise_file_logger(self, logfile: str):
        """Initialises the logging module

        Args:
            logfile (str): Logfile path.
        """

        self.logger = utils.make_logger(self.name, filename=logfile)

    def wait(self, wait_time: float):
        """Waits for a period of time

        Args:
            wait_time (float): Time to wait in seconds
        """

        self.logger.info(f"Waiting {wait_time} seconds.")
        time.sleep(wait_time)
