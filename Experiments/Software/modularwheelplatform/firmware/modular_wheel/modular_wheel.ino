#include <AccelStepper.h>
#include <LinearAccelStepperActuator.h>

#include <CommandHandler.h>
#include <CommandManager.h>
#include <CommandAccelStepper.h>
#include <CommandAnalogWrite.h>
#include <CommandLinearAccelStepperActuator.h>

CommandManager cmdMgr;

AccelStepper stepperX(AccelStepper::DRIVER, 54, 55);
CommandLinearAccelStepperActuator X(stepperX, 3, 38);

AccelStepper stepperY(AccelStepper::DRIVER, 60, 61);
CommandLinearAccelStepperActuator Y(stepperY, 14, 56);

AccelStepper stepperZ(AccelStepper::DRIVER, 46, 48);
CommandLinearAccelStepperActuator Z(stepperZ, 18, 62);

AccelStepper stepperE0(AccelStepper::DRIVER, 26, 28);
CommandLinearAccelStepperActuator E0(stepperE0, 2, 24);

AccelStepper stepperE1(AccelStepper::DRIVER, 36, 34);
CommandLinearAccelStepperActuator E1(stepperE1, 15, 30);

// PWM Control
CommandAnalogWrite a1(8);
CommandAnalogWrite a2(9);
CommandAnalogWrite a3(10);

void setup() {
    Serial.begin(115200);

    X.registerToCommandManager(cmdMgr, "X");
    Y.registerToCommandManager(cmdMgr, "Y");
    Z.registerToCommandManager(cmdMgr, "Z");
    E0.registerToCommandManager(cmdMgr, "E0");
    E1.registerToCommandManager(cmdMgr, "E1");

    a1.registerToCommandManager(cmdMgr, "A1");
    a2.registerToCommandManager(cmdMgr, "A2");
    a3.registerToCommandManager(cmdMgr, "A3");

    cmdMgr.init();
}

void loop() {
    cmdMgr.update();
}