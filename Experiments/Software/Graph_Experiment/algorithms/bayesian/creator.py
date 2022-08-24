"""
.. module:: bayesian.creator
    :platforms: Unix, Windows
    :synopsis: Experimental creator using the Bayesian Optimiser

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

# System imports
import time
import logging
from pathlib import Path
from typing import Dict, Tuple, Iterable

# Platform imports
import nanobot.constants as cst
from .analysis import BayesianOptimiser
from modularwheel.utils import write_json, read_json

# Library imports
import numpy as np

# Locations
HERE = Path('.').absolute()
DATA = HERE.joinpath('..', '..', 'data')
BAYES = DATA.joinpath('bayes')


def normalise_parameters(
    varied_values: np.ndarray,
    static_volume_total: float,
    normalisation_volume: float = 10
) -> np.ndarray:
    """Normalise experimental parameters to a set voluem so they can be
    dispensed easily

    Args:
        varied_values (np.ndarray): Values to normalise
        static_volume_total (float): Volume of static reagents (Never change)
        normalisation_volume (float, optional): Total volume. Defaults to 10.

    Returns:
        np.ndarray: Normalised values
    """

    target_volume = normalisation_volume - static_volume_total
    return (varied_values / np.sum(varied_values)) * target_volume


def create_folder(root: str, *paths: Iterable[str]) -> str:
    """Builds a path and creates the folder

    Args:
        root (str): Root path
        paths (Iterable[str]): Iterable of paths to build

    Returns:
        str: Created path
    """

    # Build path
    path = root.joinpath(*paths)

    # Create if not existing already
    if not path.exists():
        path.mkdir()

    return path


class BayesianCreator:
    """Creator class for the Bayesian Optimiser
    Orchestrates the creation of new batch folders and new experiment folders
    for each experiment in a batch.
    Updates the optimiser when the metric files have been processed

    Args:
        info (Dict): Experimental Information file
    """

    def __init__(self, info: Dict):
        # Experimental info
        self.info = info
        self.bayes_info = self.info['bayesian']

        # Total number of batches to run for
        self.total_batches = self.info[cst.GENS]

        # Root experiment path
        self.xp_path = create_folder(BAYES, self.info[cst.TITLE])

        # Optimiser
        self.optimiser = BayesianOptimiser(self.bayes_info['params'])

        # Initialise a logger
        self.logger = logging.getLogger('BayesianCreator')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s::%(levelname)s - %(message)s',
            datefmt='%d-%m-%Y %H%M',
            force=True
        )

    def create_batch(self, batch_number: int, batch_values: np.ndarray) -> str:
        """Creates teh batch folder and all experiments within

        Args:
            batch_number (int): Current batch number
            batch_values (np.ndarray): Experimental values for the experiments

        Returns:
            str: Path to the batch folder
        """

        # Create batch folder
        batch_path = create_folder(self.xp_path, f'batch_{batch_number:04d}')
        self.logger.info(f'Creating batch: {batch_path}')

        # Iterate through all experiments in the batch
        for xp_num, xp_values in enumerate(batch_values):
            # Create a folder for the experiment
            self.create_individual_experiment(batch_path, xp_num, xp_values)

        return batch_path

    def create_individual_experiment(
        self, batch_path: str, xp_num: int, xp_values: np.array
    ):
        """Creates the experiment folder and the `params.json` and
        `raw_params.json` file for an experiment.

        Args:
            batch_path (str): Path to the batch folder
            xp_num (int): Current experiment number
            xp_values (np.array): Values for the experiment
        """

        # Create the XP path
        xp_path = create_folder(batch_path, f'xp_{xp_num:04d}')

        # Get the parameters
        params, raw_params = self.create_parameters(xp_values)

        # Write parameters to XP folder
        params_path = xp_path.joinpath(cst.PARAMS_FILE)
        write_json(params, params_path)

        # Write raw parameters to XP folder
        params_path = params_path.replace(cst.PARAMS_FILE, 'raw_params.json')
        write_json(raw_params, params_path)

        self.logger.debug(
            f'Created XP {xp_path} with parameters {params}\
 (Raw Params: {raw_params})')

    def create_parameters(
        self, xp_values: np.array
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Creates the parameter and raw parameter dictionaries to be written
        to disk

        Args:
            xp_values (np.array): Values for the experiment

        Returns:
            Tuple[Dict[str, float], Dict[str, float]]: Parameters (Normalised)
                            and raw parameters (No Normalisation)
        """

        # Get the static reagents and values and the varied reagent names
        static = self.bayes_info[cst.STATIC]
        varied = self.bayes_info[cst.VARIED]

        # Normalise the varied reagents against the staitc reagents
        normalised_values = normalise_parameters(
            xp_values, sum(static.values())
        )

        # Build params dict
        params = {
            **static, **{
                name: norm for name, norm in zip(varied, normalised_values)
            }
        }

        # Build raw params dict (No normalisation)
        raw_params = {
            **static, **{
                name: raw for name, raw in zip(varied, xp_values)
            }
        }

        return params, raw_params

    def update_optimiser(self, batch_values: np.ndarray, metric_path: str):
        """Updates the optimiser with the experimental values and scores for
        each experiment.

        Args:
            batch_values (np.ndarray): Experiment values (X)
            metric_path (str): Experiment scores (y)
        """

        # Wait for the metric file to exist
        while not metric_path.exists():
            self.logger.debug(f'Waiting on {metric_path}')
            time.sleep(0.5)

        # Read in the metrics and update the optimiser
        metrics = np.asarray(read_json(metric_path)['metrics'])
        self.optimiser.update(batch_values, metrics)

        self.logger.info('Successfully updated optimiser')

    def initialise(self):
        """Entry point for the creator
        Creates the batches and experiments.
        """

        # Iterate through the total number of batches for the experiment
        for batch_num in range(self.total_batches):
            # Get values from the optimiser (random if the first batch)
            batch_values = (
                self.optimiser.request_initial_batch() if batch_num == 0
                else self.optimiser.request_next_batch()
            )

            # Create the batch
            batch_path = self.create_batch(batch_num, batch_values)

            # Path to metrics file
            metric_path = batch_path.joinpath(cst.BATCH_METRIC_FILE)

            # Update the optimiser when metrics are available
            self.update_optimiser(batch_values, metric_path)
