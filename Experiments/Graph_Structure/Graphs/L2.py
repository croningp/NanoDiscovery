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
import threading
import numpy as np 
import networkx as nx
# Platform imports
from core import CoreExperiment
import nanobot.constants as cst
from modularwheel.utils import json_utils as json
import json as json2

# initialize with Graphic structure
G_skl = nx.read_gpickle("harware_graph.gpickle")
# the experiments that will be conducted in the wheel
wheel_position_list = [G_skl.nodes[node]['exp'] for node in G_skl]

# get the expeirments to be done with 1 step
exp_list = []
for node in G_skl:
    if isinstance(G_skl.nodes[node]['exp'],int):
        if G_skl.nodes[node]['step'] == 2:
            exp_list.append(G_skl.nodes[node]['exp'])
            
# get the expeirments to be analyzed with 1 step            
analysis_list = []
for exp_list_temp in exp_list:
    if G_skl.nodes[wheel_position_list.index(exp_list_temp)]['UV_Vis'] == True:
        analysis_list.append(exp_list_temp)

# get the wheel positions corresponding to the experiments 
exp_wheel_position = [wheel_position_list.index(i) for i in exp_list]
# get the wheel positions corresponding to the analysis 
analysis_wheel_position = [wheel_position_list.index(i) for i in analysis_list]

# get the wheel positions corresponding to the parent solution
parent_wheel = []
for node in G_skl.nodes():
    if isinstance(G_skl.nodes[node]['exp'],int) and G_skl.nodes[node]['step'] == 2:
            parent_wheel.append([i for i in G_skl.predecessors(node)][0])

# Path setup
HERE = Path('.').absolute()
DATA = HERE.joinpath('data')

# Time to wait between reactions and analysis
GROWTH_TIME = 3600*16

# Wait time for the reductant to take effect
REDUCTANT_WAIT_TIME = 0.0001

