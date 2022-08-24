#!/usr/bin/env python3
# have two pump plugged with switch at 0 and 1

import pycont.controller

io = pycont.controller.PumpIO('/dev/ttyUSB0')
to_test = [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B']

for add in to_test:
    print(f"trying address {add}")
    pump = pycont.controller.C3000Controller(io, f'test{add}', add, 5)
    pump.initialize()
    pump.transfer(10, "I", "O")


# p2 = pycont.controller.C3000Controller(io, 'test2', '2', 5)
# p2.smart_initialize()
