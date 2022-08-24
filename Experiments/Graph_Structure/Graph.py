import numpy as np 
import networkx as nx
import matplotlib.pyplot as plt
import pylab
import json
import pathlib
from networkx.drawing.nx_agraph import write_dot, graphviz_layout

class Graph(object):

    def __init__(self):
        pass
    def convert_to_hex(self, rgba_color):
        '''
        Convert RGB values to RBG colors
        Args:
            rgba_color: List of RBG values
        Returns:
            string for the RBG color
        '''
        red = int(rgba_color[0]*255)
        green = int(rgba_color[1]*255)
        blue = int(rgba_color[2]*255)
        return '#%02x%02x%02x' % (red, green, blue)

    def initialize_synthesis_Graph(self,G_C,max_offspring_num,exp_info):
        """
        Initialize the synthesis graph by calculating the repeated experimental number
        Args:
            G_C: The synthesis Graph
            max_offspring_num: The numbers of reactions that one solution can seed
            exp_info: The synthetic conditions of the nanostructures
        Returns:
            G_C: The initialized synthesis Graph
        
        """
        # calculate the growth steps for individual experiments
        generation = []
        for node in list(G_C.nodes()):
            generation_temp = 0
            prec = [i for i in G_C.predecessors(node)] # got predecessors
            # keep getting predecessors until there is no predecessors, which tells the growth step required for the sample
            while len(prec) >0:
                generation_temp = generation_temp + 1
                prec = [i for i in G_C.predecessors(prec[0])]
            generation.append(generation_temp+1)
            G_C.nodes[node]["step"] = generation_temp
            if node>=1:
                G_C.nodes[node]["exp_info"] = exp_info["%d"%node]
        # take the offspring for every node
        for node in np.argsort(generation)[::-1]:
            prec = [i for i in G_C.predecessors(node)]
            if len(prec)>0:
                G_C.nodes[prec[0]]['offspring'] = G_C.nodes[prec[0]]['offspring'] + G_C.nodes[node]['UV_Vis'] + G_C.nodes[node]['number'] +int(np.ceil(G_C.nodes[node]['offspring']/max_offspring_num))
        return G_C

    def initialize_reaction_Graph(self,G_C,max_offspring_num):
        """
        Generate the reaction graph from the synthesis graph
        Args:
            G_C: The synthesis graph
            max_offspring_num: The maximum seeding number of one sample
        Returns:
            G: The reaction graph
        """
        # define the chemical reactoin graph from the synthesis graph
        G = nx.DiGraph()
        count = 0 
        # define the nodes for repeative experiments
        for node in list(G_C.nodes()):
            if node == 0:
                pass
            else:
                total_exp_num = G_C.nodes[node]['number'] + int(G_C.nodes[node]['UV_Vis']) + int(np.ceil(G_C.nodes[node]['offspring']/max_offspring_num))
                G.add_node(count)
                G.nodes[count]['UV_Vis'] = G_C.nodes[node]['UV_Vis']
                G.nodes[count]['exp'] = node
                G.nodes[count]['offspring'] = 0
                G.nodes[count]['exp_info'] = G_C.nodes[node]['exp_info']
                count = count + 1
                for i in range(total_exp_num-1):
                    G.add_node(count)
                    G.nodes[count]['UV_Vis'] = False
                    G.nodes[count]['exp'] = node
                    G.nodes[count]['offspring'] = 0
                    G.nodes[count]['exp_info'] = G_C.nodes[node]['exp_info']
                    count = count + 1
        # define the edges of the directed graph 
        for edge in list(G_C.edges()):
            if edge[0] == 0:
                pass
            else:
                parents = [node for node in G.nodes if G.nodes[node]['exp'] == edge[0]]
                offsprings = [node for node in G.nodes if G.nodes[node]['exp'] == edge[1]]
                if G.nodes[parents[0]]['UV_Vis'] == True:
                    start_index = 1
                else:
                    start_index = 0
                while G.nodes[parents[start_index]]['offspring'] >= max_offspring_num:
                    start_index = start_index + 1

                for offspring in offsprings:
                    G.add_edge(parents[start_index],offspring)
                    G.nodes[parents[start_index]]['offspring'] = G.nodes[parents[start_index]]['offspring'] + 1
                    if G.nodes[parents[start_index]]['offspring'] >= max_offspring_num:
                        start_index = start_index + 1
        return G   
    def initialize_hardware_Graph(self,G,wheel_number = 24):
        """
        Given a directed Graph of chemical reactions, generate the corresponding hardware graph.
        Args:
            G: the chemical reaction graph
            wheel_number: the total slot number of the wheel
        Returns:
            G_skl: the hardware graph
            G: the updated chemical reaction graph
        """
        # define the skeleton for the wheel
        G_skl = nx.DiGraph()
        G_skl.add_nodes_from(range(wheel_number))
        nx.set_node_attributes(G_skl, None, "exp") # set the default UV-Vis 

        # calculate the growth steps for individual experiments
        generation = []
        for node in list(G.nodes()):
            generation_temp = 0
            prec = [i for i in G.predecessors(node)] # got predecessors
            # keep getting predecessors until there is no predecessors, which tells the growth step required for the sample
            while len(prec) >0:
                generation_temp = generation_temp + 1
                prec = [i for i in G.predecessors(prec[0])]
            generation.append(generation_temp+1)
            G.nodes[node]["step"] = generation_temp+1
        
        # map the chemical reaction graph to the wheel graph 
        count = 0 
        exp_count = 0 
        for generation_temp in np.unique(generation):
            # define the preflush step 
            G_skl.nodes[count]["exp"] = "preflush"
            count = count + 1
            # get one batch
            batch = [node for node in G if G.nodes[node]["step"] == generation_temp]
            for exp in batch:
                G_skl.nodes[count]["exp"] = exp
                G_skl.nodes[count]["step"] = generation_temp
                G_skl.nodes[count]["UV_Vis"] = G.nodes[exp]["UV_Vis"]
                G_skl.nodes[count]['exp_info'] = G.nodes[exp]["exp_info"]
                
                pathlib.Path('./Experiment/'+f"/00%02d/"%(exp_count)).mkdir(parents=True, exist_ok=True)
                with open('./Experiment/'+f"/00%02d/"%(exp_count)+'params.json','w') as f:
                    json.dump(G.nodes[exp]["exp_info"], f,indent = 4)

                count = count +1 
                exp_count = exp_count + 1
            # define the flush step after the experiments
            G_skl.nodes[count]["exp"] = "flush"
            count = count +1 
        # define the experiment list in the skeleton graph
        exp_list = [G_skl.nodes[node]["exp"] for node in list(G_skl.nodes())]
        
        # get the connectivity of the wheel graph based on the chemical reaction graph
        for node in G_skl.nodes:
            if isinstance(G_skl.nodes[node]["exp"], int):
                prec = [i for i in G.predecessors(G_skl.nodes[node]["exp"])]
                if len(prec)>0:
                    G_skl.add_edge(exp_list.index(prec[0]), node)
        return G_skl,G
    def plot_reaction_Graph(self,G,label,color1,color2,file_path):
        """
        Plot the chemical reaction graph
        Args:
            G: the graph of the chemical reactions
            label: binary variable indicating if labelling the nodes
            color1: the color for nodes that will be characterized with UV-Vis
            colors: the color for nodes that will not be characterized with UV-Vis
            file_path: the file path to save the figure
        Returns:
            None
        """
        # plot the graphic structure in the hardware graph
        plt.figure(figsize=(5,5)) 
        # write dot file to use with graphviz
        pos = graphviz_layout(G, prog='dot')
        labeldict = {}
        color_map = []
        for node in G:
            if G.nodes[node]["UV_Vis"]:
                color_map.append(color1)
            else:
                color_map.append(color2)
            if label ==True:
                labeldict[node] = G.nodes[node]['exp']
        if label ==True:
            nx.draw(G,pos,
                    node_color=color_map,
                    labels=labeldict,
                    with_labels = True,
                    node_size=1000,
                    font_size=20, 
                    alpha=1)
        else:
            nx.draw(G,pos,
                    node_color=color_map,
                    with_labels = True,
                    node_size=1000,
                    font_size=20, 
                    alpha=1)
        plt.draw()
        plt.savefig(file_path+'.png', dpi=300)
        plt.show()

    def plot_hardware_Graph(self,G_skl,G,color1,color2,file_path):
        """
        Plot the hardware graph
        Args:
            G_skl: the hardware graph
            G: the chemical reaction graph
            color1: the color for nodes that will be characterized with UV-Vis
            colors: the color for nodes that will not be characterized with UV-Vis
            file_path: the file path to save the figure
        """
       # plot the graphic structure in the skeleton
        plt.figure(figsize=(5,5)) 
        pos = nx.circular_layout(G_skl)
        color_map = []
        for node in G_skl:
            if isinstance(G_skl.nodes[node]["exp"], int):
                if G.nodes[G_skl.nodes[node]["exp"]]["UV_Vis"] == False:
                    color_map.append(color2)
                else:
                    color_map.append(color1)
            elif isinstance(G_skl.nodes[node]["exp"],str):
                color_map.append('gray')
            else:
                color_map.append('black')

        labeldict = {}
        for node in range(24):
            if isinstance(G_skl.nodes[node]["exp"], int):
                labeldict[node] = G.nodes[G_skl.nodes[node]["exp"]]['exp']
            elif isinstance(G_skl.nodes[node]["exp"],str):
                pass
            else:
                pass 
        nx.draw(G_skl,
                pos,
                node_color=color_map,
                labels=labeldict,
                with_labels=True,
                node_size=1000,
                font_size=20,
                connectionstyle="arc3,rad=-0.3",
                arc_above=False,
                alpha=1)

        plt.draw()
        plt.savefig(file_path+'.png', dpi=300)
        plt.show()