# Nanomaterials Discovery
Control software of the robotic platform.
## Nanobot manager
The basic functions and classes are defined [here](Nanobot) to conduct the synthesis and UV-Vis characterization using the platform. [ModularWheelPlatform](modularwheelplatform) should be installed as well. The spectral data analysis and algorithm to design new experiments are seperated from the control software to give enough flexiblity and generality of the platform with various machine learning methods for different purposes.  
## The closed loop
The closed loop was established by three stages including:
1. Design of experiments;
2. Nanoparticle synthesis, characterization and cleaning of the platform;
3. UV-Vis data analysis, which will be used in the algorithm later.

Here we gave an [exmaple](NanobotExperiments/experiments) of exploring the chemical space using MAP-Elites algorithm. Three notebooks and one python script were used for [overall control](NanobotExperiments/experiments/Run_experiment.ipynb), [experimental design](NanobotExperiments/experiments/Algorithm.ipynb), [spectral data analysis](NanobotExperiments/experiments/UV-Vis.ipynb) and [robotic control](NanobotExperiments/experiments/basic.py). 
### Instructions
1. To establish the loop, run the notebooks for [experimental design](NanobotExperiments/experiments/Algorithm.ipynb) and [spectral data analysis](NanobotExperiments/experiments/UV-Vis.ipynb) in the background first. They will wait for the instructions before further continuing. 
2. Then run the notebook for [overall control](NanobotExperiments/experiments/Run_experiment.ipynb) to establish control. Once it requires to run the robot, open a seperate terminal to run the script for [robotic control](NanobotExperiments/experiments/basic.py) to synthesize nanoparticles and collect the UV-Vis data. DO NOT PRESS ENTER UNTIL ALL EXPERIMENTS ARE FINISHED. 

Once the data are collected, spectral data are analysed and a signal will be sent to the algorithm to design new experiments. Once the algorithm designs the new experiments, the robot can conduct the experiments again. This process is iterated until the exploration is complete. The example contains 10 steps for the exploration of multiple peak features. 

## The multistep synthesis
The multistep synthesis was built on three directed graph. An example of synthesizing six nanostructures at once is given [here](Graph_Experiment/experiments). 
