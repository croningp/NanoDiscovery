# Config file for PyDScat-GPU simulation
The major part was written in Python. The config file defines the necessary information for simulation. There're several parameters in the config file (a dictionary and usually stored as a json file) and see the information below for different parameters:
1. 'gpu_device': '/GPU:0',
- defines the GPU device to be used
2. 'dipole_length': 1,
- defines the length of dipole in nanometer
3. 'min_wavelength': 0.4, 
- defines the lowest wavelength for spectrum in micrometer
4. 'max_wavelength': 0.8, 
- defines the highest wavelength for spectrum in micrometer
5. 'num_wavelengths': 41, 
- defines the number of linear interval between lowest and highest wavelength
6. 'ref_medium': 1.333, 
- defines the medium of the simulation
7. 'rotation_steps': 10, 
- defines the average number of orientations for every solid angle
8. 'folder_path': None, 
- defines the folder path where we store the data (still in test so some data may store in the current folder)
9. 'calculate_electricField': False, 
- defines if we will calculate the local electric field
10. 'metals': ["Au","Ag"], 
- defines the metallic components in the nanoparticles
11. 'ref_data': [str(current_folder_path) + '/Au_ref_index.csv',str(current_folder_path) + '/Ag_ref_index.csv'],
-  defines the refractive index for components respectively. Keep the sequence of paths consistent with those in metals.
12. 'dipole_data': str(current_folder_path)+'/Core_shell' + '/dipole_list.csv',
- defines the position of dipoles. Always integer. 
13. "method":"heter_atomic",
- defines the method for the simulation. It can be "homo", "heter_atomic" or "heter_custom"
14. "ratio":None,
- has to be defined for method "homo", else not required. A list object recording the percentages of different components of the homogenous nanoparticle. The summation should be 1. 
15. "custom_ratio_path":None
- has to be defined for method "heter_custom", else not required. Path to the csv file storing the custom component percentages for dipoles. After reading in the csv file, we should have a n by N array, where n is the metallic component number and N is the dipole number.
16. 'atom_data': str(current_folder_path)+'/Core_shell' + exp_index + '/atomList_Octahedron.csv',
- has to be defined for method "heter_atomic", else not required. It defines the path for the positions of atoms. Always normarlized to lattice unit. 
17. 'lattice_constant': 0.41
- has to be defined for method "heter_atomic", else not required. It defines the lattice constant for an atomic model

[Mathematica >= 12.0](https://www.wolfram.com/mathematica/) was used to generate dipoles or create meshes to calculate the electric field distribution if 'calculate_electricField' is True. For this calculation, the dipole length and the lattice constant should be set in [NanoparticleProperties.wl](NanoparticleProperties.wl) accordingly. The path in [dipole_analysis.wls](dipole_analysis.wls) should be changed accordingly to load the package. 