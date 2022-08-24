# -------------------------------------------------------------------------------------- #
# ---------- DISCRETE DIPOLE METHOD FOR UV-VIS CALCULATIONS FROM DIPOLE DATA ----------- #
# -------------------------------------------------------------------------------------- #

import csv
import PIL
import pathlib
import fresnel
import subprocess
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

from multiprocessing import Process
from scipy.interpolate import interp1d

class DDA:

    def __init__(self, config):

        self.gpu_device = config["gpu_device"]
        self.dl = config["dipole_length"]*0.001     # Converting into microns.
        self.wl_min = config["min_wavelength"]
        self.wl_max = config["max_wavelength"]
        self.n_wl = config["num_wavelengths"]
        self.ref_medium = config["ref_medium"]
        self.rot_steps = config["rotation_steps"]
        self.folder_path = config["folder_path"]
        self.calculate_electricfield = config["calculate_electricField"]

        self.n_real = []
        self.n_imag = []
        self.dipole_list = []
        self.C_cross_total = []
        self.wl_exp = np.linspace(self.wl_min, self.wl_max, self.n_wl)

        self.ref_filepath = pathlib.Path(config["ref_data"])
        assert self.ref_filepath.is_file()

        self.dipole_filepath = pathlib.Path(config["dipole_data"])
        assert self.dipole_filepath.is_file()


        if len(self.dipole_list) >= 6000:
            print(f' ----- WARNING: TOO MANY DIPOLES ----- \n Number of dipoles: {len(self.dipole_list)}')

        self.initialize_sim()


    def initialize_sim(self):
        """
            Setting up the simulation and initialzing the simulation parameters
        """
        print('Reading refractive index and dipole data')
        self.read_dielectric_data()
        self.read_dipole_data()

        print('Calculating radius of the cross section and polarizability')
        self.c_rad = self.calculate_r()
        self.calculate_polarizability()


    def read_dielectric_data(self, plot_data=True):
        """
        Imports dielectric data for metals (Complex refractive index)
        :return None:
        """
        ref_data = np.genfromtxt(self.ref_filepath, skip_header=1, delimiter=',')

        if plot_data:
            fig, ax = plt.subplots()
            ax.set_xlabel("Wavelength (microns)")
            ax.set_ylabel("n, k")
            ax.plot(ref_data[:,0], ref_data[:,1], color='r', label='n')
            ax.plot(ref_data[:,0], ref_data[:,2], color='b', label='k')
            leg = ax.legend();
            fig.savefig(self.folder_path + '/ref_index.png', format='png', dpi=300)
            plt.close()
            
        self.n_real = interp1d(ref_data[:,0], ref_data[:,1], kind='cubic')
        self.n_image = interp1d(ref_data[:,0], ref_data[:,2], kind='cubic')


    def read_dipole_data(self):
        """
        Reads dipole coordinates from the file and plots them
        :return: numpy.array list of atomic coordinates of the initial nanoparticle        
        """
        self.dipole_list = np.loadtxt(self.dipole_filepath, delimiter=",")
        self.dipole_list = self.dipole_list*self.dl

        if self.calculate_electricfield:
            output = subprocess.run(['wolframscript', 'dipole_analysis.wls', self.folder_path, str(self.dipole_filepath)], stdout=subprocess.PIPE)
            print(output.stdout.decode('utf-8'))

        scene = fresnel.Scene()
        geometry = fresnel.geometry.Sphere(scene, N=len(self.dipole_list), radius=self.dl)
        geometry.position[:] = self.dipole_list
        geometry.material = fresnel.material.Material(color=fresnel.color.linear([0.9, 0.714, 0.169]), roughness = 0.2)
        
        out = fresnel.preview(scene)
        image = PIL.Image.fromarray(out[:], mode='RGBA')
        image.save(self.folder_path + '/dipolePlot.png')
        return fresnel.preview(scene)


    def read_mesh_data(self):
        """
        Reads positions of mesh elements for calculating electric field
        :return: numpy.array list of coordinates of mesh elements calculated from WolframScript
        """
        self.mesh_list = np.loadtxt(self.mesh_filepath, delimiter=",")
        return


    def calculate_rotation_matrix(self, theta_x, theta_y, theta_z):
        """
        Calculates the rotation matrix for rotational operations in Euclidean space.
        :param theta_x: Rotation operation along X
        :param theta_y: Rotation operation along Y
        :param theta_z: Rotation operation along Z
        :returns rot_matrix: 3x3 rotation matrix
        """  
        
        rot_x = tf.constant([[1.0, 0.0, 0.0],
                             [0.0, np.cos(theta_x), -np.sin(theta_x)],
                             [0.0, np.sin(theta_x),  np.cos(theta_x)]], dtype=tf.complex64)

        rot_y = tf.constant([[ np.cos(theta_y), 0.0, np.sin(theta_y)],
                             [ 0.0, 1.0, 0.0],
                             [-np.sin(theta_y), 0.0, np.cos(theta_y)]], dtype=tf.complex64)

        rot_z = tf.constant([[np.cos(theta_z), -np.sin(theta_z), 0.0],
                             [np.sin(theta_z),  np.cos(theta_z), 0.0],
                             [0.0, 0.0, 1.0]], dtype=tf.complex64)

        rot_matrix = tf.matmul(rot_z, tf.matmul(rot_y, rot_x))
        return rot_matrix


    def dense_to_sparse(self, mat):
        """
        Converts a dense matrix to sparse matrix.
        :param mat: dense matrix 
        :returns sparse_mat: sparse matrix
        """
        idx = tf.where(tf.not_equal(mat, 0))
        sparse_mat = tf.SparseTensor(idx, tf.gather_nd(x, idx), x.get_shape())
        return sparse_mat


    def delete_1D(self, new_position, position):
        """
        Deletes the dipole
        :param new_position: 
        :param position:
        :returns A:
        """
        A = np.array(np.around(new_position, 7)).tolist()
        B = np.array(np.around(position, 7)).tolist()
        A = [i for i in A if i not in B]
        return A


    def calculate_r(self):
        """
        Calculates the radius for the cross section of the nanoparticle defined by dipole volume
        :param d: dipole length
        :param N:Total number of dipoles
        :returns: Radius of the cross section of the nanoparticle
        """
        return ((self.dl**3)*len(self.dipole_list)*3/4/np.pi)**(1/3)


    def calculate_polarizability(self):
        """
        Calculates the polarizability (alpha_j) from the refractive index data for a given dipole.
        Uses Clausius-Mossotti and FLTRD Relationship

        :return alpha_j: Polarizability of the dipole
        """

        ref_target = (self.n_real(self.wl_exp) + 1j*self.n_image(self.wl_exp)).astype("complex64") 
        ref_rel = ref_target/self.ref_medium 
        wl_rel = self.wl_exp/self.ref_medium 
        self.k = 2*np.pi/wl_rel 

        # Clausius-Mossotti polarizability and FLTRD polarizability 
        alpha_CM=3*(self.dl**3)*(ref_rel**2-1)/4/np.pi/(ref_rel**2+2)
        D = alpha_CM/(self.dl**3)*(4/3*((self.k*self.dl)**2)+
            2/3/np.pi*np.log((np.pi-self.k*self.dl)/(np.pi+self.k*self.dl))*((self.k*self.dl)**3)+2j/3*((self.k*self.dl)**3))
        self.alpha_j = alpha_CM/(1+D)
        

    def calculate_Amatrix(self, r, k, alpha_j):
        """
        Calculates A matrix for Discrete Dipole Method based on the fomulation given in : 
        Discrete Dipole Approximation for Scattering Calculations
        
        :param r: Position vector of the dipole
        :param k: Wave number
        :param alpha_j: Polarizability calculated for the given wavelength
        :return A_matrix: Calculates A matrix for the Discrete Dipole Approximation 
        """
        
        rS = tf.reshape(r, (-1,1,1,3)) - tf.reshape(r, (1,-1,1,3))

        rij = tf.reshape(tf.norm(rS,axis=(2,3)) + tf.eye(len(r), dtype=tf.complex64), (len(r), len(r), 1, 1))
        rS_norm = rS/rij
        rS2 = tf.matmul(tf.linalg.matrix_transpose(rS_norm), rS_norm)
        
        norm_k = tf.cast(tf.norm(k),tf.complex64)

        rij = tf.cast(rij,tf.complex64)
        rS2 = tf.cast(rS2,tf.complex64)

        # Calculate A matrix from the Green's function formulation
        A_matrix = tf.exp(1j*norm_k*rij)/rij*(
            ((norm_k)**2)*(rS2-tf.eye(3, dtype=tf.complex64)) + 
            (1j*norm_k*rij-1)/(rij**2)*(3*rS2 - tf.eye(3, dtype=tf.complex64)))

        # Reshape A into two-dimensional matrix
        A_matrix = tf.reshape(tf.transpose(A_matrix,(1,3,0,2)), (len(r)*3, len(r)*3))
        
        # Vanish the diagonal element and add the 1/alpha_j
        A_matrix = tf.linalg.set_diag(A_matrix, tf.zeros(A_matrix.shape[0], dtype=tf.complex64), name=None) + 1/alpha_j*tf.eye(A_matrix.shape[0], dtype=tf.complex64)
        return A_matrix
 

    def run_DDA(self):
        """
        Runs Discrete Dipole Simulation to calculate the UV-Vis Spectra of the given nanoparticle
        """
        # self.r_old = self.dl*tf.constant(self.dipole_list, dtype=tf.complex64)
        self.r_old = tf.constant(self.dipole_list, dtype=tf.complex64)

        if self.calculate_electricfield:
            self.mesh_filepath = str(self.folder_path) + '/mesh_coordinates.csv'
            self.read_mesh_data()
            self.mesh_list = tf.constant(self.mesh_list, dtype = tf.complex64)

        for index_wave in range(len(self.wl_exp)):
            C_cross = []
            print(index_wave)
            
            with tf.device(self.gpu_device):
                A_matrix1 = self.calculate_Amatrix(self.r_old, self.k[index_wave], self.alpha_j[index_wave])
                A_matrix_reverse = tf.linalg.inv(A_matrix1, adjoint=False, name=None)
                A_matrix1_shape = A_matrix1.shape[0]
                A_matrix1 = []

            with tf.device(self.gpu_device):
                rotation_matrix_incident = []
                rotation_matrix_polarization = []
                
                for theta_y in np.arccos(np.linspace(1, -1, self.rot_steps)):
                    for theta_z in np.linspace(0,2*np.pi, self.rot_steps, endpoint=False):
                        for theta_z_pol in np.linspace(0, 2*np.pi, self.rot_steps, endpoint=False):
                            rotation_matrix_incident.append(self.calculate_rotation_matrix(0, theta_y, theta_z))
                            rotation_matrix_polarization.append(self.calculate_rotation_matrix(0, 0, theta_z_pol))

                rotation_matrix_incident = tf.stack(rotation_matrix_incident)
                rotation_matrix_polarization = tf.stack(rotation_matrix_polarization)    
                
                # set the initial electric field
                E_in0 = tf.constant([[1,0,0]], dtype=tf.complex64)
                E_pol = tf.constant([[0],[0],[-self.k[index_wave]]], dtype=tf.complex64)

                # rotate the initial electric field
                E_pol_set = tf.matmul(rotation_matrix_incident, E_pol)
                E_in0_set = tf.matmul(rotation_matrix_polarization, tf.transpose(E_in0))
                E_in0_set = tf.linalg.matrix_transpose(tf.matmul(rotation_matrix_incident, E_in0_set))

                # calculate k dot r
                kdotr = tf.matmul(self.r_old, E_pol_set)

                # calculate the E_j for every dipole
                E_j = tf.exp(1j*kdotr)*E_in0_set
                E_j = tf.reshape(E_j,(E_j.shape[0],-1,1))
                E_j = tf.cast(E_j,tf.complex64)

                # calculate the dipoles
                dipoles = tf.matmul(A_matrix_reverse, E_j)

                C_cross_temp = 4*np.pi*self.k[index_wave]*tf.reduce_sum(tf.math.imag(tf.math.conj(E_j)*dipoles))/E_j.shape[0]
                C_cross.append(C_cross_temp)
                print(C_cross_temp)

                if self.calculate_electricfield:
                    local_field_total = []
                    
                    for mesh_temp in self.mesh_list:
                        local_field = self.calculate_local_electrical_field(tf.reshape(mesh_temp,(1,3)), index_wave, dipoles[0], E_pol_set[0], E_in0_set[0])
                        local_field = np.array(local_field).reshape(3)
                        local_field_total.append(local_field)

                    local_field_total = np.absolute(np.array(local_field_total))              
                    np.savetxt(str(self.folder_path) + "/EField_data_" + str(index_wave) + ".csv", local_field_total, delimiter=',')
            
            self.C_cross_total.append(C_cross)

    
    def plot_spectra(self):
        result = np.array(self.C_cross_total)/np.pi/self.c_rad**2
        n_extinction = interp1d(self.wl_exp, result.flatten(),"cubic")
        plt.xlabel("Wavelength (microns)")
        plt.ylabel("Q extinction")
        plt.plot(np.linspace(self.wl_min, self.wl_max, 1000), n_extinction(np.linspace(self.wl_min, self.wl_max, 1000)), color='black')
        plt.savefig(self.folder_path + '/UV_Vis.png', format='png', dpi=300)
        plt.close()
        np.savetxt(self.folder_path + "/Results.csv", result.flatten(), delimiter=",")


    def calculate_local_electrical_field(self, r_position, index_wave, dipoles, E_pol, E_in0):
        """
        Calculates the local electrical field distribution in a position described by r_position 
            :param r_position: an 1*3 array to describe the position 
            :param dipoles: the solved dipoles
            :param E_pol: the polarization of light
            :param E_in0: the initial incident direction (not normalized) direction of light
            :returns E_local: a 1*3 array describing the local electrical field in position r_position
        """
        with tf.device(self.gpu_device):
            # calculate the position difference
            r_diff = r_position - self.r_old
            r_norm = tf.reshape(tf.norm(r_diff,axis=1),(-1,1,1))
            r_3by3 = tf.matmul(tf.reshape(r_diff,(-1,3,1))/r_norm,tf.reshape(r_diff,(-1,1,3))/r_norm)
            norm_k=tf.cast(tf.norm(self.k[index_wave]),tf.complex64)

            # calculate the A_matrix
            A_matrix=tf.exp(1j*norm_k*r_norm)/r_norm*(
                (norm_k**2)*(r_3by3-tf.eye(3,dtype=tf.complex64))+
                (1j*norm_k*r_norm-1)/(r_norm**2)*(3*r_3by3-tf.eye(3,dtype=tf.complex64)))

            # calculate electrical field from A_matrix and solved dipoles
            E_from_dipoles = -tf.matmul(A_matrix, tf.reshape(dipoles,(-1,3,1)))

            #calculate k dot r
            kdotr = tf.matmul(r_position,E_pol)
            #calculate the E_j from the incident electrical field
            E_j = tf.exp(1j*kdotr)*E_in0
            E_j = tf.reshape(E_j, (E_j.shape[0],-1,1))
            E_j = tf.cast(E_j, tf.complex64)
            # combine the effect from dipole and incident beam
            E_local = (E_j + tf.math.reduce_sum(E_from_dipoles,axis=0))
            return E_local