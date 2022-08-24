"""
.. module:: custom.creator
    :synopsis: Module for loading in custom JSON experiment to perform
    :platforms: Unix

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

# System imports
from pathlib import Path
from typing import Dict

# Platform imports
import nanobot.constants as cst
from modularwheel.utils import write_json, read_json

# Locations
HERE = Path('.').absolute()
DATA = HERE.joinpath("data")

class InvalidInputFileException(Exception):
    """Exception for invalid input files
    """

class CustomCreator:
    """Class for laoding in a JSON file and creating an experiment hierarchy
    based off of the contents.

    Args:
        info (Dict) :Experimental Information
        xp_file: (str): JSON file to load
    """

    def __init__(self, info: Dict, input_file: str):
        self.info = info
        self.xp_data = self._check_file(input_file)
        self.xp_path = self.generate_xp_path()

    def _check_file(self, input_file: str) -> Dict:
        """Checks the input file is a JSON file. Reads contents and returns
        if successful, raise exception if not.

        Args:
            xp_file (str): Input file to check

        Raises:
            InvalidInputFileException: File is not a JSON file

        Returns:
            Dict: Input file contents
        """

        # Convert Input filepath to Path
        input_file = Path(input_file)

        # Check it ends with JSON, if not raise exception
        if not Path(input_file).suffix == '.json':
            raise InvalidInputFileException(
                f'Invalid file: {input_file} is not a JSON file'
            )

        # Read the contents and return
        return read_json(input_file)

    def generate_xp_path(self) -> Path:
        """Generates the folder for the experiment

        Returns:
            Path: Experiment path
        """

        # Create paths to check for
        custom_dir = DATA.joinpath('custom')
        xp_path = custom_dir.joinpath(self.info[cst.TITLE])

        # Create `custom` directory if it doesn't exist
        if not custom_dir.exists():
            custom_dir.mkdir()

        # Create experiment path if it doesn't exist
        if not xp_path.exists():
            xp_path.mkdir()

        # Return the path
        return xp_path

    def create_generation(self):
        """Create the generation folder heirarchy
        """

        # Enumerate through input file data
        for i, (_, data) in enumerate(self.xp_data.items()):
            # Create a folder for the experiment
            xp_path = self.xp_path.joinpath(f'{i:04d}')
            xp_path.mkdir()

            # Write the contents to a `params.json` file in the folder
            params_file = xp_path.joinpath(cst.PARAMS_FILE)
            write_json(data, params_file)
