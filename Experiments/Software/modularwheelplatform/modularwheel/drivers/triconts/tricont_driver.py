"""
.. module:: tricont_driver
    :platform: Unix, Windows
    :synopsis: Module for higher level control of Tricont pumps

.. moduleauthor:: Graham Keenan 2019

"""

# Module imports
from ...utils import Reagent
import modularwheel.constants as cst
from ...base_drivers import TricontCoreDriver
from typing import List, Union, Tuple, Optional

class TricontDriver(TricontCoreDriver):
    """Driver for controlling the Tricont pumps
    Uses the base driver for the Triconts to obtain the pump controller

    Raises:
        UndefinedPumpError: Pump is invalid
    """

    def __init__(self, pump_config: dict):
        # Initialise the core driver
        TricontCoreDriver.__init__(self, pump_config)

    def pump(
        self,
        name: str,
        volume: float,
        in_valve: Optional[str] = cst.INLET,
        speed_in: Optional[int] = cst.DEFAULT_PUMP_SPEED
    ):
        """Pumps in a set volume

        Args:
            name (str): Name of the pump

            volume (float): Intake volume

            in_valve (Optional[str], optional): Inlet valve.
            Defaults to cst.INLET.

            speed_in (Optional[int], optional): Draw-in speed.
            Defaults to cst.DEFAULT_PUMP_SPEED.
        """

        # Get the pump object
        pump = self.get_pump_obj(name)

        # Draw in the liquid to the syringe
        pump.pump(volume, from_valve=in_valve, speed_in=speed_in)

    def deliver(
        self,
        name: str,
        volume: float,
        out_valve: Optional[str] = cst.OUTLET,
        speed_out: Optional[float] = cst.DEFAULT_PUMP_SPEED
    ):
        """Delivers a volume from a filled syringe

        Args:
            name (str): Name of the pump

            volume (float): Volume to deliver

            out_valve (Optional[str], optional): Output valve.
            Defaults to cst.OUTLET.

            speed_out (Optional[float], optional): Speed to deliver.
            Defaults to cst.DEFAULT_PUMP_SPEED.
        """

        # Get the pump object
        pump = self.get_pump_obj(name)

        # Deliver the volume
        pump.deliver(volume, to_valve=out_valve, speed_out=speed_out)

    def transfer(
        self,
        name: str,
        volume: float = 0,
        in_valve: Optional[str] = cst.INLET,
        out_valve: Optional[str] = cst.OUTLET,
        speed_in: Optional[int] = cst.DEFAULT_PUMP_SPEED,
        speed_out: Optional[int] = cst.DEFAULT_PUMP_SPEED
    ):
        """Transfers a volume from one valve to another

        Args:
            name (str): Name of the pump
            volume (float, optional): Volume to dispense. Defaults to 0.
            in_valve (str, optional): Valve to pump from. Defaults to cst.INLET.
            out_valve (str, optional): Valve to dispense to.
                                        Defaults to cst.OUTLET.
        """

        # Get pump object and transfer volume
        pump = self.get_pump_obj(name)

        pump.transfer(
            volume, in_valve, out_valve, speed_in=speed_in, speed_out=speed_out
        )

    def wait_until_pumps_idle(self):
        """Waits until all pumps have finished their respective operations
        """

        # Get all pump objects
        pumps = self.controller.get_pumps(self.controller.pumps)

        # Wait until each pump is finished it's current operation
        for pump in pumps:
            pump.wait_until_idle()

    def partial_dispense(
        self,
        name: str,
        volume_in: Optional[float] = 0,
        volume_out: Optional[float] = 0,
        in_valve: Optional[str] = 'I',
        out_valve: Optional[str] = 'O',
        speed_in: Optional[int] = cst.DEFAULT_PUMP_SPEED,
        speed_out: Optional[int] = cst.DEFAULT_PUMP_SPEED
    ) -> float:
        """Performs a partial dispense from a pump.
        Allows the user to take in a set volume and deliver a different volume
        E.g. Take in 5ml and deliver 3ml.

        Args:
            name (str): Name of the pump
            volume_in (float, optional): Volume to pump. Defaults to 0.
            volume_out (float, optional): Volume to deliver. Defaults to 0.
            in_valve (str, optional): In valve. Defaults to 'I'.
            out_valve (str, optional): Out valve. Defaults to 'O'.

        Raises:
            Exception: Invalid dispense request

        Returns:
            float: Remaining volume
        """
        # Get the Pump
        pump = self.get_pump_obj(name)

        # Volume in less than out, delivering remaining volume
        if volume_in < volume_out:
            # Get the current pump volume
            current_volume = pump.get_volume()

            # The volume to dispense out is valid
            if volume_out <= current_volume:
                pump.deliver(
                    volume_out, out_valve, speed_out=speed_out, wait=True
                )
                return

            # Volume is invalid
            raise Exception(
                f'Cannot dispense. In: {volume_in} Out: {volume_out}'
            )

        # Take in the volume
        pump.pump(volume_in, in_valve, wait=True, speed_in=speed_in)

        # Deliver the volume
        pump.deliver(volume_out, out_valve, wait=True, speed_out=speed_out)

        # Return the difference
        return volume_in - volume_out

    def dispense_reagents(
        self,
        *reagents: List[Union[Tuple[str, int, str, str], Reagent]]
    ):
        """Dispenses reagents sequentially
        Allows support betwen Tuples and Reagent class

        Arguments:
            *reagents (list): List of reagents
        """

        # Dispense each reagent using the transfer method
        for reagent in reagents:
            # If the reagent is a Reagent class
            # Convert to a tuple
            if isinstance(reagent, Reagent):
                reagent = reagent.as_tuple()

            # Transfer the contents
            self.transfer(*reagent)

    def set_pump_speed(self, name: str, new_speed: int):
        """Sets the speed of a pump

        Args:
            name (str): Name of the pump
            new_speed (int): Speed to set
        """

        pump = self.get_pump_obj(name)
        pump.set_default_top_velocity(new_speed)
        pump.set_top_velocity(new_speed)

    def adjust_pH(
        self,
        acid_or_base_pump: str,
        volume: float,
        dilution_factor: Optional[float] = 1.0,
        inlet_valve: Optional[str] = "E",
        outlet_valve: Optional[str] = "I",
        water_valve: Optional[str] = "O"
    ):
        """Adjusts the pH of solution by dispensing acid/base with a water
        dilution factor.

        Args:
            acid_or_base_pump (str): Name of the acid or base pump.

            volume (float): Volume to dispense.

            dilution_factor (Optional[float], optional): Dilution factor.
            Defaults to 1.0.

            inlet_valve (Optional[str], optional): Acid/base inlet valve.
            Defaults to "E".

            outlet_valve (Optional[str], optional): Outlet valve.
            Defaults to "I".

            water_valve (Optional[str], optional): Water inlet valve.
            Defaults to "O".
        """

        pump = self.get_pump_obj(acid_or_base_pump)
        max_volume = pump.total_volume

        while volume > 0:
            dispense_volume = max_volume if volume > max_volume else volume

            solution_vol = dispense_volume * dilution_factor
            water_volume = dispense_volume * (1 - dilution_factor)

            pump.pump(solution_vol, from_valve=inlet_valve, wait=True)
            pump.pump(water_volume, from_valve=water_valve, wait=True)
            pump.deliver(dispense_volume, to_valve=inlet_valve, wait=True)

            volume -= volume
