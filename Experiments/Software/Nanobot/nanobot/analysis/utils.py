import numpy as np

def find_nearest_value_index(array, value):
    """Returns closest value and its index in a given array.

    Args:
        array (:obj: np.array(float)): An array to search in.
        value (float): Target value.

    Returns:
        Tuple[float, int]: Nearest value in array and its index.
    """

    index_ = np.argmin(np.abs(array - value))
    return (array[index_], index_)

def interpolate_to_index(array, ids, precision=100):
    """Find value in between arrays elements.

    Constructs linspace of size "precision" between index+1 and index to
    find approximate value for array[index], where index is float number.
    Used for 2D data, where default scipy analysis occurs along one axis only,
    e.g. signal.peak_width.

    Rough equivalent of array[index], where index is float number.

    Args:
        array (:obj: np.array[float]): Target array.
        ids (:obj: np.array[float]): An array with "intermediate" indexes to
            interpolate to.
        precision (int): Desired presion.

    Returns:
        (:obj: np.array): New array with interpolated values according to
            provided indexes "ids".

    Example:
        >>> interpolate_to_index(np.array([1.5]), np.array([1,2,3], 100))
            array([2.50505051])
    """

    # breaking ids into fractional and integral parts
    prec, ids = np.modf(ids)

    # rounding and switching type to int
    prec = np.around(prec*precision).astype('int32')
    ids = ids.astype('int32')

    # linear interpolation for each data point
    # as (n x m) matrix where n is precision and m is number of indexes
    space = np.linspace(array[ids], array[ids+1], precision)

    # due to rounding error the index may become 100 in (100, ) array
    # as a consequence raising IndexError when such array is indexed
    # therefore index 100 will become the last (-1)
    prec[prec == 100] = -1

    # precise slicing
    true_values = np.array([
        space[:, index[0]][value]
        for index, value in np.ndenumerate(prec)
    ])

    return true_values
