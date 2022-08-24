"""
.. module:: analysis.optimiser
    :platforms: Unix
    :synopsis: Bayesian Optimiser that allows for exploration and exploitation
    (Adapted from http://krasserm.github.io/2018/03/21/bayesian-optimization/)

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

# System Imports
import logging
from typing import Dict, Optional

# Library imports
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern


# Constants
XI_EXPLORE = 1.0  # Explore the space
XI_EXPLOIT = 0.01  # Exploit a region


def _create_kernel(
    constant: Optional[float] = 1.0,
    length_scale: Optional[float] = 1.0,
    nu: Optional[float] = 1.5,
    noise: Optional[float] = 0.2
) -> GaussianProcessRegressor:
    """Creates the kernel for the Gaussian Regressor

    Args:
        constant (Optional[float], optional): Constant value for the
                                                ConstantKernel. Defaults to 1.0.

        length_scale (Optional[float], optional): Length scale for the Matern
                                                kernel. Defaults to 1.0.

        nu (Optional[float], optional): Nu parameter for the Matern kernel.
                                        Defaults to 1.5.

        noise (Optional[float], optional): Noise parameter for the Gaussian
                                            Process. Defaults to 0.2.

    Returns:
        GaussianProcessRegressor: Kernel of the Optimiser
    """

    kernel = ConstantKernel(constant) * \
        Matern(length_scale=length_scale, nu=nu)

    return GaussianProcessRegressor(kernel=kernel, alpha=noise**2)


class BayesianOptimiser:
    """Custom-built Bayesian Optimiser that allows for exploration of a space
    and exploitation of regions of interest.

    Args:
        params (Dict): Optimiser parameters
    """

    def __init__(self, params: Dict):
        # Experimental values and experimental scores
        self.X_samples = None
        self.Y_samples = None

        # Bounds of the algorithm
        self.bounds = np.array(params['bounds'])

        # Tradeoff parameter
        self.xi = params['xi']

        # How many experiments per batch
        self.batch_size = params['batch_size']

        # Heart of the optimiser - does the optimising
        self.kernel = _create_kernel(**params['kernel'])

        # Initialise a logger
        self.logger = logging.getLogger('BayesianOptimiser')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s::%(levelname)s - %(message)s',
            datefmt='%d-%m-%Y %H:%M',
            force=True
        )

        self.logger.info("Initialised")

    def explore(self, xi: Optional[float] = None):
        """Updates the Xi parameter to widen the optimiser's results
        Higher values means wider exploration.

        Args:
            xi (Optional[float], optional): New value of Xi. Defaults to None.
        """

        # Set to default explore value if not defined
        new_xi = XI_EXPLORE if xi is None else xi
        self.logger.info(f'Switching to exploration (Xi: {new_xi})')
        self.xi = new_xi

    def exploit(self, xi: Optional[float] = None):
        """Updates the Xi parameter to narrow the optimiser's results
        Lower values mean tighter exploitation

        Args:
            xi (Optional[float], optional): New value of Xi. Defaults to None.
        """

        # Set to default exploit value if not defined
        new_xi = XI_EXPLOIT if xi is None else xi
        self.logger.info(f'Switching to exploitation: (Xi: {new_xi})')
        self.xi = new_xi

    def expected_improvement(
        self,
        X: np.ndarray,
        X_sample: np.ndarray,
        Y_sample: np.ndarray,
        noise_based: Optional[bool] = False
    ) -> float:
        """Calculate the expected improvement at points X based on previously
        existing values in X_samples and Y_samples, using a Gaussian Process
        surrogate model.

        Args:
            X (np.ndarray): Points at which the expected improvement will be
                            calculated

            X_sample (np.ndarray): Sample locaitons
            Y_sample (np.ndarray): Sample values
            noise_based (Optional[bool], optional): Model utilises noise.
                                                    Defaults to False.

        Returns:
            float: Expected improvement
        """

        mu, sigma = self.kernel.predict(X, return_std=True)
        mu_sample = self.kernel.predict(X_sample)

        mu_sample_opt = np.max(mu_sample) if noise_based else np.max(Y_sample)

        with np.errstate(divide='warn'):
            improvement = mu - mu_sample_opt - self.xi
            Z = improvement / sigma
            expected_improvement = improvement * \
                norm.cdf(Z) + sigma * norm.pdf(Z)

            expected_improvement[sigma == 0.] = 0.

        self.logger.debug(f'Expected improvement: {expected_improvement}')

        return expected_improvement

    def propose_location(
        self,
        X_sample: np.ndarray,
        Y_sample: np.ndarray,
        n_restarts: Optional[int] = 25
    ) -> np.array:
        """Proposes the next experiment to perform by optimising the
        acqisition function.

        Args:
            X_sample (np.ndarray): Sample locations
            Y_sample (np.ndarray): Sample values
            n_restarts (Optional[int], optional): Number of times to run the
                            optimisation to avoid local minima. Defaults to 25.

        Returns:
            np.array: Next experiment to perform
        """

        # Dimension of input data
        dim = X_sample.shape[1]
        min_val, next_xp = 1, None

        # Acquisition function
        def min_obj(X):
            return -self.expected_improvement(
                X.reshape(-1, dim), X_sample, Y_sample
            )

        # Minimise for X random points
        for x0 in np.random.uniform(
            self.bounds[:, 0], self.bounds[:, 1], size=(n_restarts, dim)
        ):
            res = minimize(min_obj, x0=x0, bounds=self.bounds,
                           method='L-BFGS-B')

            if res.fun < min_val:
                min_val = res.fun[0]
                next_xp = res.x

        self.logger.debug(f'New suggested experiment: {next_xp}')

        return next_xp

    def update(self, X: np.ndarray, y: np.ndarray):
        """Updates the kernel with new values for X and y

        Args:
            X (np.ndarray): Experiment values
            y (np.ndarray): Experiment scores
        """

        # Set X_samples if not already
        self.X_samples = np.append(
            self.X_samples, X, axis=0
        ) if self.X_samples is not None else X

        # Set Y_samples if not already
        self.Y_samples = np.append(
            self.Y_samples, y, axis=0
        ) if self.Y_samples is not None else y

        # Update kernel
        self.logger.info('Updating kernel...')
        self.kernel.fit(self.X_samples, self.Y_samples)

    def request_initial_batch(self) -> np.ndarray:
        """Requests an intial batch of random experiments to perform

        Returns:
            np.ndarray: Random experiments to perform
        """

        return np.random.uniform(
            self.bounds[:, 0],
            self.bounds[:, 1],
            size=(self.batch_size, self.bounds.shape[0])
        )

    def request_next_batch(self) -> np.ndarray:
        """Request the next batch of experiments to perform.
        Returns `batch_size` total experiments.

        Returns:
            np.ndarray: Next batch to perform
        """

        return np.asarray([
            self.propose_location(self.X_samples, self.Y_samples)
            for _ in range(self.batch_size)
        ])
