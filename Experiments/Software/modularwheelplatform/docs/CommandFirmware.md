# Firmware Setup For Commanduino
The following is a description of how to set up the Arduino firmware for use with Commanduino.

## Installation
Clone the following repositories and follow the basic set up instructions within (Works with Windows/Linux)
* [Arduino Command Handler](https://github.com/croningp/Arduino-CommandHandler)
* [Arduino Command Tools](https://github.com/croningp/Arduino-CommandTools)

## Basic Setup

* Include the Command Handler and Command Manager at the top of your file and create a CommandManager instance

```C++
#include <CommandHandler.h>
#include <CommandManager.h>
CommandManager cmdMgr;
```

* Include the basic Arduino devices you will be using e.g. AccelSteppers, Servos, etc.

```C++
#include <AccelStepper.h>
#include <LinearAccelStepperActuator.h>

/* Additional Modules if necessary */
```

* Next, include the "Command" version of all your included devices from above

```C++
#include <CommandAccelStepper.h>
#include <CommandLinearAccelStepperActuator.h>
```

* Now instantiate the Arduino device objects and their Command equivalents
    * Note: The numbers are pins and these may change depending on your setup  

```C++
AccelStepper stepper1(AccelStepper::DRIVER, 54, 55);
CommandLinearAccelStepperActuator cmdStepper(stepper1, 3, 38);

/* Additional Object creation */
```

## Setup Function

Within the setup function, we use the created CommandDevice objects and add them to the manager. Each object is given a unique ID that the user specifies.

```C++
void setup() {
    /* Here, "drive_wheel" is the unique ID */
    cmdStepper.registerToCommandManager(cmdMgr, "drive_wheel");

    /* Register the remaining devices in a similar fashion */
}
```

## Loop Function

The loop function only contains single call for the manager to update. Nothing else is required here.

```C++
void loop() {
    cmdMgr.update();
}
```

# Pin Mappings

One of the most common uses of Commanduino is controlling stepper motors for movement, pumps, etc. To be able to use multiple stepper motors on a single Arduino board, a RAMPS shield is used, giving access to 5 possible motor locations and a collection of pins for other devices. Below is a list of pin mappings for using multiple stepper motors on a single RAMPS shield.

```C++
X_STEP_PIN         54
X_DIR_PIN          55
X_ENABLE_PIN       38

Y_STEP_PIN         60
Y_DIR_PIN          61
Y_ENABLE_PIN       56

Z_STEP_PIN         46
Z_DIR_PIN          48
Z_ENABLE_PIN       62

E0_STEP_PIN         26
E0_DIR_PIN          28
E0_ENABLE_PIN       24

E1_STEP_PIN         36
E1_DIR_PIN          34
E1_ENABLE_PIN       30

X_MIN_PIN          3
X_MAX_PIN          2
Y_MIN_PIN          14
Y_MAX_PIN          15
Z_MIN_PIN          18
Z_MAX_PIN          19
```