"""
.. module:: cleaning.clean_vial
    :platforms: Unix, Windows
    :synopsis: Cleaning protocols for cleaning a vial on Nanobot

.. moduleauthor:: Graham Keenan (Cronin Lab 2020)

"""

import nanobot.constants as cst
from typing import Optional, Callable

ACID_VOLUME = 5

def clean_vial_protocol(dispense_func: Callable, cycles: int = 2):
    """Cleaning protocol for cleaning a vial

    Args:
        dispense_func (Callable): Pump dispense method
        cycles (int, optional): Number of cleaning cycles. Defaults to 2.
    """

    # Any additional cleaning methods here (e.g. Acid)

    # Clean the UV/IR line
    clean_uv_ir_lines(dispense_func, cycles)

def dispense_acid(dispense: Callable, volume: float):
    """Dispense acid into the target vial and cleaning the valve head afterwards

    Args:
        dispense (Callable): Pump dispense method
        volume (float): Volume of acid to dispense
    """

    # Use 20% of acid volume to clean the valve
    residue_vol = volume / 5

    # Move acid to vial
    dispense(
        cst.ACID_PUMP,
        volume,
        in_valve=cst.EXTRA,
        out_valve=cst.INLET
    )

    # Remove any acidic residue from valve head
    dispense(
        cst.ACID_PUMP, residue_vol, in_valve=cst.OUTLET, out_valve=cst.EXTRA
    )

def acid_purge(dispense: Callable, cycles: Optional[int] = 4):
    """Perform an acid puge of the vial, moving acid around the system and out
    to waste. Flushes system with water afterwards

    Args:
        dispense (Callable): Pump dispense function
    """

    # Push acid into vial
    dispense_acid(dispense, ACID_VOLUME)

    # Move acid through UV/IR lines
    dispense(
        cst.SAMPLE_PUMP,
        volume=ACID_VOLUME,
        in_valve=cst.SAMPLE_INLET,
        out_valve=cst.UV_IR
    )

    # Move to waste line
    dispense(
        cst.SAMPLE_PUMP,
        volume=ACID_VOLUME,
        in_valve=cst.SAMPLE_INLET,
        out_valve=cst.SAMPLE_WASTE
    )

    # Perform X water clean cycles of the lines/valves
    for _ in range(cycles):
        # Move water into sample vial
        dispense(
            cst.WATER_PUMP,
            volume=ACID_VOLUME,
            in_valve=cst.WATER_STOCK,
            out_valve=cst.WATER_TO_SAMPLE
        )

        # Move water through UV/IR lines
        dispense(
            cst.SAMPLE_PUMP,
            volume=ACID_VOLUME,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.UV_IR
        )

        # Move water out to waste
        dispense(
            cst.SAMPLE_PUMP,
            volume=ACID_VOLUME,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.SAMPLE_WASTE
        )

def clean_uv_ir_lines(dispense: Callable, cycles: int):
    """Protocol for cleaning the UV/IR lines

    Args:
        dispense (Callable): Pump dispense method
        cycles (int): Cleaning cycles to perform
    """
    # Pump out of the samples into the waste
    dispense(
        cst.SAMPLE_PUMP,
        13,
        in_valve=cst.SAMPLE_INLET,
        out_valve=cst.SAMPLE_WASTE,
        speed_out=cst.FAST_SPEED
    )

    # Perform clean cycle X times
    for _ in range(cycles):
        single_uv_ir_clean(dispense)

def single_uv_ir_clean(dispense: Callable, volume: float = 5):
    """Performs a single clean of the UV/IR lines

    Args:
        dispense (Callable): Pump dispense method
    """
    # Pull water directly into the UV line
    dispense(
        cst.SAMPLE_PUMP,
        volume=volume,
        in_valve=cst.SAMPLE_WATER,
        out_valve=cst.UV_IR,
        speed_in=cst.DEFAULT_SPEED,
        speed_out=cst.FAST_SPEED
    )

    # Pull the residual in the sample to the waste
    dispense(
        cst.SAMPLE_PUMP,
        volume,
        in_valve=cst.SAMPLE_INLET,
        out_valve=cst.SAMPLE_WASTE,
        speed_in=cst.DEFAULT_SPEED,
        speed_out=cst.FAST_SPEED
    )
