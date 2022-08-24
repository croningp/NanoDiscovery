"""
.. module:: bayesian.watcher
    :platforms: Unix, Windows
    :synopsis: Watcher file for processing shape metric data for the Bayesian
                Optimiser.

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

# System Imports
import time
from pathlib import Path
from typing import Dict, List

# Platform imports
import nanobot.constants as cst
from .analysis import obtain_metrics
from modularwheel.utils import read_json, write_json

# Locations
HERE = Path('.').absolute()
DATA = HERE.joinpath('..', '..', 'data')
BAYES = DATA.joinpath('bayes')


def get_folders(path: str) -> List[str]:
    """Get all folders and subfolders within a given path

    Args:
        path (str): Target path

    Returns:
        List[str]: List of all folders within a target path
    """

    return sorted([
        file for file in path.iterdir()
        if file.is_dir()
    ])


def get_files(path: str) -> List[str]:
    """Get all files within a directory

    Args:
        path (str): Target directory

    Returns:
        List[str]: All files within the directory
    """

    return sorted([
        file for file in path.iterdir()
        if file.is_file()
    ])


def wait_until_file_ready(path: str, wait: float = 0.5):
    """Waits until a given file exists

    Args:
        path (str): File to check
        wait (float, optional): Default wait time. Defaults to 0.5.
    """

    while not path.exists():
        time.sleep(wait)


class BayesianWatcher:
    """Watcher class that will look over all batches and process the UV data
    of each experiment to obtain a metric for that experiment.
    These are written to each batch and the Creator will updat the optimiser.

    Args:
        info (Dict): Experimental information file
    """

    def __init__(self, info: Dict):
        # Info
        self.info = info

        # List to hold the metrics for each XP in a batch
        self.batch_metrics = []

        # Root XP path
        self.xp_path = BAYES.joinpath(self.info[cst.TITLE])

    def watch_batch(self, batch_path: str):
        """Watches a batch by checking each experiment within it for UV data

        Args:
            batch_path (str): batch to watch
        """

        # Get all XP folders
        xp_folders = get_folders(batch_path)

        # Read in the Seed UV data for this batch
        seeds_uv = read_json(batch_path.joinpath(cst.SEEDS_UV_JSON))

        # Iterate through each experiment
        for xp_folder in xp_folders:
            # Obtain the metric for the experiment
            self.watch_xp(xp_folder, seeds_uv)

        # Write metrics to disk and reset
        self.write_metrics(batch_path)

    def watch_xp(self, xp_folder: str, seeds_uv: Dict):
        """Checks the curent XP folder for the UV file.
        When it is found, calculate the shape metric based on the observed data
        and seed data supplied.

        Args:
            xp_folder (str): XP folder to watch
            seeds_uv (Dict): Seed UV data for the batch
        """

        # Get paths for the UV file and metric file
        uv_file = xp_folder.joinpath(cst.UV_JSON)
        metric_file = xp_folder.joinpath(cst.METRIC_FILE)

        # Wait until the UV file is present
        wait_until_file_ready(uv_file)

        # Read in the UV data
        uv_data = read_json(uv_file)

        # TODO::SOME MAGIC REQUIRED BELOW
        scores, _ = obtain_metrics(seeds_uv, uv_data)
        metric = {
            'metric': scores
        }
        # TODO::SOME MAGIC REQUIRED ABOVE

        # Add experiment metric to list
        self.batch_metrics.append(scores)

        # Write metric to disk
        write_json(metric, metric_file)

    def write_metrics(self, batch_path: str):
        """Simple wrapper for writing batch metrics to disk and resetting

        Args:
            batch_path (str): Path to current batch
        """

        # Mettric filepath and data
        metric_file = batch_path.joinpath(cst.BATCH_METRIC_FILE)
        metrics = {
            'metrics': self.batch_metrics
        }

        # Write to disk
        write_json(metrics, metric_file)

        # Reset metrics for next batch
        self.batch_metrics = []

    def initialise(self):
        """Entry point for the watcher
        Watch all batches and get metric data
        """

        # Get all batch folders
        batch_folders = get_folders(self.xp_path)

        # Iterate through each batch
        for batch_path in batch_folders:
            # Process the data within
            self.watch_batch(batch_path)
