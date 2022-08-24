"""JSON Wrappers

.. moduleauthor:: Graham Keenan 2019

"""

import json

def read_json(filename: str) -> dict:
    """Reads a JSON file and returns the data structure

    Args:
        filename (str): Path to the file

    Returns:
        dict: JSON data
    """
    with open(filename) as f_d:
        return json.load(f_d)


def write_json(data: dict, filename: str):
    """Writes a dictionary to JSON file

    Args:
        data (dict): Data to write
        filename (str): Path to the file
    """
    with open(filename, "w") as f_d:
        json.dump(data, f_d, indent=4)