# List of experiments in which we control the pH using the operations
# there must be an operation json file in it
Operation_pH_index = sorted([i for i in range(24)])

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

    def __init__(self, reactions: bool = True, analysis: bool = True, current_wheel_position = min(exp_wheel_position)-1):
        super().__init__()
        self.do_reactions = reactions
        self.do_analysis = analysis
        self.current_wheel_position = current_wheel_position
        self.pH_electrode_ready = True
        self.seed_transfer_flag = True
        self.water_pump_flag = True
        self.manager.set_stir_rate("wash_fan",35)
        self.manager.wheel.home_motor("seed_v")
        self.manager.wheel.home_motor("seed_h")
        self.move_seed_transfer_to_sample_position_h()
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

    def move_seed_transfer_to_stock_position(self):
        """
        To do: 
            Move the sample_transfer unit to the wash station
        """
        self.manager.wheel.home_motor("seed_v")
        self.manager.wheel.home_motor("seed_h")
        self.manager.wheel.move_motor_to_position("seed_v",220000)
        return 

    def move_seed_transfer_to_sample_position(self):
        """
        To do: 
            Move the sample_transfer unit to the sample position
        """
        self.manager.wheel.home_motor("seed_v")
        self.manager.wheel.home_motor("seed_h")
        self.manager.wheel.move_motor_to_position("seed_h",180000)
        self.manager.wheel.move_motor_to_position("seed_v",220000)
        return

    def move_seed_transfer_to_sample_position_h(self):
        """
        To do: 
            Move the sample_transfer unit to the sample position horizontally 
        """
        self.manager.wheel.home_motor("seed_v")
        self.manager.wheel.move_motor_to_position("seed_h",180000)
        return

    def clean_seed_transfer_unit(self,n = 1):
        """
        To do:
            Clean the wash station of the sample transfer
        Args:
            n: the number of cleaning times
        """

        for i in range(n):
            self.manager.dispense(
                "wheel_seed",
                11,
                in_valve=cst.INLET,
                out_valve=cst.OUTLET,
                speed_in=cst.DEFAULT_SPEED,
                speed_out=cst.FAST_SPEED)
            # make sure water pump is not being used currently
            while True:
                if self.water_pump_flag == True:
                    break
                time.sleep(0.5)
            
            # label it as being used
            self.water_pump_flag = False
            self.manager.dispense(
                "water",
                10,
                in_valve=cst.WATER_STOCK,
                out_valve=cst.WATER_TO_SEED,
                speed_in=cst.SLOW_SPEED,
                speed_out=cst.FAST_SPEED)  
            # release water pump
            self.water_pump_flag = True
          
        self.move_seed_transfer_to_sample_position_h()
        return

    def transfer_seed_from_x_to_y(self, x, y = 0, transfer_position = 14):
        """
        To do:
            Transfer seed solutions from the vial exiting in the wheel
        Args:
            x: the position of the vial containing the seeds. Integer between 0 and 23.  
            y: the position of the destination vial. Integer between 0 and 23.  
            transfer_position: the position where the transfer unit gets the solution. Integer between 0 and 23.  
        """
        # calculate the turn numbers to move x position to transfer_position
        if x == transfer_position:
            turn_num = 0
        elif x < transfer_position:
            turn_num = 24-(transfer_position - x)
        else:
            turn_num = x - transfer_position
            
        # calculate the turn numbers to move y position to transfer_position
        if y == transfer_position:
            turn_num_for_y = 0
        elif y < transfer_position:
            turn_num_for_y = 24-(transfer_position - y)
        else:
            turn_num_for_y = y - transfer_position
        # because we will turn turn_num times first. turn_num_for_y should substrate turn_num to be the real number
        if turn_num_for_y >= turn_num:
            turn_num_for_y_real = turn_num_for_y - turn_num
        else:
            turn_num_for_y_real = turn_num_for_y - turn_num + 24

        # turn the wheels so the seed vial reaches the position for transferring
        self.manager.turn_wheel(cst.WHEEL_NAME,int(turn_num))
        self.move_seed_transfer_to_sample_position_h()
        # move the motor to the destination position (assume it is moved horizontally)
        self.manager.wheel.move_motor_to_position("seed_v",220000)
        # get preflesh the wheel_seed line
        self.manager.dispense(
            "wheel_seed",
            2,
            in_valve=cst.INLET,
            out_valve=cst.OUTLET,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED)
        # get preflesh the wheel_seed line and dispense part of the solution
        # Store the rest of the solution in the syringe  for sometime
        residual_vol = self.manager.partial_dispense(
            "wheel_seed",
            volume_in=1.0,
            volume_out=0.5,
            in_valve=cst.INLET,
            out_valve=cst.OUTLET,
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED
        )
        # move the unit up
        self.manager.wheel.move_motor_to_position("seed_v",0)
        # put the y vial to the transfer_position
        self.manager.turn_wheel(cst.WHEEL_NAME,int(turn_num_for_y_real))
        # lower down the unit, dispense the rest of the seeds and move it up
        self.manager.wheel.move_motor_to_position("seed_v",220000)
        self.manager.partial_dispense(
            "wheel_seed",
            volume_out=residual_vol,
            in_valve=cst.INLET,
            out_valve=cst.INLET,    
            speed_in=cst.DEFAULT_SPEED,
            speed_out=cst.FAST_SPEED
        )
        self.manager.wheel.move_motor_to_position("seed_v",0)
        threading.Thread(target = self.clean_seed_transfer_in_parallel).start()
        # restore the relative positions of the wheel
        self.manager.turn_wheel(cst.WHEEL_NAME,int(24 - turn_num_for_y))
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

            while True:
                if self.water_pump_flag == True:
                    break
                time.sleep(0.5)
            # label it as being used
            self.water_pump_flag = False

            self.manager.dispense(
                "water",
                volume = 10,
                in_valve=cst.WATER_STOCK, 
                out_valve=cst.WATER_TO_PH,
                speed_out=cst.FAST_SPEED)
            
            self.water_pump_flag = True

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
    def clean_seed_transfer_in_parallel(self):
        """
        Clean the seed transfer uniti in parallel
        """
        self.seed_transfer_flag = False
        # move the unit for washing and this part can be parallel
        self.move_seed_transfer_to_stock_position()
        self.clean_seed_transfer_unit()
        self.seed_transfer_flag = True

    def reaction_protocol(self, xp_path: str, parent_wheel_position):
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
        
        while True:
            if self.seed_transfer_flag == True:
                break
            time.sleep(0.1)
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
                elif reagent.name == 'seeds':
                    self.transfer_seed_from_x_to_y(x = (parent_wheel_position - self.current_wheel_position)%24, y = 0, transfer_position = 14)
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
        uv, ir, uv_ref, ir_ref = self.manager.obtain_uv_ir_spectra2()
        uv.dump_spectrum(str(xp_path)+'/uv.json')
        ir.dump_spectrum(str(xp_path)+'/ir.json')
        uv_ref.dump_spectrum(str(xp_path)+'/uv_ref.json')
        ir_ref.dump_spectrum(str(xp_path)+'/ir_ref.json')
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
        self.preflush_pumps2(
            'silver',
            'gold',
            'hydroquinone',
            'seeds',
            ("water_reagent",1.5),
            ('surfactant',3 ),
            ("ph_acid",1),
            ("ph_base",1),
        )
        self.current_wheel_position = self.current_wheel_position + 1
        self.manager.set_stir_rate("wash_fan",35)
        self.activate_ring_stirrer(speed=35)
        # Get all experiments to perform in order
        # Only 1 file means no analysis has been performed
        xp_list = sorted([
            xp for xp in self.root_xp_folder.iterdir()
            if not xp.is_file()
        ])

        # the experiments that will be done in this script 
        xp_list_1 = [xp_list[i] for i in exp_list]
        # the experiments that will be analyzed in this script 
        analysis_list_1 = [xp_list[i] for i in analysis_list]

        # No experiments to conduct, Finish
        if not xp_list:
            self.manager.logger.warning(
                f"No experiments to do for {self.root_xp_folder}"
            )
            return

        # Before we put the pH probe into the sample, clean it with water once to get rid of KCl
        clean_probe_flag = 'y'
        if clean_probe_flag == "y":
            self.clean_probe(1)

        
        # Refresh the pH measurement with calibrated data
        with open(f'{self.root_xp_folder}/calibration.json') as json_file:
            pH_json = json2.load(json_file)
        self.manager.ph_module.update_calibrations([pH_json["pH4"],pH_json["pH7"],pH_json["pH10"]])

        # input('Press Enter to start!')
        # Conduct reactions if flag set
        if self.do_reactions:
            # Let user know we're starting
            # self.manager.send_slack_message("Starting reaction sequence.")

            # Activate the stirrers on the ring
            self.activate_ring_stirrer(speed=35)

            self.xp_index = 0
            # Execute reaction
            for xp in xp_list_1:
                self.reaction_protocol(xp,parent_wheel[self.xp_index])
                self.activate_ring_stirrer(speed=35)
                self.xp_index = self.xp_index + 1
                self.current_wheel_position = self.current_wheel_position + 1

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

            self.manager.dispense(
            "surfactant",
            5,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET,
            speed_out=cst.FAST_SPEED)
            
            # Wait for a set time after dispensing
            mins, hours = int(GROWTH_TIME / 60), int(GROWTH_TIME / 60 / 60)
            self.manager.logger.info(f"Waiting for {mins} mins...")
            time.sleep(GROWTH_TIME)

        analysis_wheel_turn = 0
        # Analyse reactions if flag set
        if self.do_analysis:
            for analytic_index in range(len(analysis_wheel_position)):
                # calculate the current wheel position
                self.current_wheel_position = self.current_wheel_position%24
                # keep rotating it until it mathes with the analytical wheel position
                while self.current_wheel_position != (7+analysis_wheel_position[analytic_index])%24:
                    self.manager.turn_wheel(cst.WHEEL_NAME,1)
                    self.current_wheel_position = (self.current_wheel_position+1)%24
                    analysis_wheel_turn = analysis_wheel_turn + 1

                # Do the analysis
                xp = analysis_list_1[analytic_index]
                self.analysis_protocol(xp)
                self.current_wheel_position = (self.current_wheel_position+1)%24
                analysis_wheel_turn = analysis_wheel_turn + 1

        self.manager.reverse_wheel(cst.WHEEL_NAME)
        self.manager.turn_wheel(cst.WHEEL_NAME, analysis_wheel_turn - 1)
        self.manager.reverse_wheel(cst.WHEEL_NAME)

if __name__ == "__main__":
    if "-a" in sys.argv:
        BasicExperiment(reactions=False).full_protocol()
    elif "-r" in sys.argv:
        BasicExperiment(analysis=False).full_protocol()
    else:
        BasicExperiment().full_protocol()
