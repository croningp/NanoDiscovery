"""
.. module:: heimdall
    :platforms: Unix, Windows
    :synopsis: Watcher file that creates and watches all experiment folders
                created by the algorithms

.. moduleauthor:: Graham Keenan (Cronin Lab 2019)

"""

# System imports
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict
from argparse import ArgumentParser
from multiprocessing import Process

# Platform imports
from modularwheel.utils import read_json

# Locations
HERE = Path('.').absolute()
ALGORITHMS = HERE.joinpath("algorithms")
EXPERIMENTS = HERE.joinpath('experiments')

# Supported Algorithms
GA = "GA"
BAYES = "bayesian"
BASIC = "basic"
CUSTOM = 'custom'

# Add a logger
logger = logging.getLogger('Heimdall')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s::%(levelname)s - %(message)s',
    datefmt='%d-%m-%Y %H%M'
)

class UnsupportedAlgorithm(Exception):
    """Exception when algorithm is not supported
    """


def get_watchers(info: dict, alg_type: str) -> Optional:
    """
    Gets the Creators and Watchers for the experimental run
    Type of Creator and Watcher depend on the type of algorithm in use

    Args:
        info (Dict): Information about the current experiment

    Returns:
        creator (Creator): Folder generator and assessor of the experiment
        watcher (Watcher): File watcher for the experiment
    """

    # Genetic algorithm
    if alg_type == GA:
        from algorithms import GeneticWatcher, GeneticCreator

        return GeneticCreator(info), GeneticWatcher(info)

    # Basic experiment (No algorithm)
    if alg_type == BASIC:
        from algorithms import BasicExperimentCreator

        return BasicExperimentCreator(info)

    # Bayesian algorithm
    if alg_type == BAYES:
        from algorithms import BayesianCreator, BayesianWatcher

        return BayesianCreator(info), BayesianWatcher(info)

    raise UnsupportedAlgorithm(f'Algorithm "{alg_type}" is not supported.')


def guard_the_genetic_realm(info: Dict):
    """Manages the processes of Creator and Watcher for the Genetic Algorithm

    Arguments:
        info (Dict): Experimental information file
    """

    creator, watcher = get_watchers(info, GA)

    creator_process = Process(target=creator.initialise, args=())
    watcher_process = Process(target=watcher.parse_experiment, args=())

    logger.info("Starting Genetic Creator and Genetic Watcher processes...")
    creator_process.start()
    time.sleep(2)  # Give short pause to let folder be created
    watcher_process.start()

    creator_process.join()
    watcher_process.join()
    logger.info(
        "Successfully joined Genetic Creator and Genetic Watcher processes."
    )


def guard_the_basic_realm(info: Dict):
    """Calls the single experiment creator to create a single experimental
    run of X reactions

    Arguments:
        info {dict} -- Experimental information file
    """

    creator = get_watchers(info, BASIC)

    logger.info("Creating single experiment...")
    creator.create_generation()


def guard_the_bayesian_realm(info: Dict):
    """Launches the Bayesian Creator and Bayesian Watchers

    Args:
        info (Dict): Experimental info
    """

    creator, watcher = get_watchers(info, BAYES)

    cp = Process(target=creator.initialise, args=())
    wp = Process(target=watcher.initialise, args=())

    logger.info('Launching Bayesian Creator and Bayesian Watcher.')
    cp.start()
    time.sleep(2)  # Pause to allow for the experiment folder to be created
    wp.start()

    cp.join()
    wp.join()
    logger.info('Successfully joined Bayesian Creatotr and Bayesian Watcher.')

def guard_the_custom_realm(info: Dict, file_to_load: str):
    """Launches the Custom generation creator

    Args:
        info (Dict): Experimentan info
        file_to_load (str): Input File
    """

    from algorithms import CustomCreator
    creator = CustomCreator(info, file_to_load)

    logger.info(f'Creating custom experiment using file: {file_to_load}')
    creator.create_generation()


def guard_the_realm():
    """Creates watchers and generation managers dependent on algorithm choice
    """

    # Argument parser for easier loading
    parser = ArgumentParser()

    # `--genetic` for GA
    parser.add_argument(
        '--genetic', help='Run the Genetic Algorithm', action='store_true'
    )

    # `--bayes` for Bayesian Optimisation/Exploration
    parser.add_argument(
        '--bayes', help='Run the Bayesian Algorithm', action='store_true'
    )

    # `--basic` for the basic experiment
    parser.add_argument(
        '--basic', help='Run the Basic system', action='store_true'
    )

    # `--custom [input_file] for loading a custom file`
    parser.add_argument(
        '--custom',
        help='Load a JSON file for experiments to perform',
    )

    # Parse args
    args = parser.parse_args()

    # Read in the information file
    info = read_json(
        os.path.join(
            EXPERIMENTS, 'configs', 'experimental_information.json'
        )
    )

    # Do Genetic
    if args.genetic:
        guard_the_genetic_realm(info)

    # Do Basic
    if args.basic:
        guard_the_basic_realm(info)

    # Do Bayes
    if args.bayes:
        guard_the_bayesian_realm(info)

    # Do Custom
    if args.custom:
        guard_the_custom_realm(info, args.custom)


if __name__ == "__main__":
    guard_the_realm()
