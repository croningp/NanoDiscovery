'''
Run using IPython for interactive testing of the hardware
'''

from nanobot import NanobotManager
cfg = './platform_configuration.json'

nb = NanobotManager(cfg)
mw = nb.wheel

