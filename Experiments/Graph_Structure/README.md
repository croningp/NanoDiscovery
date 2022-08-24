# Directed Graph Structure of Multistep Synthesis of Au NPs
Create synthesis,reaction and hardware graph of a complex nanostructure network with dedicated synthetic conditions.

## Example code
One example is available [here](Graph_Generator.ipynb). 
The synthetic conditions of different nanostructures should be defined in [exp_info.json](exp_info.json).

After running the example code, [experiments](Experiment) and [three graphs](Graphs) can be generated. 

The experimental data should be copies to the [custom folder](../Software/Graph_Experiment/data/custom) in the software control. Also, we recorded the operations to reach certain pHs when finding the nanostructures in the second batch and used them in reproducing them. So "pH_operation.json" files were added in the same folder. 

Copy all the content in [Graphs](Graphs) to the [experiments](../Software/Graph_Experiment/experiments) folder in Graph_Experiment and run the [Python script](../Software/Graph_Experiment/experiments/basic.py) will synthesize the six nanostructures. 
