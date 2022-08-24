"""
.. module:: triconts
    :platform: Unix, Windows
    :synopsis: Module for interfacing with Tricontinent C3000 pumps using PyCont

.. moduleauthor:: Graham Keenan (Cronin Lab 2019)

"""

import logging
from pycont.controller import MultiPumpController

def tricont_initialisation(config: dict) -> MultiPumpController:
    """Initialises the PyCont controller with the given configuration

    Args:
        config (dict): PyCont config

    Returns:
        MultiPumpController: PyCont controller for the pumps
    """

    # Initialise the controller
    logging.basicConfig(level=logging.INFO)
    controller = MultiPumpController.from_config(config)

    # Initialise all pumps defined in the configuration
    controller.smart_initialize()

    # Reset the pumps back to 0
    pumps = controller.get_pumps(controller.pumps)
    for pump in pumps:
        pump.go_to_volume(0)

    return controller
