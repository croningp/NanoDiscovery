"""
Common constants shared amongst a collection of files
"""

PLATFORM_NAME = "Nanobot"

""" PUMP CONSTANTS """
# Pump names
SAMPLE_PUMP = "sample"
WATER_PUMP = "water"
ACETONE_PUMP = "acetone"
ACID_PUMP = "regia"
PROBE_PUMP = "probe"
WATER_REAGENT_PUMP = "water_reagent"

# Valves (4-way)
INLET = "I"
OUTLET = "O"
EXTRA = "E"

# Water Valves
WATER_TO_SAMPLE = "1"
WATER_TO_PH = "2"
# WATER_REAGENT = "3"
WATER_TO_SEED = "4"
WATER_STOCK = "6"

# Sample Valves (6-way)
SAMPLE_WASTE = "2"
SAMPLE_INLET = "6"
SAMPLE_WATER = "4"
UV_IR = "5"

# Arbitrary pump speeds
SLOW_SPEED = 2000
DEFAULT_SPEED = 5000
FAST_SPEED = 15000

""" COMMANDUINO CONSTANTS """
PH_HORZ_MODULE = 'ph_horz'
PH_VERT_MODULE = 'ph_vert'
SAMPLE_MODULE = "sample"
WHEEL_NAME = "wheel"
RING = "ring"
PLATE = "plate"
LASER = "laser"
FULL_WHEEL_TURN = 6400
PUMP_INCREMENT = 8000
SAMPLE_MODULE_LOWER = 31500
PH_HORZ_SAMPLE_POSITION = 35000
PH_VERT_SAMPLE_POSITION = 31500


""" SPECTROMETER TYPES """
UV_SPECTROMETER = "UV"
RAMAN_SPECTROMETER = "RAMAN"
IR_SPECTROMETER = "IR"

""" SPECTROMETER CONSTANTS """
WAVELENGTH = "wavelength"
WAVENUMBER = "wavenumber"
INTENSITY = "intensities"
ABSORBANCE = "absorbances"
REFERENCE = 'reference'
UV_LIMITS = (400, 1100)
IR_LIMITS = ()

""" VIDEO """
VIDEO_DURATION = 30


""" MISC """
WHEEL_TURN = 1
DISPENSE_TO_SAMPLE_POSITION = 7
RAISED_MSD = 15000

# Emails for notifications
EMAILS = [
    "2492961j@student.gla.ac.uk"
]

# Slack IDs
SLACK_IDS = [
    "chemyibinjiang"
]
