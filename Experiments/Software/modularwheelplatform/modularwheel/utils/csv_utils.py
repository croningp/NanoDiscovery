"""
.. module:: csv_utils
    :platform: Unix, Windows
    :synopsis: Wrappers for CSV reading/writing

.. moduleauthor:: Graham Keenan 2019

"""

import csv

def read_csv(filename: str, delimiter: str = ",") -> (list, list):
    """Reads a CSV file, returning column names and data

    Args:
        filename (str): Name of the csv file
        delimiter (str, optional): Default delimiter for csv format.
                                    Defaults to ",".

    Returns:
        (list, list): Column names and data
    """

    with open(filename) as f_d:
        reader = csv.reader(f_d, delimiter=delimiter)
        data = [row for row in reader]
        header = data.pop(0)

    return header, data


def write_csv(header: list, data: list, filename: str, delimiter: str = ","):
    """Writes data to a CSV file

    Args:
        header (list): Column names
        data (list): Data to write
        filename (str): Name of the file
        delimiter (str, optional): Default delimiter for csv format.
                                    Defaults to ",".
    """

    with open(filename, "w") as f_d:
        writer = csv.writer(f_d, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(data)
