"""Module for creating a single experiment with parameters
defined in the information file.

Similar implementation to that in the ALC Creator

.. moduleauthor:: Graham Keenan 2019

"""

# System imports
from pathlib import Path
from typing import Dict

# Platform imports
import nanobot.constants as cst
from modularwheel.utils import write_json

# Locations
HERE = Path('.').absolute()
DATA = HERE.joinpath("data")

class BasicExperimentCreator(object):
    """Class for creating a single experiment folder structure

    Pretty much reimplements the ALC creator but for a single run

    Arguments:
        info (Dict): Info from info file
    """

    def __init__(self, info: Dict):
        self.info = info
        self.xp_path = self.generate_xp_path()
        self.params = self.info[cst.BASIC]

    def generate_xp_path(self) -> str:
        """Generates a path to the experiment folder
        Creates the flder if it doesn't exist already

        Returns:
            str -- Experiment path
        """

        path = DATA.joinpath("basic", self.info[cst.TITLE])

        if not path.exists():
            path.mkdir()

        return path

    def create_generation(self):
        """Creates the experiment folder and populates all folders with params.

        Params are defined in the Info file
        """

        print(f"Creating generation: {self.xp_path}")
        for xp_num in range(self.info[cst.XP]):
            # Create XP path
            xp_folder_name = f'{xp_num:04d}'
            xp_folder = self.xp_path.joinpath(xp_folder_name)

            # Create if it doesn't already exist (it wont)
            if not xp_folder.exists():
                xp_folder.mkdir()

            # Write the params file
            params_file = xp_folder.joinpath(cst.PARAMS_FILE)
            write_json(self.params, params_file)
