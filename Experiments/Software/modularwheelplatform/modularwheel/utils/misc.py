"""
.. module:: utils.misc
    :platforms: Unix, Windows
    :synopsis: Miscellaneous classes/functions that don't fit under any other
                utility file

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

from typing import Optional, Tuple

class Reagent:
    """Class for representing a Reagent to be dispensed.

    Args:
        name (str): Name of the reagent/pump
        volume (Optional[float]): Volume to dispense. Defaults to 1.0
        in_valve (Optional[str]): Intake valve. Defaults to 'I'
        out_valve (Optional[str]): Output valve. Defaults to 'O'
    """

    def __init__(
        self,
        name: str,
        volume: Optional[float] = 1.0,
        in_valve: Optional[str] = 'I',
        out_valve: Optional[str] = 'O'
    ):
        self.name = name
        self.volume = volume
        self.in_valve = in_valve
        self.out_valve = out_valve

    def __repr__(self) -> str:
        """Get human-readable name for reagent

        Returns:
            str: Reagent string
        """

        return f'Reagent: {self.name} Volume: {self.volume}'

    @property
    def as_tuple(self) -> Tuple[str, int, str, str]:
        """Converts the reagent to a tuple
        """

        return (
            self.name, self.volume, self.in_valve, self.out_valve
        )
