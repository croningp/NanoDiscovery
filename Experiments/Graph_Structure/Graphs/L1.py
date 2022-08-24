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
import networkx as nx
import numpy as np 

# Platform imports
from core import CoreExperiment
import nanobot.constants as cst
from modularwheel.utils import json_utils as json
import json as json2

# initialize with Graphic structures
G_skl = nx.read_gpickle("harware_graph.gpickle")

# the experiments that will be conducted in the wheel
wheel_position_list = [G_skl.nodes[node]['exp'] for node in G_skl]
# get the expeirments to be done with 1 step
exp_list = []
for node in G_skl:
    if isinstance(G_skl.nodes[node]['exp'],int):
        if G_skl.nodes[node]['step'] == 1:
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


# Path setup
HERE = Path('.').absolute()
DATA = HERE.joinpath('data')

# Time to wait between reactions and analysis
GROWTH_TIME = 7200

# Wait time for the reductant to take effect
REDUCTANT_WAIT_TIME = 10

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

    def __init__(self, reactions: bool = True, analysis: bool = True, current_wheel_position = 0):
        super().__init__()
        self.do_reactions = reactions
        self.do_analysis = analysis
        self.current_wheel_position = current_wheel_position
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
    def move_probe_to_sample_position(self):
        self.manager.wheel.move_motor_to_position(cst.PH_VERT_MODULE, 0)
        self.manager.wheel.move_motor_to_position(cst.PH_HORZ_MODULE, 80000)
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

        params = self.manager.convert_params_dict_to_reagents(params)

        # Dispense all reagents
        self.manager.logger.info(f"Dispensing reagents: {params}")

        for reagent in params:
            if reagent.name != cst.WATER_PUMP:
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
            'silver',
            'gold',
            'reductant',
            'seeds',
            ('water_reagent', 1.5),
            ('surfactant',3 )
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
            # Activate the stirrers on the ring
            self.activate_ring_stirrer(speed=35)

            # Execute reaction
            for xp in xp_list_1:
                self.reaction_protocol(xp)
                self.activate_ring_stirrer(speed=35)
                self.current_wheel_position = self.current_wheel_position + 1 # keep tracking the wheel position
            # Stop the stirrers after dispensing
            self.kill_ring_stirrers()
            self.manager.set_stir_rate("wash_fan",35)

            # the final flush of the surfactant after experiments
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