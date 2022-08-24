from nanobot import NanobotManager
from modularwheel.utils import Reagent
from nanobot.constants import common as cst

nb = NanobotManager('./platform_configuration.json')
nb.home_all_motors()
mw = nb.wheel

def make_reagent(name, volume: float = 5):
    return Reagent(name, volume, in_valve=cst.EXTRA, out_valve=cst.INLET)

REAGENTS = [
    make_reagent('gold'),
    make_reagent('surfactant'),
    make_reagent('reductant', volume=0.5),
    make_reagent('seeds', volume=0.5),
    make_reagent('silver', volume=1)
]

def fill_vial():
    for reagent in REAGENTS:
        nb.dispense(*reagent.as_tuple)
    nb.turn_wheel(cst.WHEEL_NAME, 1)

def take_sample():
    mw.move_motor_to_position(
        cst.SAMPLE_MODULE, cst.SAMPLE_MODULE_LOWER
    )

    nb.dispense(
        cst.SAMPLE_PUMP, 5, in_valve=cst.SAMPLE_INLET, out_valve=cst.UV_IR
    )

    nb.dispense(
        cst.SAMPLE_PUMP, 13, in_valve=cst.SAMPLE_INLET, out_valve=cst.SAMPLE_WASTE
    )

    mw.home_motor(cst.SAMPLE_MODULE)

    nb.turn_wheel(cst.WHEEL_NAME, 1)

def routine():
    nb.logger.info('Beginning fluidic test')
    # for _ in range(3):
    #     fill_vial()
    
    # nb.turn_wheel(cst.WHEEL_NAME, 4)

    for _ in range(3):
        take_sample()

    nb.logger.info('Finished fluidic test!')
    nb.logger.error('Error for the banter')

if __name__ == '__main__':
    routine()
