"""
Module contains various utility function for spectral data processing and
analysis.
"""

import numpy as np
import scipy

from .utils import find_nearest_value_index


def create_binary_peak_map(data):
    """ Return binary map of the peaks within data points.

    True values are assigned to potential peak points, False - to baseline.

    Args:
        data (:obj:np.array): 1D array with data points.

    Returns:
        :obj:np.array, dtype=bool: Mapping of data points, where True is
            potential peak region point, False - baseline.
    """
    # copying array
    data_c = np.copy(data)

    # placeholder for the peak mapping
    peak_map = np.full_like(data_c, False, dtype=bool)

    for _ in range(100500): # shouldn't take more iterations

        # looking for peaks
        peaks_found = np.logical_or(
            data_c > np.mean(data_c) + np.std(data_c)*3,
            data_c < np.mean(data_c) - np.std(data_c)*3
        )

        # merging with peak mapping
        np.logical_or(peak_map, peaks_found, out=peak_map)

        # if no peaks found - break
        if not peaks_found.any():
            break

        # setting values to 0 and iterating again
        data_c[peaks_found] = 0

    return peak_map

def combine_map_to_regions(mapping):
    """ Combine True values into their indexes arrays.

    Args:
        mapping (:obj:np.array): Boolean mapping array to extract the indexes
            from.

    Returns:
        :obj:np.array: 2D array with left and right borders of regions, where
            mapping is True.

    Example:
        >>> combine_map_to_regions(np.array([True, True, False, True, False]))
        array([[0, 1],
                [3, 3]])
    """

    # No peaks identified, i.e. mapping is all False
    if not mapping.any():
        return np.array([], dtype='int64')

    # region borders
    region_borders = np.diff(mapping)

    # corresponding indexes
    border_indexes = np.argwhere(region_borders)

    lefts = border_indexes[::2]+1 # because diff was used to get the index

    # edge case, where first peak doesn't have left border
    if mapping[border_indexes][0]:
        # just preppend 0 as first left border
        # mind the vstack, as np.argwhere produces a vector array
        lefts = np.vstack((0, lefts))

    rights = border_indexes[1::2]

    # another edge case, where last peak doesn't have a right border
    if mapping[-1]: # True if last point identified as potential peak
        # just append -1 as last peak right border
        rights = np.vstack((rights, -1))

    # columns as borders, rows as regions, i.e.
    # :output:[0] -> first peak region
    return np.hstack((lefts, rights))

def filter_regions(x_data, peaks_regions):
    """ Filter peak regions.

    Peak regions are filtered to remove potential false positives (e.g. noise
        spikes).

    Args:
        x_data (:obj:np.array): X data points, needed to pick up the data
            resolution and map the region indexes to the corresponding data
            points.
        y_data (:obj:np.array): Y data points, needed to validate if the peaks
            are actually present in the region and remove invalid regions.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).

    Returns:
        :obj:np.array: 2D Mx2 array with filtered peak regions indexes(rows) as
            left and right borders (columns).
    """

    # filter peaks where region is smaller than spectrum resolution
    # like single spikes, e.g. noise
    # compute the regions first
    x_data_regions = np.copy(x_data[peaks_regions])

    # get arguments where absolute difference is greater than data resolution
    resolution = np.absolute(np.mean(np.diff(x_data)))

    # (N, 1) array!
    valid_regions_map = np.absolute(np.diff(x_data_regions)) > resolution

    # get their indexes, mind the flattening of all arrays!
    valid_regions_indexes = np.argwhere(valid_regions_map.flatten()).flatten()

    # filtering!
    peaks_regions = peaks_regions[valid_regions_indexes]

    return peaks_regions

