"""
.. module:: experiments.basic_experiment
    :platform: Unix
    :synopsis: Basic Experiment child class for running the system

.. moduleauthor:: Graham Keenan (Cronin Group 2019)

"""

# System imports
import sys
import time
from datetime import datetime
from pathlib import Path
import numpy as np 
import threading

# Platform imports
from core import CoreExperiment
import nanobot.constants as cst
from modularwheel.utils import json_utils as json
import json as json2

# Path setup
HERE = Path('.').absolute()
DATA = HERE.joinpath('data')

# Time to wait between reactions and analysis
GROWTH_TIME = 3600

# Wait time for the reductant to take effect
REDUCTANT_WAIT_TIME = 10

# List of experiments in which we control the pH using the operations
# there must be an operation json file in it
Operation_pH_index = sorted([23])

# List of experiment indexes to analys  e, empty means all of them
ANALYTICAL_INDEX = sorted([])

class BasicExperiment(CoreExperiment):
    """Experimental run script.
    Performs a `Basic` run of the system which consists of a single batch
    of X reactions in a single folder.
    Dispenses and analyses the X reactions and finishes, that's all.

    Args:
        reactions (bool): Execute reaction protocol
        analysis (bool): Execute analysis protocol

    Inherits:
        CoreExperiment: Base experiment class with common functions
    """

    def __init__(self, reactions: bool = True, analysis: bool = True):
        super().__init__()
        self.do_reactions = reactions
        self.do_analysis = analysis
        self.pH_electrode_ready = True
        self.manager.set_stir_rate("wash_fan",35)
    def __del__(self):
        """Send an email once the script has concluded"
        """

        # Send emails to users when finished
        self.manager.send_emails(
            f"Experiment {self.info[cst.TITLE]} is complete!", cst.EMAILS
        )

        # Send slack message
        # self.manager.send_slack_message(
        #     f'Experiment {self.info[cst.TITLE]} complete!'
        # )
    def tune_pH_measurement(
        self,
        target_pH,
        acid_pump,
        base_pump,
        xp_path,
        coeff= 10/4,
        dilution_factor = 1.0,
        default_vol = 10 * (10 ** -3),
        tolerance = 0.2
    ):
        """Tunes the pH of a solution dynamically.

        Args:
            target_pH (float): pH to aim for.

            acid_pump (str): Name of the acid pump.

            base_pump (str): Name of the base pump.

            coeff (Optional[float], optional): Tuning coefficient.
            Defaults to 10.0.

            dilution_factor (Optional[float], optional): Dilution factor.
            Defaults to 1.0.

            default_vol (Optional[float], optional): Default dispense volume.
            Defaults to 10*(10 ** -3).
        """
        exp_start_t = time.time()

        operation_json = {}
        volume_total = 0
        n_step = 0

        # Initial pH measurement
        measured_pH = self.manager.ph_module.measure_pH()
        print(f"Target pH is {target_pH} and current pH is {measured_pH}")
        # Direction of pH travel
        direction = ""

        # Loop until consensus reached
        while True:
            # Solution is too basic
            if target_pH < measured_pH:
                # Calculate error and dispensing volume
                error = measured_pH - target_pH
                volume = coeff * error * default_vol

                # Dispense the acid
                self.manager.dispense(
                    acid_pump, 
                    volume, 
                    in_valve=cst.EXTRA,
                    out_valve=cst.INLET,
                    speed_in=cst.DEFAULT_SPEED,
                    speed_out=cst.FAST_SPEED
                )
                volume_total = volume_total +volume
                # Update direction of travel
                direction = "acidic"

            # Solution is too acidic
            elif measured_pH < target_pH:
                # Calculate error and dispensing volume
                error = target_pH - measured_pH
                volume = coeff * error * default_vol

                # Dispense the base
                self.manager.dispense(
                    base_pump, 
                    volume, 
                    in_valve=cst.EXTRA,
                    out_valve=cst.INLET,
                    speed_in=cst.DEFAULT_SPEED,
                    speed_out=cst.FAST_SPEED
                )

                volume_total = volume_total +volume
                # Update direction of travel
                direction = "basic"

            # append the operation to json file
            operation_json[f"{n_step}"] = [direction,volume,10]
            
            # Wait for stabilisation and record pH
            time.sleep(10)
            measured_pH = self.manager.ph_module.measure_pH()
            print(f"Target pH is {target_pH} and current pH is {measured_pH}")

            # pH is within range
            if measured_pH - tolerance <= target_pH <= measured_pH + tolerance:
                operation_json[f"{n_step}"].append(15)

                # Wait to see if it is stable
                time.sleep(15)
                measured_pH = self.manager.ph_module.measure_pH()
                print(f"Target pH is {target_pH} and current pH is {measured_pH}")

                # Check range again and break if stable
                if measured_pH - tolerance <= target_pH <= measured_pH + tolerance:
                    operation_json[f"{n_step}"].append(measured_pH)
                    operation_json[f"{n_step}"].append(True)
                    break

            if volume_total > 3:
                operation_json[f"{n_step}"].append(measured_pH)
                operation_json[f"{n_step}"].append(False)
                break

            if time.time() > exp_start_t + 3*60:
                operation_json[f"{n_step}"].append(measured_pH)
                operation_json[f"{n_step}"].append(False)
                break

            # Overshot the target, reduce coefficient and repeat
            if (
                (direction == "acidic" and target_pH > measured_pH)
                or (direction == "basic" and target_pH < measured_pH)
            ):
                coeff = coeff*0.6

            n_step = n_step +1

        with open(f'{xp_path}/pH_operation.json', 'w') as fp:
            json2.dump(operation_json, fp)

    def set_pH_with_instrucitons(
        self,
        acid_pump,
        base_pump,
        xp_path):
        """
        set the pH value accoding to the instructions given by pH_operation.json file
        """

        # read in the instruction file
        with open(f'{xp_path}/pH_operation.json', 'r') as json_file:
            operation_json = json2.load(json_file)
        # count how many steps are needed
        n = len(operation_json)
        # begin the operations except for all the steps
        for n_step in range(n):
            operation_temp = operation_json[f"{n_step}"]
            volume = operation_temp[1]
            # special case for the last step, 
            # since the last variable records if this step is successful or not
            if n_step == n:
                operation_temp = operation_temp[0:-2]
            # perform the operations according to the operation_temp
            if operation_temp[0] == "basic":
                self.manager.dispense(
                    base_pump, 
                    volume, 
                    in_valve=cst.EXTRA,
                    out_valve=cst.INLET,
                    speed_in=cst.DEFAULT_SPEED,
                    speed_out=cst.FAST_SPEED
                )                
            else:
                self.manager.dispense(
                    acid_pump, 
                    volume, 
                    in_valve=cst.EXTRA,
                    out_valve=cst.INLET,
                    speed_in=cst.DEFAULT_SPEED,
                    speed_out=cst.FAST_SPEED
                )    
      
            # set sleep time according to the instruction
            for sleep_time in operation_temp[2:]:
                time.sleep(sleep_time)


    def move_probe_to_sample_position(self):
        """
        To do:
            Move the pH probe to the sample position
        """
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_HORZ_MODULE, 81000)
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 40500)
        return 

    def move_probe_to_stock_position(self):
        """
        To do:
            Move the pH probe to the stock solution position
        """
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_HORZ_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 40500)
        return

    def dip_probe(self,n = 3):
        """
        To do:
            dip the probe several times
        Args:
            n: the number of cleaning times
        """
        for i in range(n):
            self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 20500)
            self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 40500)
            time.sleep(5)
        return

    def clean_probe(self,n = 3):
        """
        To do:
            Clean the vial to store the pH probe with water
        Args:
            n: the number of cleaning times
        """

        for i in range(n):
            self.manager.dispense(
                "probe",
                15,
                in_valve=cst.INLET,
                out_valve=cst.EXTRA,
                speed_in=cst.SLOW_SPEED,
                speed_out=cst.FAST_SPEED)

            self.manager.dispense(
                "water",
                volume = 10,
                in_valve=cst.WATER_STOCK, 
                out_valve=cst.WATER_TO_PH,
                speed_out=cst.FAST_SPEED)

        return

    def calibrate_pH(self,xp_path):
        """
        To do:
            Calibrate the pH probe for this new generation
        Args:
            xp_path: the root path of the experiment
        """
        buffer_pHs = [4,7,10]
        pH_cal_json = {}

        # obtain the analog signal of three different buffers
        for buffer_pH in buffer_pHs:
            input(f"Put buffer with pH {buffer_pH} and Press Enter to continue...")
            self.move_probe_to_sample_position()
            time.sleep(10)

            pHvalueAnalog,pHvaluestd = self.manager.ph_module.driver.measure_analog_values()

            print(f"Analog value is {pHvalueAnalog} and the std is {pHvaluestd}")
            pH_cal_json[f"pH{buffer_pH}"] = pHvalueAnalog

            self.move_probe_to_stock_position()
            # rinse the probe 
            time.sleep(10)
            # clean the probe
            self.dip_probe(2)

            self.manager.turn_wheel(cst.WHEEL_NAME,1)

        self.clean_probe(n=1)
        
        pH_cal_json["time"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(f'{xp_path}/calibration.json', 'w') as fp:
            json2.dump(pH_cal_json, fp)
        return 
    
    def clean_electrode_in_parallel(self):
        """
        Clean the electrode in parallel with dispensing
        """
        self.pH_electrode_ready = False
        # put probe back to stock and clean 
        self.move_probe_to_stock_position()
        self.dip_probe(n = 2)
        self.clean_probe(n = 1)
        self.pH_electrode_ready = True

    def reaction_protocol(self, xp_path: str):
        """Dispensing protocol
        Loads in parameters for each experiment and dispenses reagents

        Args:
            xp_path (str): Path to experiment
        """

        # Log experiment
        self.manager.logger.info(f"Conducting experiment: {xp_path}")

        # Load in parameters
        params = json.read_json(
            xp_path.joinpath(cst.PARAMS_FILE)
        )
        print(params)
        # get the pH value of the json file
        reaction_pH = params["pH"]
        params.pop("pH")

        params = self.manager.convert_params_dict_to_reagents(params)
        print(params)

        # Dispense all reagents
        self.manager.logger.info(f"Dispensing reagents: {params}")

        # Dispense everything except the last 3 reagents: Au, Ag and seed
        for reagent in params[0:3]:
            if reagent.name != cst.WATER_PUMP:
                if reagent.name == "water1" or reagent.name == "water2":
                    self.manager.dispense(
                        "water_reagent",
                        reagent.volume,
                        in_valve=reagent.in_valve,
                        out_valve=reagent.out_valve,
                        speed_out=cst.FAST_SPEED
                    )
                else:
                    self.manager.dispense(
                        reagent.name,
                        reagent.volume,
                        in_valve=reagent.in_valve,
                        out_valve=reagent.out_valve,
                        speed_out=cst.FAST_SPEED
                    )
            # Special case for when water is used as a reagent
            else:
                self.manager.dispense(
                    reagent.name,
                    reagent.volume,
                    in_valve=cst.WATER_STOCK,
                    out_valve=cst.WATER_REAGENT
                )

        # Check if the pH electrode is ready to use
        while True:
            if self.pH_electrode_ready == True:
                break
            time.sleep(0.1)

        # turn wheels 4 times
        self.manager.turn_wheel(cst.WHEEL_NAME,4)

        # move pH probe to the sample position
        self.move_probe_to_sample_position()
        
        # perform the algorithm which is in module wheel system
        if self.xp_index in Operation_pH_index:

            self.set_pH_with_instrucitons(
                acid_pump = "ph_acid",
                base_pump = "ph_base",
                xp_path = xp_path)

        else:
            self.tune_pH_measurement(
                target_pH = reaction_pH,
                acid_pump = "ph_acid",
                base_pump = "ph_base",
                xp_path = xp_path)

        # move the probe up first
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 0)

        # clean the electrode in parallel
        threading.Thread(target = self.clean_electrode_in_parallel).start()

        # turn 20 times wheel
        self.manager.turn_wheel(cst.WHEEL_NAME,20)
        self.activate_ring_stirrer(speed=35)

        # dispense Au, Ag and seed
        for reagent in params[3:]:
            if reagent.name != cst.WATER_PUMP:
                # special case for dispensing water
                if reagent.name == "water1" or reagent.name == "water2":
                    self.manager.dispense(
                        "water_reagent",
                        reagent.volume,
                        in_valve=reagent.in_valve,
                        out_valve=reagent.out_valve,
                        speed_out=cst.FAST_SPEED
                    )

                else:
                    self.manager.dispense(
                        reagent.name,
                        reagent.volume,
                        in_valve=reagent.in_valve,
                        out_valve=reagent.out_valve,
                        speed_out=cst.FAST_SPEED
                    )
            # Special case for when water is used as a reagent in a 6-way valve system
            else:
                self.manager.dispense(
                    reagent.name,
                    reagent.volume,
                    in_valve=cst.WATER_STOCK,
                    out_valve=cst.WATER_REAGENT
                )
            # Give time for reducing
            if reagent.name == 'gold':
                time.sleep(REDUCTANT_WAIT_TIME)

        # Turn the wheel
        self.manager.turn_wheel(cst.WHEEL_NAME)

        """
        Something should be added here to control the pH before Ag, Au and seeds are added
        1. dispense everthing except for seed
        2. turn wheels 4 times
        3. use the algorithm to tune the pH
        4. move probe up, move the wheel backward 4 times
        5. dispense Ag, Au, seed and final water
        6. probe to stock and clean
        7. if it's the end of a generation, refill the probe vial with KCl
        """

    def analysis_protocol(self, xp_path: str):
        """Analysis protocol for analysing each experiment
        Obtain UV/IR spectra for the experiment  and cleans the vial afterwards

        Args:
            xp_path (str): Experiment to analyse
        """

        # Log experiment
        self.manager.logger.info(f"Analysing experiment: {xp_path}")

        # Obtain experimental spectra
        uv, ir = self.manager.obtain_uv_ir_spectra(sample_volume=3.5)
        self.save_spectra(uv, ir, xp_path)
        # Clean the vial and tubing
        self.manager.clean_vial()

    def full_protocol(self):
        """Executes protocols depending on which flags are set

        Raises:
            Exception: General exception to catch common errors.
        """

        # Preflush the reagent pumps -- Always ask!
        self.manager.logger.info(
            f"Initialising experiment: {self.info['title']}"
        )

        self.move_probe_to_stock_position()
        self.preflush_pumps(
            'surfactant',
            'silver',
            'gold',
            'reductant',
            'seeds',
            ("water_reagent",1.5),
            ("ph_acid",1),
            ("ph_base",1),
        )
        self.manager.set_stir_rate("wash_fan",35)
        self.activate_ring_stirrer(speed=35)
        # Get all experiments to perform in order
        # Only 1 file means no analysis has been performed
        xp_list = sorted([
            xp for xp in self.root_xp_folder.iterdir()
            if not xp.is_file()
        ])

        # No experiments to conduct, Finish
        if not xp_list:
            self.manager.logger.warning(
                f"No experiments to do for {self.root_xp_folder}"
            )
            return
        # Take a reference if needed
        self.take_reference()

        # Before we put the pH probe into the sample, clean it with water once to get rid of KCl
        clean_probe_flag = input("Do you want to clean the pH probe vial?(y/n)")
        if clean_probe_flag == "y":
            self.clean_probe(1)
        
        self.calibrate_pH_flag = input("Do you want to calibrate the pH probe? (y/n)")
        if self.calibrate_pH_flag == "y":
            # Calibrate pH probe
            self.calibrate_pH(self.root_xp_folder)
        
        # Refresh the pH measurement with calibrated data
        with open(f'{self.root_xp_folder}/calibration.json') as json_file:
            pH_json = json2.load(json_file)
        self.manager.ph_module.update_calibrations([pH_json["pH4"],pH_json["pH7"],pH_json["pH10"]])

        input('Press Enter to start!')
        # Conduct reactions if flag set
        if self.do_reactions:
            # Let user know we're starting
            # self.manager.send_slack_message("Starting reaction sequence.")

            # Activate the stirrers on the ring
            self.activate_ring_stirrer(speed=35)

            self.xp_index = 0
            # Execute reaction
            for xp in xp_list:
                self.reaction_protocol(xp)
                self.activate_ring_stirrer(speed=35)
                self.xp_index = self.xp_index + 1

            # Stop the stirrers after dispensing
            self.kill_ring_stirrers()

            # Check if the pH electrode is ready to use
            while True:
                if self.pH_electrode_ready == True:
                    break
                time.sleep(0.1)
            
            # refill the probe vial with KCl solution to store the pH probe
            self.manager.dispense(
                "probe",
                14,
                in_valve=cst.INLET,
                out_valve=cst.EXTRA,
                speed_in=cst.DEFAULT_SPEED,
                speed_out=cst.FAST_SPEED)

            self.manager.dispense(
                "kcl",
                volume = 10,
                in_valve=cst.EXTRA, 
                out_valve=cst.INLET,
                speed_out=cst.FAST_SPEED)           

            # Wait for a set time after dispensing
            mins, hours = int(GROWTH_TIME / 60), int(GROWTH_TIME / 60 / 60)
            self.manager.logger.info(f"Waiting for {mins} mins...")
            # self.manager.send_slack_message(
            #     f"Finished dispensing, waiting {hours} hours."
            # )
            time.sleep(GROWTH_TIME)

            # Move into sample position
            self.manager.turn_wheel(
                cst.WHEEL_NAME, n_turns=cst.DISPENSE_TO_SAMPLE_POSITION
            )

        # Analyse reactions if flag set
        if self.do_analysis:
            # Let user know we're analysing
            # self.manager.send_slack_message("Starting analysis.")

            # This is ugly AF, need a proper solution but I'm tired
            # No specific reactions, do them all
            if not ANALYTICAL_INDEX:
                for xp in xp_list:
                    self.analysis_protocol(xp)

            # Got indexes to analyse, ONLY analyse them
            else:
                for idx in ANALYTICAL_INDEX:
                    for pos, xp in enumerate(xp_list):
                        if pos == idx:
                            self.analysis_protocol(xp)
                        else:
                            self.manager.turn_wheel(cst.WHEEL_NAME)

        # Ask user if they wish to purge with acid
        self.ask_for_system_purge()

        # Inform user generation is complete
        self.manager.send_emails(
            f'Experiment {self.info[cst.TITLE]} complete!', flag=2
        )

        # Send slack message
        # self.manager.send_slack_message(
        #     f'Experiment {self.info[cst.TITLE]} complete!'
        # )
if __name__ == "__main__":
    if "-a" in sys.argv:
        BasicExperiment(reactions=False).full_protocol()
    elif "-r" in sys.argv:
        BasicExperiment(analysis=False).full_protocol()
    else:
        BasicExperiment().full_protocol()
