"""
Provides models, agents, and spaces for the SoSSim system-of-systems simulator.
"""

import math
import random
import sys
from typing import Any, List, Tuple

import networkx as nx

import capabilities
import mesa

# Type abbreviations for nodes and edges
Node = Tuple[int, int]
Edge = Tuple[Node, Node]

# Auxiliary functions to calculate neighbours of a coordinate in the grid.

directions = {"N" : (0, -1), "E" : (1, 0), "S" : (0, 1), "W" : (-1, 0)}

def node_to(node: Node, direction: str) -> Node:
    """
    Returns the node neighbouring the given node in the given direction

    Args:
        node (Node): the starting node.
        direction (str): the direction, which is "N", "E", "S", "W".

    Returns:
        Node: the neighbouring node.
    """
    (dx, dy) = directions[direction]
    return (node[0] + dx, node[1] + dy)

def direction(from_node: Node, to_node: Node) -> str:
    """
    Returns the direction from one node to an adjacent node.

    Args:
        from_node (Node): the source node.
        to_node (Node): the sink node.

    Returns:
        str: direction as one of the strings "N", "E", "S", "W"
    """
    inverse_directions = { value : key for (key, value) in directions.items() }
    (dx, dy) = (to_node[0] - from_node[0], to_node[1] -  from_node[1])
    return inverse_directions[(dx, dy)]    

def subnode(node: Node, i: int, j: int) -> Node:
    """
    Returns the detailed network subnode (i, j) of a coarse network node.
    """
    return (node[0] * 4 + i, node[1] * 4 + j)

