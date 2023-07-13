"""
Provides spaces for the SoSSim system-of-systems simulator.
"""

import math
import random
from typing import List, Tuple

import networkx as nx

import mesa

# Type abbreviations for nodes and edges
Node = Tuple[int, int]
Edge = Tuple[Node, Node]

# Auxiliary functions to calculate neighbours of a coordinate in the grid.

directions = {"N" : (0, -1), "E" : (1, 0), "S" : (0, 1), "W" : (-1, 0)}
opposite_directions = {"N" : "S", "S" : "N", "W" : "E", "E" : "W"}

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

class RoadNetworkGrid(mesa.space.NetworkGrid):
    """
    A mesa space consisting of a road network which is placed on a grid.
    The road network is a networkx graph, where node names are tuples (x, y) referring to grid positions.
    Some nodes in the road networks can be destinations, where places of interest can be placed.
    """

    def __init__(self, size_x: int = 10, size_y: int = 10, road_density: float = 0.3, destination_density: float = 0.3):
        """
        Creates a grid of size (size_x, size_y), and adds a road network to it.
        
        Args:
            size_x (int, optional): the grid size in the x dimension. Defaults to 10.
            size_y (int, optional): the grid size in the y dimension. Defaults to 10.
            road_density (float, optional): the proportion of grid elements to be connected by roads. Defaults to 0.3.
        """
        # Setup parameters and superclass
        self.size_x = size_x
        self.size_y = size_y
        self.road_density = road_density
        self.destination_density = destination_density
        self.coarse_network = nx.Graph()
        self.road_network = nx.DiGraph()
        super().__init__(self.road_network)

        # Generate roads and destinations
        self.generate_roads()

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
            # TODO: In each if statement, the first add destination is problematic.
            if node_to(node, "E") in cnw[node]: # East
                self.add_edges(subnode(node, 2, 2), "EEE")
                self.add_destination(subnode(node, 3, 2), "S")
            if node_to(node, "W") in cnw[node]: # West
                self.add_edges(subnode(node, 1, 1), "WWW")
                self.add_destination(subnode(node, 0, 1), "N")
            if node_to(node, "N") in cnw[node]: # North
                self.add_edges(subnode(node, 2, 1), "NNN")
                self.add_destination(subnode(node, 2, 0), "E")
            if node_to(node, "S") in cnw[node]: # South
                self.add_edges(subnode(node, 1, 2), "SSS")
                self.add_destination(subnode(node, 1, 3), "W")

        # Add connections for roundabouts and through roads
        for node in cnw:
            (x, y) = node
            if cnw.degree[node] == 1:
                # Dead ends need to make it possible to turn around, which requires adding three out of four edges.
                if node_to(node, "E") not in cnw[node]: # No eastern neighbour
                    self.add_edges(subnode(node, 2, 2), "N")
                    self.add_destination(subnode(node, 2, 1), "E")
                if node_to(node, "W") not in cnw[node]: # No western neighbour
                    self.add_edges(subnode(node, 1, 1), "S")
                    self.add_destination(subnode(node, 1, 2), "W")
                if node_to(node, "N") not in cnw[node]: # No northern neighbour
                    self.add_edges(subnode(node, 2, 1), "W")
                    self.add_destination(subnode(node, 1, 1), "N")
                if node_to(node, "S") not in cnw[node]: # No southern neighbour
                    self.add_edges(subnode(node, 1, 2), "E")
                    self.add_destination(subnode(node, 2, 2), "S")
                # Add further destinations on the incoming edge
                if node_to(node, "E") in cnw[node]: # Eastern neighbour
                    self.add_destination(subnode(node, 3, 1), "N")
                    self.add_destination(subnode(node, 2, 1), "N")
                if node_to(node, "W") in cnw[node]: # Western neighbour
                    self.add_destination(subnode(node, 0, 2), "S")
                    self.add_destination(subnode(node, 1, 2), "S")
                if node_to(node, "N") in cnw[node]: # Northern neighbour
                    self.add_destination(subnode(node, 1, 0), "W")
                    self.add_destination(subnode(node, 1, 1), "W")
                if node_to(node, "S") in cnw[node]: # Southern neighbour
                    self.add_destination(subnode(node, 2, 3), "E")
                    self.add_destination(subnode(node, 2, 2), "E")
            if cnw.degree[node] == 2:
                # Through roads
                if node_to(node, "N") in cnw[node] and node_to(node, "W") in cnw[node]: # Northern and western neighbours
                    self.add_edges(subnode(node, 1, 2), "EN")
                    self.add_destination(subnode(node, 0, 2), "S")
                    self.add_destination(subnode(node, 1, 2), "S")
                    self.add_destination(subnode(node, 2, 2), "S")
                    self.add_destination(subnode(node, 2, 1), "E")
                if node_to(node, "N") in cnw[node] and node_to(node, "S") in cnw[node]: # Northern and southern neighbours
                    self.add_edges(subnode(node, 1, 1), "S")
                    self.add_edges(subnode(node, 2, 2), "N")
                    self.add_destination(subnode(node, 1, 0), "W")
                    self.add_destination(subnode(node, 1, 1), "W")
                    self.add_destination(subnode(node, 1, 2), "W")
                    self.add_destination(subnode(node, 2, 3), "E")
                    self.add_destination(subnode(node, 2, 2), "E")
                    self.add_destination(subnode(node, 2, 1), "E")
                if node_to(node, "N") in cnw[node] and node_to(node, "E") in cnw[node]: # Northern and eastern neighbours
                    self.add_edges(subnode(node, 1, 1), "SE")
                    self.add_destination(subnode(node, 1, 0), "W")
                    self.add_destination(subnode(node, 1, 1), "W")
                    self.add_destination(subnode(node, 1, 2), "W")
                    self.add_destination(subnode(node, 2, 2), "S")
                if node_to(node, "W") in cnw[node] and node_to(node, "S") in cnw[node]: # Western and southern neighbours
                    self.add_edges(subnode(node, 2, 2), "NW")
                    self.add_destination(subnode(node, 2, 3), "E")
                    self.add_destination(subnode(node, 2, 2), "E")
                    self.add_destination(subnode(node, 2, 1), "E")
                    self.add_destination(subnode(node, 1, 1), "N")
                if node_to(node, "W") in cnw[node] and node_to(node, "E") in cnw[node]: # Western and eastern neighbours
                    self.add_edges(subnode(node, 2, 1), "W")
                    self.add_edges(subnode(node, 1, 2), "E")
                    self.add_destination(subnode(node, 3, 1), "N")
                    self.add_destination(subnode(node, 2, 1), "N")
                    self.add_destination(subnode(node, 1, 1), "N")
                    self.add_destination(subnode(node, 0, 2), "S")
                    self.add_destination(subnode(node, 1, 2), "S")
                    self.add_destination(subnode(node, 2, 2), "S")
                if node_to(node, "S") in cnw[node] and node_to(node, "E") in cnw[node]: # Southern and eastern neighbours
                    self.add_edges(subnode(node, 2, 1), "WS")
                    self.add_destination(subnode(node, 3, 1), "N")
                    self.add_destination(subnode(node, 2, 1), "N")
                    self.add_destination(subnode(node, 1, 1), "N")
                    self.add_destination(subnode(node, 1, 2), "W")
            if cnw.degree[(x, y)] > 2:
                # Three and four way crossings require roundabouts, so all four edges are added.
                self.add_edges(subnode(node, 1, 1), "SENW")
                # For three way crossings, it is possible to have two additional destinations.
                if node_to(node, "E") not in cnw[node]: # No eastern neighbour
                    self.add_destination(subnode(node, 2, 3), "E")
                    self.add_destination(subnode(node, 2, 2), "E")
                    self.add_destination(subnode(node, 2, 1), "E")
                if node_to(node, "W") not in cnw[node]: # No western neighbour
                    self.add_destination(subnode(node, 1, 0), "W")
                    self.add_destination(subnode(node, 1, 1), "W")
                    self.add_destination(subnode(node, 1, 2), "W")
                if node_to(node, "N") not in cnw[node]: # No northern neighbour
                    self.add_destination(subnode(node, 3, 1), "N")
                    self.add_destination(subnode(node, 2, 1), "N")
                    self.add_destination(subnode(node, 1, 1), "N")
                if node_to(node, "S") not in cnw[node]: # No southern neighbour
                    self.add_destination(subnode(node, 0, 2), "S")
                    self.add_destination(subnode(node, 1, 2), "S")
                    self.add_destination(subnode(node, 2, 2), "S")

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
            rnw.nodes[node]["destination"] = False
            node = next_node

    def add_destination(self, node: Node, direction: str):
        """
        Adds a destination node, as a neighbor of the given node in the indicated direction.
        Edges are added to and from the destination from the node.
        The destination node is indicated as such using a node attribute.
        The probability of a destination being added is controlled by the configuration parameter destination_density.
        
        Args:
            node (Node): the node to be connected to the destination.
            direction (str): the direction from the given node to the destination.
        """
        if random.random() < self.destination_density:
            rnw = self.road_network
            destination = node_to(node, direction)
            rnw.add_edge(node, destination, direction = direction)
            rnw.add_edge(destination, node, direction = opposite_directions[direction])
            rnw.nodes[destination]["destination"] = True

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

    def priority_nodes(self, from_node: Node, to_node: Node) -> List[Node]:
        """
        Returns the nodes from which traffic has priority over from_node when going into to_node.
        This is traffic coming from the left in a roundabout, and any traffic when leaving a parking.

        Args:
            from_node (Node): the node to be checked for priority.
            to_node (Node): the node to be checked for priority.

        Returns:
            List[Node]: a list of nodes from which vehicles have priority.
        """
        rnw = self.road_network
        # In a roundabout, W has priority over S, S over E, E over N and N over W.
        priority_rule = { "W" : "S", "S" : "E", "E" : "N", "N" : "W" }

        # Determine which node has priority entering to_node.
        priority_direction = priority_rule[direction(from_node, to_node)]
        priority_node = node_to(to_node, priority_direction)

        # If from_node is a destination, all other nodes going into to_node have priority.
        if rnw.nodes[from_node]["destination"]:
            return [n for (n, _) in rnw.in_edges(to_node) if n != from_node]

        # If the priority node can reach to_node, return it, otherwise return nothing.
        if rnw.has_edge(priority_node, to_node):
            return [priority_node]
        else:
            return []