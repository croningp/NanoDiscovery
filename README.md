# Autonomous Intelligent Exploration, DIScovery and Optimisation of Nanomaterials (AI-EDISON)
Software and hardware control of AI-EDISON. The version-specific repository for the paper is available in Zenodo [here](https://zenodo.org/record/6654585). From that version, this repository has been updated from three perspectives below, but no relevant codes/files used in the work have been changed:

1. We corrected some typo errors and updated multiple README.md files as well as statements of license/restrictions for a clearer guidance; 
2. We have added some additional contents which include: a missing [license](Experiments/Software/modularwheelplatform/modularwheel/drivers/pH/DrDAQ/LICENSE.md) of DrDAQ driver locally to this repository (the preivous hyperlink was not valid); the [source codes](Theory/Optimization_targets) to simulate the target spectra for the experimental optimization in the paper.
3. We updated several unused/invalid links, scripts and functions (e.g., several links in [requirement.txt](Experiments/Software/modularwheelplatform/requirements.txt) and the "dense_to_sparse" function (which contains a variable error but was never used) in [dda.py](Theory/PyDScat-GPU/dda.py)) to avoid potential ambiguity.

**Please refer to this repository for general guidance and license information.**

![](./Images/robot.jpg)
## Experiment

### Hardware construction
The full bill of materials to construct the robot are available [here](Experiments/Hardware).
### Software control requirement
The following software are required to control the robot:
* Python >= 3.6 ([Linux](http://docs.python-guide.org/en/latest/starting/install3/linux/) / [Windows](https://www.python.org/downloads/release/python-363/))
* [Arduino Command Handler](https://github.com/croningp/Arduino-CommandHandler)
* [Arduino Command Tools](https://github.com/croningp/Arduino-CommandTools)
* [pySerial 3.4](https://github.com/pyserial/pyserial/)
* [SerialLabware](https://www.science.org/doi/10.1126/science.abo0058)
* [pycont](https://github.com/croningp/pycont)
* [commanduino](https://github.com/croningp/commanduino)
* [CommanduinoLabware](https://www.science.org/doi/10.1126/science.abo0058)
* [InorganicClusterDiscovery](https://github.com/croningp/InorganicClusterDiscovery)
* [XDL](https://croningroup.gitlab.io/chemputer/xdl/standard/index.html) (with its gitlab link [here](https://gitlab.com/croningroup/chemputer/xdl)) (Note we used XDL 1 in this work. Specifically, [XDL 1.6.0](https://gitlab.com/croningroup/chemputer/xdl/-/tree/v1.6.0) was used to generate the digital signatures of the six AuNPs.)
* [SeaBreeze](https://python-seabreeze.readthedocs.io/en/latest/)
* [PicoTech](https://github.com/picotech/picosdk-python-wrappers)
* [ModularWheelPlatform](Experiments/Software/modularwheelplatform)
* [Nanobot](Experiments/Software/Nanobot)

Go to the corresponidng folders of [ModularWheelPlatform](Experiments/Software/modularwheelplatform) and [Nanobot](Experiments/Software/Nanobot), and use "pip install ." to install these two packages. In ModularWheelPlatform, we used [DrDAQ](https://www.picotech.com/data-logger/drdaq/overview) to measure the pH. In Nanobot, the code is based on [SeaBreeze](https://python-seabreeze.readthedocs.io/en/latest/) from Ocean Optics to control the spectrometers. For the usage of UV-Vis spectrum, the integration time is set (either 0.01 or 0.02 s) to avoid spectral saturation.

<!-- ### Python library -->
<!-- To install all required Python libraries, run the following command: `pip install -r requirements.txt` -->
### Exploration with MAP-Elites
The MAP-Elites algorithm was described in the manuscript and supplementary information. An example of exploring the multiple-peak systems in chemical sapce 2 with pH control is available [here](Experiments/Software).
<!-- ### Optimisation with GS-LS 
The GS-LS algorithm was described in the manuscript and supplementary information. An example of optimizing towards a target spectrum of nanorods is [here](Experiments/Software). -->
### Simulating the target spectra for experimental optimisation
The original codes to simulate the target spectra for Au nanorods/octahedra for the experimental optimisation are [here](Theory/Optimization_targets). See below for more information about the simulation engine PyDScat-GPU.
### Multistep synthesis with directed graph structure
The codes to generate syntehsis/reaction/hardware graph, and control the robot are available [here](Experiments/Graph_Structure).
### The unique digital signatures of the synthesised nanoparticles
The codes to generate the unique digital signatures using XDL are available [here](Experiments/Hash_XDL).
## Theory
### Software requirement
* Python >= 3.6 ([Linux](http://docs.python-guide.org/en/latest/starting/install3/linux/) / [Windows](https://www.python.org/downloads/release/python-363/))
* [numpy](https://numpy.org/)
* [matplotlib](https://matplotlib.org/)
* [Tensorflow >= 2.0](https://www.tensorflow.org/)
* [pathlib](https://docs.python.org/3/library/pathlib.html)
* [fresnel](https://fresnel.readthedocs.io/en/stable/)
* [Mathematica >= 12.0](https://www.wolfram.com/mathematica/)
### PyDScat-GPU
PyDScat-GPU is developed for efficient scaterring simulations with [discrete-dipole approximation](https://en.wikipedia.org/wiki/Discrete_dipole_approximation) method. One example was given below, and see [here](Theory/PyDScat-GPU/) for more details and examples. 
#### Example code
```python
import os
import json
import pathlib
import numpy as np
from dda import DDA

# GPU Device Config
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   
os.environ["CUDA_VISIBLE_DEVICES"]="3"

current_folder_path = pathlib.Path().absolute()

config = {'gpu_device': '/GPU:0',
          'dipole_length': 1,
          'min_wavelength': 0.4,
          'max_wavelength': 0.8,
          'num_wavelengths': 41,
          'ref_medium': 1.333,
          'rotation_steps': 10,
          'folder_path': None,
          'calculate_electricField': True,
          'lattice_constant': 0.41,
          'ref_data': [str(current_folder_path) + '/Au_ref_index.csv',str(current_folder_path) + '/Ag_ref_index.csv'],
          'metals': ["Au","Ag"],
          'dipole_data': str(current_folder_path)+ '/dipole_list.csv',
          "ratio":[1.0, 0.0],
          "method":"homo",
          "custom_ratio_path":None,
          'atom_data':None,
          'lattice_constant': None
        }
config['folder_path'] = str(current_folder_path)
np_dda = DDA(config)
np_dda.run_DDA()
np_dda.plot_spectra()
np.savetxt("Results.csv",np.array(np_dda.C_cross_total)/np.pi/np_dda.c_rad**2,delimiter=",")
```
### Benchmark of MAP-Elites and GS-LS
Both MAP-Elites and GS-LS algorithms were benchmarked in a simulated chemical space using [superellipsoid](https://en.wikipedia.org/wiki/Superellipsoid) as the shape descriptor. The code of creating the discrete dipoe representation of a superellipsoid is [here](Theory/Superellipsoid). We created the set of dipoles by changing the (a,b,c,r,t) parameters of the createDipoles function in the [mathematica notebook](Theory/Superellipsoid/Superellipsoid_Generate_Dipoles.nb) to approximate the specific geometry. 
#### *In silico* exploration using MAP-Elites
The codes to reproduce the results from the in silico exploration of two simulated chemical spaces are [here](Theory/Algorithms). 
#### *In silico* optimisation using GS-LS
The code to reproduce the results from the in silico optimisation is [here](Theory/Algorithms/Simulated_Space_2/1-GS-LS).


## License
The [license](LICENSE) aims to protect the design of the robot in this work for non-commercial usage only. For the codes used in this work, see [here](http://www.chem.gla.ac.uk/cronin/media/license/) for the license information. However, if the licenses listed here are incompatible with the licenses of certain resources that parts of this work are based on, the original licenses of these resources should be used for the relevant parts of this work.

Copyright 2022 The Cronin Group, University of Glasgow.