def supernode(node: Node) -> Node:
    """
    Returns the coarse network node corresponding to a detailed road network node.
    """
    return (node[0] // 4, node[1] // 4)

class GridNetworkSpace:
    """
    A mesa space consisting of a road network which is placed on a grid.
    The road network is a networkx graph, where node names are tuples (x, y) referring to grid positions.
    Some nodes in the road networks can be destinations, where places of interest can be placed.
    """

    def __init__(self, x: int = 10, y: int = 10, road_density: float = 0.3):
        """
        Creates a grid of size (x, y), and adds a road network to it.
        
        Args:
            x (int, optional): the grid size in the x dimension. Defaults to 10.
            y (int, optional): the grid size in the y dimension. Defaults to 10.
            road_density (float, optional): the proportion of grid elements to be connected by roads. Defaults to 0.3.
        """
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
        """
        Generates the road network. This is a two step process.
        First, a coarse undirected network is generated, where each node corresponds to a grid cell.
        Heustistics are used to try to spread this network over the grid and have a balance between dense and sprawling roads.
        Second, this network is expanded into a directed graph, containing separate roadways and roundabouts.
        This is achieved by dividing each coarse network node / grid cell into 4 x 4 subnodes.
        These are connected so that traffic in all directions become possible.
        In the resulting directed network, each node has either one or two outgoing edges.
        The network keeps track of what agents are currently in a node.
        """
        cnw = self.coarse_network = nx.Graph()

        # Step 1. Create a connected graph whose nodes are a subset of the grid cells.
        node = (self.size_x // 2, self.size_y //2)
        edge_candidates = [(node, neighbour) for neighbour in self.grid_neighbours(node)]

        # The number of nodes is determined by the road_density parameter.
        while nx.number_of_nodes(cnw) < self.size_x * self.size_y * self.road_density:
            # Pick an edge to add, removing it from the candidates and adding it to the graph
            edge = random.choices(edge_candidates, weights = [self._edge_preference(e) for e in edge_candidates])[0]

            # If the sink of the new edge is new in the graph, add edges to its neighbours as new edge candidates
            node = edge[1]
            if not cnw.has_node(node):
                edge_candidates += [(node, neighbour) for neighbour in self.grid_neighbours(node)]
            # Add the new edge (and implicitly its nodes), and remove the edge as a candidate.
            cnw.add_edge(*edge)
            edge_candidates.remove(edge)

        # Step 2. Add lanes and roundabouts.
        # Create a new graph, this time directed. Each node in the coarse graph maps to 4 x 4 nodes in the new graph.
        rnw = self.road_network = nx.DiGraph()

        # Add internal connections between coarse node in detailed graph.
        for node in cnw:
            if node_to(node, "E") in cnw[node]: # East
                self.add_edges(subnode(node, 2, 2), "EEE")
            if node_to(node, "W") in cnw[node]: # West
                self.add_edges(subnode(node, 1, 1), "WWW")
            if node_to(node, "N") in cnw[node]: # North
                self.add_edges(subnode(node, 2, 1), "NNN")
            if node_to(node, "S") in cnw[node]: # South
                self.add_edges(subnode(node, 1, 2), "SSS")

        # Add connections for roundabouts and through roads
        for node in cnw:
            (x, y) = node
            if cnw.degree[node] == 1:
                # Dead ends need to make it possible to turn around, which requires adding three out of four edges.
                if node_to(node, "E") not in cnw[node]: # No eastern neighbour
                    self.add_edges(subnode(node, 2, 2), "N")
                if node_to(node, "W") not in cnw[node]: # No western neighbour
                    self.add_edges(subnode(node, 1, 1), "S")
                if node_to(node, "N") not in cnw[node]: # No northern neighbour
                    self.add_edges(subnode(node, 2, 1), "W")
                if node_to(node, "S") not in cnw[node]: # No southern neighbour
                    self.add_edges(subnode(node, 1, 2), "E")
            if cnw.degree[node] == 2:
                # Through roads
                if node_to(node, "N") in cnw[node] and node_to(node, "W") in cnw[node]: # Northern and western neighbours
                    self.add_edges(subnode(node, 1, 2), "EN")
                if node_to(node, "N") in cnw[node] and node_to(node, "S") in cnw[node]: # Northern and southern neighbours
                    self.add_edges(subnode(node, 1, 1), "S")
                    self.add_edges(subnode(node, 2, 2), "N")
                if node_to(node, "N") in cnw[node] and node_to(node, "E") in cnw[node]: # Northern and eastern neighbours
                    self.add_edges(subnode(node, 1, 1), "SE")
                if node_to(node, "W") in cnw[node] and node_to(node, "S") in cnw[node]: # Western and southern neighbours
                    self.add_edges(subnode(node, 2, 2), "NW")
                if node_to(node, "W") in cnw[node] and node_to(node, "E") in cnw[node]: # Western and eastern neighbours
                    self.add_edges(subnode(node, 2, 1), "W")
                    self.add_edges(subnode(node, 1, 2), "E")
                if node_to(node, "S") in cnw[node] and node_to(node, "E") in cnw[node]: # Southern and eastern neighbours
                    self.add_edges(subnode(node, 2, 1), "WS")
            if cnw.degree[(x, y)] > 2:
                # Three and four way crossings require roundabouts, so all four edges are added.
                self.add_edges(subnode(node, 1, 1), "SENW")

        # Keep track of all agents in a node
        for node in rnw.nodes:
            rnw.nodes[node]["agent"] = []

    def add_edges(self, node: Node, directions: str):
        """
        Adds a sequence of edges to the road network, starting in the provided node and going in the provided directions.

        Args:
            node (Node): the start node.
            directions (str): the direction, which is a string containing the characters N, E, S, W
        """
        rnw = self.road_network
        for d in directions:
            next_node = node_to(node, d)
            rnw.add_edge(node, next_node, direction = d)
            node = next_node

    def _edge_preference(self, edge: Edge) -> float:
        """
        Provides a heuristic for adding edges to the coarse network during generation.
        It assigns a random preference to the provided edge depending on where it is on the grid and the connecting nodes previous edges.

        Args:
            edge (Edge): the edge.

        Returns:
            float: a number indicating how preferred this edge is.
        """
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
        
    def grid_neighbours(self, node: Node) -> List[Node]:
        """
        Returns the grid neighbours of a node, taking coarse network grid boundaries into accound.
        Diagonal neighbours are not considered.

        Args:
            node (Node): the node.

        Returns:
            List[Node]: the neighbours.
        """
        return [(x, y) for (x, y) in [node_to(node, d) for d in "EWSN"] 
                if x >= 0 and y >= 0 and x < self.size_x and y < self.size_y]

    def generate_destinations(self, probability: float = 1.0):
        """
        Determines which nodes in the road network should be destinations.
        Only nodes with exactly one ingoing and one outgoing edge can be a destination.
        This is to disallow destinations in crossings.
        
        Args:
            probability (float, optional): The probability that an eligible node will be selected as a destination. Defaults to 1.
        """
        # TODO: This requires some polishing.
        rnw = self.road_network
        for node in rnw.nodes:
            if rnw.in_degree(node) == 1 and rnw.out_degree(node) == 1 and random.random() < probability:
                rnw.nodes[node]["destination"] = True
            else:
                rnw.nodes[node]["destination"] = False

    def priority_nodes(self, from_node: Node, to_node: Node) -> List[Node]:
        """
        Returns the nodes from which traffic has priority over from_node when going into to_node.

        Args:
            from_node (Node): the node to be checked for priority.
            to_node (Node): the node to be checked for priority.

        Returns:
            List[Node]: a list of nodes from which vehicles have priority.
        """
        # In a roundabout, W has priority over S, S over E, E over N and N over W.
        priority_rule = { "W" : "S", "S" : "E", "E" : "N", "N" : "W" }

        # Determine which node has priority entering to_node.
        priority_direction = priority_rule[direction(from_node, to_node)]
        priority_node = node_to(to_node, priority_direction)

        # If the priority node can reach to_node, return it, otherwise return nothing.
        if self.road_network.has_edge(priority_node, to_node):
            return [priority_node]
        else:
            return []

class Vehicle(mesa.Agent):

    def __init__(self, unique_id: int, model: mesa.Model):
        """
        Creates a vehicle agent in a simulation model.

        Args:
            unique_id (int): the unique id of the agent.
            model (mesa.Model): the model in which the agent is situated.
        """
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

    def create_plan(self):
        """
        The vehicle creates a plan, which consists of randomly moving to one the neighbours in the road network.
        """
        rnw = self.model.space.road_network
        new_pos = random.choice(list(rnw.neighbors(self.pos)))
        self.plan = [capabilities.MoveCapability(self, new_pos)]

    def step(self):
        """
        The first part of a simulation round when using the Mesa simultaneous activation scheduler.
        If the agent does not have a plan, it creates one.
        Then it checks that the preconditions of the first action in the plan are fulfilled.
        """
        if not self.plan:
            self.create_plan()
        action = self.plan[0]
        self.ready_to_advance = action.precondition()

    def advance(self):
        """
        The second part of a simulation round when using the Mesa simultaneous activation scheduler.
        If the precondition of the first action in the current plan was fullfilled, that action is now carried out.
        If this leads to the action's postcondition being fulfilled, the action is removed from the plan.
        Finally, if the agent has a view, that view is updated.
        """
        action = self.plan[0]
        if self.ready_to_advance:
            action.activate()
        if action.postcondition():
            self.plan = self.plan[1:]

        # Update the position in the drawing
        if self.model.view:
            self.view.update(self)

class TransportSystem(mesa.Model):
    def __init__(self):
        """
        Creates a transport system model.
        Note that it is empty initially, and needs to be generated using the generate method.
        """
        # TODO: Initialize from a configuration object, to make it easier to edit, load, and save it.
        # TODO: Mesa has its own random seed handling, see source code of Mesa.model. 
        self.view = None
        self.num_agents = 0
        self.width = 0
        self.height = 0
        self.random_seed = random.randrange(sys.maxsize)

    def add_view(self, view: Any):
        """
        Adds a view to the model.

        Args:
            view (Any): the view to be added.
        """
        self.view = view

    def generate(self, N: int = 10, width: int = 10, height: int = 10, random_seed: int | None = None):
        """
        Generates the model, including creating its space and agents.

        Args:
            N (int, optional): number of agents. Defaults to 10.
            width (int, optional): width of the coarse grid space. Defaults to 10.
            height (int, optional): height of the coarse grid space. Defaults to 10.
            random_seed (int | None, optional): a random seed. Defaults to None, in which case a seed is generated.
        """
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
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        if self.view:
            self.view.update_time(self.schedule.time)