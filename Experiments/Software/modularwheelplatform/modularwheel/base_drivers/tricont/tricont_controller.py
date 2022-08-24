"""
.. module:: tricont_controller
    :platform: Unix, Windows
    :synopsis: Base driver for interfacing with Tricontinent C3000 pumps
                via PyCont

.. moduleauthor:: Graham Keenan 2019

"""

import logging
from pycont.controller import MultiPumpController

logging.basicConfig(level=logging.INFO)


class UndefinedPumpError(Exception):
    """Exception for handling an undefined pump in the controller
    """

class TricontCoreDriver:
    """Core driver for initialising PyCont

    Args:
        config (dict): PyCont config
    """

    def __init__(self, config: dict):
        # Create the controller
        self.controller = MultiPumpController(config)

        # Set the config
        self.config = config

        # Initialise all pumps
        self.controller.smart_initialize()

        # Reset the position to zero
        self._reset_position()

    def _reset_position(self):
        """Resets all pumps back to zero
        """

        # Get all pump objects
        pumps = self.controller.get_pumps(
            self.controller.pumps
        )

        # Reset each pump
        for pump in pumps:
            pump.go_to_volume(0)

    def get_pump_obj(self, pump_name: str):
        """Gets the Tricont pump object from the PyCont Controller

        Args:
            pump_name (str): Name of the pump

        Raises:
            UndefinedPumpError: Pump is not recognised

        Returns:
            C3000Controller: PuCont pump object
        """

        try:
            return getattr(self.controller, pump_name)
        except AttributeError:
            raise UndefinedPumpError(
                f"Cannot find pump {pump_name} in the PyCont controller!"
            )
