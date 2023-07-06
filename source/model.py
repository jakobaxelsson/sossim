import math
import random
import sys

import networkx as nx

import capabilities
import mesa

# Auxiliary functions to calculate neighbours of a coordinate in the grid.

def east_of(node): 
    return (node[0] + 1, node[1])

def west_of(node): 
    return (node[0] - 1, node[1])

def north_of(node): 
    return (node[0], node[1] - 1)

def south_of(node): 
    return (node[0], node[1] + 1)

def subnode(node, i, j):
    """
    Returns the detailed network subnode (i, j) of a coarse network node.
    """
    return (node[0] * 4 + i, node[1] * 4 + j)

def supernode(node):
    """
    Returns the coarse network node corresponding to a detailed road network node.
    """
    return (node[0] // 4, node[1] // 4)

class GridNetworkSpace:
    """
    A grid world containing a road network.
    """

    def __init__(self, x = 10, y = 10, road_density = 0.3):
        # Setup parameters
        self.size_x = x
        self.size_y = y
        self.road_density = road_density
        self.coarse_network = None
        self.road_network = None

        # Generate roads and destinations
        self.generate_roads()
        self.generate_destinations()

    def generate_roads(self):
        self.coarse_network = cnw = nx.Graph()

        # Step 1. Create a connected graph whose nodes are a subset of the grid cells.
        node = (self.size_x // 2, self.size_y //2)
        edge_candidates = [(node, neighbour) for neighbour in self.neighbours(node)]

        # The number of nodes is determined by the road_density parameter.
        while nx.number_of_nodes(cnw) < self.size_x * self.size_y * self.road_density:
            # Pick an edge to add, removing it from the candidates and adding it to the graph
            edge = random.choices(edge_candidates, weights = [self.edge_preference(e) for e in edge_candidates])[0]

            # If the sink of the new edge is new in the graph, add edges to its neighbours as new edge candidates
            node = edge[1]
            if not cnw.has_node(node):
                edge_candidates += [(node, neighbour) for neighbour in self.neighbours(node)]
            # Add the new edge (and implicitly its nodes), and remove the edge as a candidate.
            cnw.add_edge(*edge)
            edge_candidates.remove(edge)

        # Step 2. Add lanes and roundabouts.
        # Create a new graph, this time directed. Each node in the coarse graph maps to 4 x 4 nodes in the new graph.
        self.road_network = rnw = nx.DiGraph()

        for node in cnw:
            if east_of(node) in cnw[node]: # East
                path = [subnode(node, 2 + i, 2) for i in range(4)]
                nx.add_path(rnw, path, direction = "E")
            if west_of(node) in cnw[node]: # West
                path = [subnode(node, 1 - i, 1) for i in range(4)]
                nx.add_path(rnw, path, direction = "W")
            if north_of(node) in cnw[node]: # North
                path = [subnode(node, 2, 1 - i) for i in range(4)]
                nx.add_path(rnw, path, direction = "N")
            if south_of(node) in cnw[node]: # South
                path = [subnode(node, 1, 2 + i) for i in range(4)]
                nx.add_path(rnw, path, direction = "S")

        # Add connections for roundabouts and through roads
        for node in cnw:
            (x, y) = node
            if cnw.degree[node] == 1:
                # Dead ends need to make it possible to turn around, which requires adding three out of four edges.
                if east_of(node) not in cnw[node]: # No eastern neighbour
                    rnw.add_edge(subnode(node, 2, 2), subnode(node, 2, 1), direction = "N")
                if west_of(node) not in cnw[node]: # No western neighbour
                    rnw.add_edge(subnode(node, 1, 1), subnode(node, 1, 2), direction = "S")
                if north_of(node) not in cnw[node]: # No northern neighbour
                    rnw.add_edge(subnode(node, 2, 1), subnode(node, 1, 1), direction = "W")
                if south_of(node) not in cnw[node]: # No southern neighbour
                    rnw.add_edge(subnode(node, 1, 2), subnode(node, 2, 2), direction = "E")
            if cnw.degree[node] == 2:
                # Through roads
                if north_of(node) in cnw[node] and west_of(node) in cnw[node]: # Northern and western neighbours
                    rnw.add_edge(subnode(node, 1, 2), subnode(node, 2, 2), direction = "E")
                    rnw.add_edge(subnode(node, 2, 2), subnode(node, 2, 1), direction = "N")
                if north_of(node) in cnw[node] and south_of(node) in cnw[node]: # Northern and southern neighbours
                    rnw.add_edge(subnode(node, 1, 1), subnode(node, 1, 2), direction = "S")
                    rnw.add_edge(subnode(node, 2, 2), subnode(node, 2, 1), direction = "N")
                if north_of(node) in cnw[node] and east_of(node) in cnw[node]: # Northern and eastern neighbours
                    rnw.add_edge(subnode(node, 1, 1), subnode(node, 1, 2), direction = "S")
                    rnw.add_edge(subnode(node, 1, 2), subnode(node, 2, 2), direction = "E")
                if west_of(node) in cnw[node] and south_of(node) in cnw[node]: # Western and southern neighbours
                    rnw.add_edge(subnode(node, 2, 2), subnode(node, 2, 1), direction = "N")
                    rnw.add_edge(subnode(node, 2, 1), subnode(node, 1, 1), direction = "W")
                if west_of(node) in cnw[node] and east_of(node) in cnw[node]: # Western and eastern neighbours
                    rnw.add_edge(subnode(node, 2, 1), subnode(node, 1, 1), direction = "W")
                    rnw.add_edge(subnode(node, 1, 2), subnode(node, 2, 2), direction = "E")
                if south_of(node) in cnw[node] and east_of(node) in cnw[node]: # Southern and eastern neighbours
                    rnw.add_edge(subnode(node, 2, 1), subnode(node, 1, 1), direction = "W")
                    rnw.add_edge(subnode(node, 1, 1), subnode(node, 1, 2), direction = "S")
            if cnw.degree[(x, y)] > 2:
                # Three and four way crossings require roundabouts, so all four edges are added.
                rnw.add_edge(subnode(node, 1, 1), subnode(node, 1, 2), direction = "S")
                rnw.add_edge(subnode(node, 1, 2), subnode(node, 2, 2), direction = "E")
                rnw.add_edge(subnode(node, 2, 2), subnode(node, 2, 1), direction = "N")
                rnw.add_edge(subnode(node, 2, 1), subnode(node, 1, 1), direction = "W")

        # Keep track of all agents in a node
        for node in rnw.nodes:
            rnw.nodes[node]["agent"] = []

    def edge_preference(self, edge):
        # Returns a numerical value indicating how preferred this edge is (higher means more likely to be selected)
        cnw = self.coarse_network

        # Count number of existing edges for the source and sink of the selected edge
        nb_source_edges = cnw.degree[edge[0]] if edge[0] in cnw else 0
        nb_sink_edges = cnw.degree[edge[1]] if edge[1] in cnw else 0

        # Count distance of sink from center of world normalized with respect to the size of the world
        dist_x = edge[1][0] - self.size_x // 2
        dist_y = edge[1][1] - self.size_y // 2
        norm_dist = math.sqrt(dist_x ** 2 + dist_y ** 2) / math.sqrt((self.size_x // 2) ** 2 + (self.size_y // 2) ** 2)

        # Prefer adding edges away from the center and adding new nodes (a small epsilon is added to ensure that weights > 0)
        return 50 * norm_dist / (nb_source_edges ** 2 + nb_sink_edges + 0.00001)
        
    def neighbours(self, node):
        result = [east_of(node), west_of(node), south_of(node), north_of(node)]
        return [(x, y) for (x, y) in result if x >= 0 and y >= 0 and x < self.size_x and y < self.size_y ]

    def generate_destinations(self, probability = 1):
        """
        Determines which nodes in the road network should be destinations.
        Only nodes with exactly one ingoing and one outgoing edge can be a destination.
        This is to disallow destinations in crossings.
        
        Args:
            probability (int, optional): The probability that an eligible node will be selected as a destination. Defaults to 1.
        """
        # TODO: This requires some polishing.
        rnw = self.road_network
        for node in rnw.nodes:
            if rnw.in_degree(node) == 1 and rnw.out_degree(node) == 1 and random.random() < probability:
                rnw.nodes[node]["destination"] = True
            else:
                rnw.nodes[node]["destination"] = False

class Vehicle(mesa.Agent):

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        # Add a load capacity of the vehicle
        self.capacity = random.choice([1, 2, 3])

        # Randomly select a starting position which is not yet occupied by some other vehicle.
        rnw = self.model.space.road_network
        available_positions = [p for p in rnw.nodes if not rnw.nodes[p]["agent"]]
        self.pos = random.choice(available_positions)
        rnw.nodes[self.pos]["agent"].append(self)
        self.new_pos = self.pos

        # Set the initial heading of the vehicle.
        self.heading = rnw[self.pos][next(rnw.neighbors(self.pos))]["direction"]

        # Add a view
        if self.model.view:
            self.view = self.model.view.create_agent_view(self)

        # Add a plan, which is a list of capability instances.
        self.plan = []

    def step(self):
        if not self.plan:
            new_pos = (x, y) = random.choice(list(self.model.space.road_network.neighbors(self.pos)))
            self.plan = [capabilities.MoveCapability(self, new_pos)]

    def advance(self):
        # Move the vehicle on the grid
        capability = self.plan[0]
        if capability.precondition():
            capability.activate()
        if capability.postcondition():
            self.plan = self.plan[1:]

        # Update the position in the drawing
        if self.model.view:
            self.view.update(self)

class TransportSystem(mesa.Model):
    def __init__(self):
        # TODO: Initialize from a configuration object, to make it easier to edit, load, and save it.
        self.view = None
        self.num_agents = 0
        self.width = 0
        self.height = 0
        self.random_seed = random.randrange(sys.maxsize)

    def add_view(self, view):
        self.view = view

    def generate(self, N = 10, width = 10, height = 10, random_seed = None):
        self.num_agents = N
        self.width = width
        self.height = height
        self.random_seed = random_seed or random.randrange(sys.maxsize)
        random.seed(self.random_seed)
        self.schedule = mesa.time.SimultaneousActivation(self)

        self.space = GridNetworkSpace(self.width, self.height)
        if self.view:
            self.view.update(self)
        # Create agents
        for i in range(self.num_agents):
            a = Vehicle(i, self)
            self.schedule.add(a)

    def step(self):
        self.schedule.step()
        if self.view:
            self.view.update_time(self.schedule.time)