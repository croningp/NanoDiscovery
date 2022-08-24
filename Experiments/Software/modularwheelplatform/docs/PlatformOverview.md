# Platform
The following is a generalised guide on how to structure your project. The structure of a project follows a standard as set [here.](http://datalore.chem.gla.ac.uk/GAK/PlatformTemplate) This is a base template structure that can be added to/modified to fit your project's specific needs.

# Basic Platform Structure
![platformstructure](https://user-images.githubusercontent.com/13821621/34262631-d78c3d20-e664-11e7-9b9a-efb9a7f70907.png)


# Requirements
* [Commanduino](https://github.com/croningp/commanduino)
* [Arduino Command Handler](https://github.com/croningp/Arduino-CommandHandler)
* [Arduino Command Tools](https://github.com/croningp/Arduino-CommandTools)
* [PyCont](https://github.com/croningp/pycont) (If using Tricontinent Pumps)

# Project Folder
Holds all the information necessary to run the platform. It is split into two main folders: **Hardware** and **Software**

## **Hardware**
Holds all the files necessary for the building of this platform. Here, you can add STL files for 3D printed parts, links to building materials such as cross-beams, motors, Arduino kits, etc., amongst other items necessary for the construction of your platform. This repository comes fully equipped with all the 3D files necessary for construction and links to purchasing said building materials.

## **Software** 
Holds all the software necessary for operating your platform. A hierarchial structure is adopted here to maximise modularity, allowing additional modules to be introduced/removed as and when required. Firmware and Utilities folders should also be included to hold the Arduino code and general purpose fuctions respectively. The project structure is as follows:
```
Base Layer -> Operational Layer -> Managerial Layer
```
## Base Layer
This is the lowest level of the platform which implements the base functionality of the platform. That being, no specific operations would be conducted in these scripts, just basic setup and low-level functions. Examples would be setting up Tricont pumps, initialising a UV spectrometer or pH probe, setting up a camera, etc. See examples below:

### **PyCont Pump Base Layer**
This script simply sets up the Tricont pump controller using PyCont and sets all pumps to 0. The controller can then be called upon from an Operations script to give access to the pumps.  
For more information on PyCont, click [here](https://github.com/croningp/pycont).
```python
# Base Layer: PUMPS

import os
import inspect
import logging
import json

logging.basicConfig(level=logging.INFO)

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
from pycont.controller import MultiPumpController

config_path = os.path.join(HERE, "pycont_config.json")
controller = MultiPumpController.from_configfle(config_path)

with open(config_path) as f:
    config = json.load(f)

controller.smart_initialize()

pumps = controller.get_pumps(controller.pumps)
for pump in pumps:
    pump.go_to_volume(0)
```

### **Commanduino Device Base Layer**
This script sets up Commanduino for any Arduino device, allowing you to access any device currently attached to it that is listed in its commanduino config file (operations/configs folder).  
For more information on how to use Commanduino, click [here](https://github.com/croningp/commanduino).
```python
import os
import sys
import json
import time
import inspect

from commanduino import CommandManager

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

root_path = os.path.join(HERE, "..")
sys.path.append(root_path)

from utils import json_utils

""" CONSTANTS """
DEVICES = "devices"

class CoreDevice(object):
    """
    Class representing a core Commanduino system.
    Allows access to the modules attached

    Args:
        config (str): path to the Commanduino config file
    """
    def __init__(self, config):
        self.mgr = CommandManager.from_configfile(config)
        self.config = json_utils.read_json(config)


    def valid_device(self, dev_name):
        """
        Checks if the given device name is present within the config

        Args:
            dev_name (str): name of the device
        
        Returns:
            valid (bool): If the device is present or not
        """
        return dev_name in self.config[DEVICES].keys()

    def get_device_attribute(self, dev_name):
        """
        Gets the device attribute from CommandManager

        Args:
            dev_name (str): Name of the device

        Returns:
            device (CommandDevice): Device instance in the CommandManager

        Raises:
            AttributeError: The device is not in the CommandManager
        """
        if self.valid_device(dev_name):
            try:
                return getattr(self.mgr, dev_name)
            except AttributeError:
                print("No device named {0} in the manager!\nBailing out!".format(dev_name))
                sys.exit(-1)
        else:
            print("Invalid device name: {0}".format(dev_name))
            sys.exit(-1)

```

## Operational Layer
The operational layer is responsible for implementing all the functions specific to your platform. This takes a base layer component and adds a control script on top, allowing access to the hardware to perform the desired function.  
An example would be setting up a cleaning routine for pumps, dispensing reagents from pumps, turning the Geneva Wheel, raising and lowering modular drivers on the wheel etc.  
See below:

### **Example: Geneva Wheel Control Operations**
This example highlights using the Commanduino Core Base Layer and incorporating it into an operational layer control script for a Geneva Wheel. By using the base layer methods, we can get access to all the devices attached and write functions to perform specific tasks. In this case, turning the wheel, moving modular drivers and runing peristaltic pumps.
```python
import os
import sys
import time
import inspect

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
root_path = os.path.join(HERE, "..")
sys.path.append(root_path)

from base_layer.commanduino_setup.core_device import CoreDevice

""" CONSTANTS """
WHEEL_NAME = "wheel"
FULL_WHEEL_TURN = 6400
PUMP_INCREMENT = 8000
MODULE_LOWER = -39000


class WheelControl(CoreDevice):
    """
    Class for controlling a Geneva Wheel system
    Contains methods for rotation, modular drivers, pumps, etc.
    Assumes the user has at least one Geneva wheel, one modular driver, and one peristaltic
    pump attached to their rig.

    Inherits:
        CoreDevice: Base Commanduino Device

    Args:
        config (str): Path to the config
    """
    def __init__(self, config):
        super().__init__(self, config)


    def turn_wheel(self, n_turns, wait=True):
        """
        Turns the Geneva Wheel n_turns times

        Args:
            n_turns (int): Number of turns
        """
        drive_wheel = self.get_device_attribute(WHEEL_NAME)
        for _ in range(n_turns):
            drive_wheel.move(FULL_WHEEL_TURN, wait=wait)


    def move_module(self, mod_name, pos, wait=True):
        """
        Moves the modular driver to a set position

        Args:
            mod_name (str): Name of the module
            pos (int/float): Number of steps to move
            wait (bool): Wait for the device to be idle, default set to True
        """
        module = self.get_device_attribute(mod_name)
        module.move(-pos, wait=wait) # -ve due to inverted direction
    

    def lower_module(self, mod_name, wait=True):
        """
        Lowers the modular driver

        Args:
            mod_name (str): Name of the modular driver
            wait (bool): Wait for the device to be idle, default set to true
        """
        self.move_module(mod_name, MODULE_LOWER, wait=wait)


    def home_module(self, mod_name, wait=True):
        """
        Brings the module back to its home position

        Args:
            mod_name (str): Name of the module
            wait (bool): Wait for the device to be idle, default set to true
        """
        module = self.get_device_attribute(mod_name)
        module.home(wait=wait)


    def run_peri_pump(self, pump_name, num_secs):
        """
        Runs a peristaltic pump for num_secs time

        Args:
            pump_name (str): Name of the pump
            num_secs (int/float): Number of seconds to run for
        """
        pump = self.get_device_attribute(pump_name)
        curr_time = time.time()
        while time.time() < (curr_time + num_secs):
            pump.move(PUMP_INCREMENT)    

```

## Managerial Layer
The Managerial Layer is responsible for consolidating all required operational layer modules into a single, easily accessible script. This script can then be called by an experimental run script to give you access to all the functions.  
By doing so, wrapper functions can be implemented that encompass an entire operation e.g. cleaning. Other manager functions can also be implemented. Example function below:
```python
# manager.py
def clean_routine(self):
    self.wheel_control.lower_module()
    self.pump_control.empty_vessel()
    self.pump_control.clean()
    self.wheel_control.home_module()
    self.wheel_control.turn_wheel()
```
Skeletal example of a manager.py file:
```python
import os
import sys
import inspect

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
root_path = os.path.join(HERE, "..")
sys.path.append(root_path)

""" Operations Modules """
from operations.tricont_control import TricontControl
from operations.wheel_control import WheelControl
# Add more as required


class Manager(object):
    """
    Class representing a manager which governs the entire platform
    Wrapper around certain operations for the platform and general management
    """
    def __init__(self):
        self.pump_control = TricontControl()
        self.wheel_control = WheelControl()
        # Add more as required

    """
    Add general managerial functions here 
    """



    """
    Add wrappers to operational functions here
    """

```

## Firmware
The firmware folder is where all Arduino and microcontroller code should be stored. For Arduino code to be used with Commanduino, please see the [Arduino Command Handler](https://github.com/croningp/Arduino-CommandHandler) and [Arduino Command Tools](https://github.com/croningp/Arduino-CommandTools) repositories for installation instructions and demos.