def filter_noisy_regions(y_data, peaks_regions):
    """ Remove noisy regions from given regions array.

    Peak regions are filtered to remove false positive noise regions, e.g.
        incorrectly assigned due to curvy baseline. Filtering is performed by
        computing average peak points/data points ratio.

    Args:
        y_data (:obj:np.array): Y data points, needed to validate if the peaks
            are actually present in the region and remove invalid regions.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).

    Returns:
        :obj:np.array: 2D Mx2 array with filtered peak regions indexes(rows) as
            left and right borders (columns).
    """

    # compute the actual regions data points
    y_data_regions = []
    for region in peaks_regions:
        y_data_regions.append(
            y_data[region[0]:region[-1]]
        )

    # compute noise data regions, i.e. in between peak regions
    noise_data_regions = []
    for row, _ in enumerate(peaks_regions):
        try:
            noise_data_regions.append(
                y_data[peaks_regions[row][1]:peaks_regions[row+1][0]]
            )
        except IndexError:
            # exception for the last row -> discard
            pass

    # compute average peaks/data points ratio for noisy regions
    noise_peaks_ratio = []
    for region in noise_data_regions:
        # protection from empty regions
        if region.size != 0:
            # minimum height is pretty low to ensure enough noise is picked
            peaks, _ = scipy.signal.find_peaks(region, height=region.max()*0.2)
            noise_peaks_ratio.append(peaks.size/region.size)

    # compute average with weights equal to the region length
    noise_peaks_ratio = np.average(
        noise_peaks_ratio,
        weights=[region.size for region in noise_data_regions]
    )

    # filtering!
    valid_regions_indexes = []
    for row, region in enumerate(y_data_regions):
        peaks, _ = scipy.signal.find_peaks(region, height=region.max()*0.2)
        if peaks.size != 0 and peaks.size/region.size < noise_peaks_ratio:
            valid_regions_indexes.append(row)

    # protecting from complete cleaning
    if not valid_regions_indexes:
        return peaks_regions

    peaks_regions = peaks_regions[np.array(valid_regions_indexes)]

    return peaks_regions

def merge_regions(x_data, peaks_regions, d_merge, recursively=True):
    """ Merge peak regions if distance between is less than delta.

    Args:
        x_data (:obj:np.array): X data points.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).
        d_merge (float): Minimum distance in X data points to merge two or more
            regions together.
        recursively (bool, optional): If True - will repeat the procedure until
            all regions with distance < than d_merge will merge.

    Returns:
        :obj:np.array: 2D Mx2 array with peak regions indexes (rows) as left and
            right borders (columns), merged according to predefined minimal
            distance.

    Example:
        >>> regions = np.array([
                [1, 10],
                [11, 20],
                [25, 45],
                [50, 75],
                [100, 120],
                [122, 134]
            ])
        >>> data = np.ones_like(regions) # ones as example
        >>> merge_regions(data, regions, 1)
        array([[  1,  20],
               [ 25,  45],
               [ 50,  75],
               [100, 120],
               [122, 134]])
        >>> merge_regions(data, regions, 20, True)
        array([[  1,  75],
               [100, 134]])
    """
    # the code is pretty ugly but works
    merged_regions = []

    # converting to list to drop the data of the fly
    regions = peaks_regions.tolist()

    for i, _ in enumerate(regions):
        try:
            # check left border of i regions with right of i+1
            if abs(x_data[regions[i][-1]] - x_data[regions[i+1][0]]) <= d_merge:
                # if lower append merge the regions
                merged_regions.append([regions[i][0], regions[i+1][-1]])
                # drop the merged one
                regions.pop(i+1)
            else:
                # if nothing to merge, just append the current region
                merged_regions.append(regions[i])
        except IndexError:
            # last row
            merged_regions.append(regions[i])

    merged_regions = np.array(merged_regions)

    if not recursively:
        return merged_regions

    # if recursively, check for the difference
    if (merged_regions == regions).all():
        # done
        return merged_regions

    return merge_regions(x_data, merged_regions, d_merge, recursively=True)

def expand_regions(x_data, peaks_regions, d_expand):
    """ Expand the peak regions by the desired value.

    Args:
        x_data (:obj:np.array): X data points.
        peaks_regions (:obj:np.array): 2D Nx2 array with peak regions indexes
            (rows) as left and right borders (columns).
        d_expand (float): Value to expand borders to (in X data scale).

    Returns:
        :obj:np.array: 2D Nx2 array with expanded peak regions indexes (rows) as
            left and right borders (columns).
    """

    data_regions = np.copy(x_data[peaks_regions])

    # determine scale orientation, i.e. decreasing (e.g. ppm on NMR spectrum)
    # or increasing (e.g. wavelength on UV spectrum)
    if (data_regions[:, 0] - data_regions[:, 1]).mean() > 0:
        # ppm-like scale
        data_regions[:, 0] += d_expand
        data_regions[:, -1] -= d_expand
    else:
        # wavelength-like scale
        data_regions[:, 0] -= d_expand
        data_regions[:, -1] += d_expand

    # converting new values to new indexes
    for index_, value in np.ndenumerate(data_regions):
        data_regions[index_] = find_nearest_value_index(x_data, value)[1]

    return data_regions.astype(int)
