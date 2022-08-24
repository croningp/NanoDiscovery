"""
.. module:: genetic.watcher
    :platforms: Unix, Windows
    :synopsis: Watches XP folders and calculates the fitness for the GA

.. moduleauthor:: Graham Keenan (Cronin Lab 2019)

"""

# System imports
import time
import logging
from pathlib import Path
from typing import Dict, List, Union

# Platform imports
from .fitness import octahedron_fitness
import nanobot.constants as cst
from modularwheel.utils import read_json, write_json

# Locations
HERE = Path('.').absolute()
DATA = HERE.joinpath('..', '..', 'data')
GENETIC = HERE.joinpath('genetic')


# Objective
TARGET_TO_INCREASE = 553  # 80nm sphere

# Peak to decrease if two peak system
TARGET_TO_DECREASE = 515


class GeneticWatcher:
    """
    Class for watching a series of experiment folders for UV files
    Once they have been found, they are processed and a
    fitness value given to the experiment

    Args:
        info (Dict): Information about the overall experiment
    """

    def __init__(self, info: Dict):
        # Experimental info
        self.info = info

        # Initialise a logger
        self.logger = logging.getLogger('GeneticWatcher')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s::%(levelname)s - %(message)s',
            datefmt='%d-%m-%Y %H:%M',
            force=True
        )

        # Get the current experiment path
        self.xp_path = self.get_xp_path()

        # Generation info
        self.current_generation_number = 0
        self.total_generations = self.info[cst.GENS]

    def get_xp_path(self) -> str:
        """Gets the current experiment folder

        Returns:
            str: Current XP path
        """

        path = DATA.joinpath(self.info[cst.TITLE], str(self.info[cst.SEED]))

        # make if it doesn't exist
        if not path.exists():
            path.mkdir()

        return path

    def parse_experiment(self):
        """Parses all generations in a given experimental run

        Takes a generation and obtains the fitness values for
        each experiment in each
        """
        for _ in range(self.total_generations):
            self.parse_generation()

    def parse_generation(self):
        """
        Watches a single generation folder for UV data
        Parses all experiments and obtains a fitness value for
        each and list of all values for the generation

        Returns:
            fitness_list (List): List of fitness values for each
                                    experiment in the generation
        """

        # Get current generation path
        gen_number = f'{self.current_generation_number:04d}'
        current_generation_path = self.xp_path.joinpath(gen_number)

        # Wait until it the Creator creates the folder
        while not current_generation_path.exists():
            time.sleep(1)

        # Watch the generation folder for a fitness file
        self.logger.info(f'Currently watching generation: {gen_number}.')

        # Already have a fitness, return
        if current_generation_path.joinpath(cst.FITNESS_FILE).exists():
            self.current_generation_number += 1
            self.logger.info(f'Already calculated: {gen_number}.')
            return

        # Go through all XP folders to obtain fitnesses and write to generation
        fitness_list = self.parse_xp_folders(current_generation_path)
        self.write_fitness_to_file(current_generation_path, fitness_list)
        self.current_generation_number += 1

    def parse_xp_folders(self, generation_path: str) -> List[float]:
        """
        Parses all experiments in a generation to get their fitnesses

        Args:
            generation_path (str): Path of the current generation folder

        Returns:
            fitnesses (List[float]): List of all the fitnesses for a generation
        """

        # List for fitnesses
        fitnesses = []

        # Get all XP folders in the current generation path
        xp_folders = sorted([
            folder for folder in generation_path.iterdir()
            if folder.is_dir()
        ])

        # Go through each XP folder and calculate a fitness
        for xp in xp_folders:
            self.logger.info(f'Experiment: {xp}')
            fitness = self.parse_uv_for_fitness(xp)
            self.logger.info(f'Fitness: {fitness}')
            self.write_fitness_to_file(xp, fitness)
            fitnesses.append(fitness)

        return fitnesses

    def parse_uv_for_fitness(self, xp_folder: str) -> float:
        """Waits until a UV file is present and processes it for a fitness value

        Args:
            xp_folder (str): Path of the folder to watch

        Returns:
            fitness (float): Fitness for the experiment
        """

        # Wait until the UV file is ready
        uv_file = xp_folder.joinpath(cst.UV_JSON)
        while not uv_file.exists():
            time.sleep(1)

            # Parse the file and calculatae fitness
        uv_data = self.parse_file(uv_file)
        self.logger.info(f'Calculating fitness of {xp_folder}.')

        return self.calculate_fitness(uv_data)

    def calculate_fitness(self, uv_data: Dict) -> float:
        """Calculates the fitness for a set of UV data

        Args:
            uv_data (Dict): Series of UV data containing
                            wavelength and absorbance

        Returns:
            fitness (float): Fitness value of the UV data
        """

        wavelength = uv_data[cst.WAVELENGTH]
        absorbance = uv_data[cst.ABSORBANCE]

        # Do new fitness here
        # TODO:: Find better way to deal with different shapes and targets
        # return rods_fitness(wavelength, absorbance)
        return octahedron_fitness(wavelength, absorbance)

    def write_fitness_to_file(
        self, xp_path: str, fitness: Union[List[float], float]
    ):
        """Writes the fitness value to the experiment folder

        Args:
            xp_path (str): path to the experiment folder
            fitness (Union[List[float], float]): Fitness value to write
                                                or List of fitnesses
        """

        filename = xp_path.joinpath(cst.FITNESS_FILE)
        data = {'fitness': fitness}
        write_json(data, filename)

    def parse_file(self, path: str) -> Dict:
        """Parses a JSON file

        Args:
            path (str): path to file

        Returns:
            json_data (Dict): JSON data as a dictionary
        """

        # Check if the file is being read or written to
        while self.is_file_busy(path):
            time.sleep(0.5)

        return read_json(path)

    def is_file_busy(self, path: str, modified_time: float = 1.0) -> bool:
        """Checks of a file is currently busy (being written to)

        Args:
            path (str): Path to file
            modified_time (int/float): Time to wait until it is checked after
                                        initial check

        Returns:
            bool: Busy or not
        """

        time_start = path.stat().st_mtime
        time.sleep(modified_time)
        time_end = path.stat().st_mtime

        return time_end > time_start
