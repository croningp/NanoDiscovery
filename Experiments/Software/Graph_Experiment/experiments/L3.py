"""
.. module:: experiments.basic_experiment
    :platform: Unix
    :synopsis: Basic Experiment child class for running the system

.. moduleauthor:: Graham Keenan (Cronin Group 2019)

"""

# System imports
import sys
import time
from pathlib import Path
import numpy as np 
import threading
import networkx as nx

# Platform imports
from core import CoreExperiment
import nanobot.constants as cst
from modularwheel.utils import json_utils as json

# Set up the Graph
G_skl = nx.read_gpickle("harware_graph.gpickle")
# the experiments that will be conducted in the wheel
wheel_position_list = [G_skl.nodes[node]['exp'] for node in G_skl]

# get the expeirments to be done with 1 step
exp_list = []
for node in G_skl:
    if isinstance(G_skl.nodes[node]['exp'],int):
        if G_skl.nodes[node]['step'] == 3:
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
    if isinstance(G_skl.nodes[node]['exp'],int) and G_skl.nodes[node]['step'] == 3:
            parent_wheel.append([i for i in G_skl.predecessors(node)][0])
        
# Path setup
HERE = Path('.').absolute()
DATA = HERE.joinpath('data')

# Time to wait between reactions and analysis
GROWTH_TIME = 3600

# Wait time for the reductant to take effect
REDUCTANT_WAIT_TIME = 0.0001

# List of experiment indexes to analyse, empty means all of them
ANALYTICAL_INDEX = sorted([0])

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
        self.manager.set_stir_rate("wash_fan",35)
        self.seed_transfer_flag = True
        self.manager.wheel.home_motor("seed_v")
        self.manager.wheel.home_motor("seed_h")
        self.move_seed_transfer_to_sample_position_h()
        self.current_wheel_position = current_wheel_position

    def __del__(self):
        """Send an email once the script has concluded"
        """

        # Send emails to users when finished
        self.manager.send_emails(
            f"Experiment {self.info[cst.TITLE]} is complete!", cst.EMAILS
        )

        # Send slack message
        self.manager.send_slack_message(
            f'Experiment {self.info[cst.TITLE]} complete!'
        )
    def move_probe_to_sample_position(self):
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_HORZ_MODULE,80000)
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE,42500)
        return 

    def move_probe_to_stock_position(self):
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_HORZ_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE,42500)
        return

    def clean_probe(self):
        self.move_probe_to_stock_position()
        
        for i in range(3):
            self.manager.dispense(
                cst.SAMPLE_PUMP,
                volume = 12,
                in_valve="6",
                out_valve=cst.SAMPLE_WASTE,
                speed_out=cst.FAST_SPEED)

            self.manager.dispense(
                "water",
                volume = 10,
                in_valve=cst.WATER_STOCK, 
                out_valve=cst.WATER_TO_PH,
                speed_out=cst.FAST_SPEED)

            time.sleeps(10)
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
        self.manager.wheel.move_motor_to_position("seed_h",180000)
        self.manager.wheel.move_motor_to_position("seed_v",220000)
        return

    def clean_seed_transfer_in_parallel(self):
        """
        Clean the seed transfer uniti in parallel
        """
        self.seed_transfer_flag = False
        # move the unit for washing and this part can be parallel
        self.move_seed_transfer_to_stock_position()
        self.clean_seed_transfer_unit()
        self.seed_transfer_flag = True

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

            self.manager.dispense(
                "water",
                10,
                in_valve=cst.WATER_STOCK,
                out_valve=cst.WATER_TO_SEED,
                speed_in=cst.SLOW_SPEED,
                speed_out=cst.FAST_SPEED)            
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

        params = self.manager.convert_params_dict_to_reagents(params)
        while True:
            if self.seed_transfer_flag == True:
                break
            time.sleep(0.1)
            
        # Dispense all reagents
        self.manager.logger.info(f"Dispensing reagents: {params}")
        for reagent in params:
            if reagent.name == 'seeds':
                # transfer the seed and clean the seed unit
                self.transfer_seed_from_x_to_y(x = (parent_wheel_position - self.current_wheel_position)%24, y = 0, transfer_position = 14)
            elif reagent.name != cst.WATER_PUMP:
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
                    "water_reagent",
                    reagent.volume,
                    in_valve=reagent.in_valve,
                    out_valve=reagent.out_valve,
                    speed_out=cst.FAST_SPEED)

            # Give time for reducing
            if reagent.name == 'reductant':
                time.sleep(REDUCTANT_WAIT_TIME)

        # Turn the wheel
        self.manager.turn_wheel(cst.WHEEL_NAME)
    
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
        self.manager.set_stir_rate("wash_fan",35)

        self.preflush_pumps2(
            'HCl',
            'silver',
            'gold',
            'reductant',
            'seeds',
            ('water_reagent', 1.5),
            ("CTAC",1.5),
        )
        self.current_wheel_position = self.current_wheel_position + 1

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
        # Conduct reactions if flag set
        if self.do_reactions:
            # Let user know we're starting
            # self.manager.send_slack_message("Starting reaction sequence.")

            # Activate the stirrers on the ring
            self.activate_ring_stirrer(speed=35)
            
            # Execute reaction
            self.xp_index = 0
            # Execute reaction
            for xp in xp_list_1:
                self.reaction_protocol(xp,parent_wheel[self.xp_index])
                self.activate_ring_stirrer(speed=35)
                self.xp_index = self.xp_index + 1
                self.current_wheel_position = self.current_wheel_position + 1
            # Stop the stirrers after dispensing
            self.kill_ring_stirrers()
            self.manager.set_stir_rate("wash_fan",35)

            self.manager.dispense(
            "surfactant",
            5,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET,
            speed_out=cst.FAST_SPEED)

            # Wait for a set time after dispensing
            mins, hours = int(GROWTH_TIME / 60), int(GROWTH_TIME / 60 / 60)
            self.manager.logger.info(f"Waiting for {mins} mins...")
            self.manager.send_slack_message(
                f"Finished dispensing, waiting {hours} hours."
            )
            time.sleep(GROWTH_TIME)

            # Move into sample position
            # self.manager.turn_wheel(
            #     cst.WHEEL_NAME, n_turns=cst.DISPENSE_TO_SAMPLE_POSITION
            # )

        # Analyse reactions if flag set
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
