"""
Provides spaces for the SoSSim system-of-systems simulator.
The space is a grid rendered as a bidirectional graph, with nodes being grid cells and with edges between all adjacent grid cells.
Attributes can be set on nodes and edges to represent roads, destinations, etc.
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

import mesa

# Type abbreviations for nodes and edges
Node = Tuple[int, int]
Edge = Tuple[Node, Node]

class RoadGridGraph(nx.DiGraph):
    """
    A directed graph representing a 2D grid where the edges are labelled by direction (N, S, E, W).
    Roads are represented by having the node and edge attribute "road" set to True.
    Destinations are represented by having the node attribute "destination" set to True.
    """

    def __init__(self, width: int, height: int, node_attrs: Dict[str, Any] = dict(), edge_attrs: Dict[str, Any] = dict()):
        """
        Creates the grid graph.
        Two dictionaries are provided that give optional default attributes to nodes and edges.
        
        Args:
            width (int): the width of the grid.
            height (int): the height of the grid.
            node_attrs (Dict[str, Any]): attributes and values to be added to each node. Defaults to an empty dictionary.
            edge_attrs (Dict[str, Any]): attributes and values to be added to each edge. Defaults to an empty dictionary.

        Returns:
            nx.DiGraph: the resulting graph.
        """
        # Create the graph and fill it by adding bidirectional edges going down and to the right of each node.
        super().__init__()
        for x in range(width):
            for y in range(height):
                if x != width - 1: # Do not add edge to the right if in last column
                    self.add_edge((x, y), (x + 1, y))
                    self.add_edge((x + 1, y), (x, y))
                if y != height - 1: # Do not add edge downwards if in last row
                    self.add_edge((x, y), (x, y + 1))
                    self.add_edge((x, y  + 1), (x, y))

        # Set default attribute values for nodes and edges
        for node in self.nodes:
            for (attr, value) in node_attrs.items():
                self.nodes[node]["road"] = False
                self.nodes[node]["destination"] = False
                self.nodes[node][attr] = value
        for (source, sink) in self.edges:
            self[source][sink]["road"] = False
            for (attr, value) in edge_attrs.items():
                self[source][sink][attr] = value

        # Set the direction attribute for edges
        for (source, sink) in self.edges:
            ((x1, y1), (x2, y2)) = (source, sink)
            d = (x2 - x1, y2 - y1)
            if d == (-1, 0):
                self[source][sink]["direction"] = "W"
            elif d == (1, 0):
                self[source][sink]["direction"] = "E"
            elif d == (0, -1):
                self[source][sink]["direction"] = "N"
            else: # d == (0, 1)
                self[source][sink]["direction"] = "S"

    def roads_from(self, source: Node) -> List[Node]:
        """
        Returns a list of all nodes that can be reached by road from a given source node.

        Args:
            source (Node): the source node.

        Returns:
            List[Node]: a list of nodes reachable by road.
        """
        return [sink for _, sink, has_road in self.out_edges(source, data = "road") if has_road]

    def roads_to(self, sink: Node) -> List[Node]:
        """
        Returns a list of all nodes that can reach the given sink node by road.

        Args:
            sink (Node): the sink node.

        Returns:
            List[Node]: a list of nodes from which the sink node can be reached by road.
        """
        return [source for source, _, has_road in self.in_edges(sink, data = "road") if has_road]

    def has_road_to(self, source: Node, direction: str) -> bool:
        """
        Returns True if and only if the graph has a road from the given node in the given direction.

        Args:
            source (Node): the source node.
            direction (str): the direction, which is one of "N", "S", "E", "W".

        Returns:
            bool: _description_
        """
        return any(self[source][sink]["direction"] == direction for sink in self.roads_from(source))

    def add_road(self, source: Node, sink: Node, bidirectional: bool = False):
        """
        Adds a road from the source node to the sink node.

        Args:
            source (Node): source node.
            sink (Node): sink node.
            bidirectional (bool, optional): if True, the road in opposite direction is also added. Defaults to False.
        """
        self.nodes[source]["road"] = True
        self.nodes[sink]["road"] = True
        self[source][sink]["road"] = True
        if bidirectional:
            self[sink][source]["road"] = True

    def add_roads(self, node: Node, directions: str):
        """
        Adds a sequence of roads to the network, starting in the provided node and going in the provided directions.

        Args:
            node (Node): the start node.
            directions (str): the direction, which is a string containing the characters N, E, S, W
        """
        for d in directions:
            next_node = next(n for n in self.neighbors(node) if self[node][n]["direction"] == d)
            self.add_road(node, next_node)
            node = next_node

    def add_destination2(self, node1: Node, node2: Node):
        """
        Adds a destination node, as a neighbor of the given node.
        Roads are added to and from the destination from the node.
        The destination node is indicated as such using a node attribute.
        
        Args:
            node1 (Node): the node to be connected to the destination.
            node2 (Node): the destination.
        """
        self.add_road(node1, node2, bidirectional = True)
        self.nodes[node2]["destination"] = True

    def is_road(self, node1: Node, node2: Optional[Node] = None) -> bool:
        """
        Checks if a node or an edge is a road. If two nodes are given, it checks the edge, otherwise the node.

        Args:
            node1 (Node): a node.
            node2 (Optional[Node], optional): a second node, if checking an edge. Defaults to None.

        Returns:
            bool: True if the node or edge is a road.
        """
        if node2:
            return self[node1][node2].get("road", False)
        else:
            return self.nodes[node1].get("road", False)

    def is_destination(self, node: Node) -> bool:
        """
        Checks if a node is a destination.

        Args:
            node (Node): the node.

        Returns:
            bool: True if the node is a destination.
        """
        return self.nodes[node].get("destination", False)

    def road_degree(self, node: Node) -> int:
        """
        Returns the number of outgoing roads from a node.

        Args:
            node (Node): the node.

        Returns:
            int: the number of outgoing roads.
        """
        return len(self.roads_from(node))

def subnode(node: Node, i: int, j: int) -> Node:
    """
    Returns the detailed network subnode (i, j) of a coarse network node.
    """
    return (node[0] * 4 + i, node[1] * 4 + j)

class RoadNetworkGrid(mesa.space.NetworkGrid):
    """
    A mesa space consisting of a road network which is placed on a grid.
    The road network is a networkx graph, where node names are tuples (x, y) referring to grid positions.
    Some nodes in the road networks can be destinations, where places of interest can be placed.
    """

    def __init__(self, width: int = 10, height: int = 10, road_density: float = 0.3, destination_density: float = 0.3):
        """
        Creates a grid of size (width, height), and adds a road network to it.
        
        Args:
            width (int, optional): the grid size in the x dimension. Defaults to 10.
            height (int, optional): the grid size in the y dimension. Defaults to 10.
            road_density (float, optional): the proportion of grid elements to be connected by roads. Defaults to 0.3.
        """
        # Setup parameters and superclass
        self.width = width
        self.height = height
        self.road_density = road_density
        self.destination_density = destination_density
        self.coarse_network = None
        self.road_network = None

        # Generate roads and destinations
        self.generate_roads()
        super().__init__(self.road_network)

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
        cnw = self.coarse_network = RoadGridGraph(self.width, self.height)

        # Step 1. Create a connected graph whose nodes are a subset of the grid cells.
        start_node = (self.width // 2, self.height //2)
        edge_candidates = [(start_node, neighbor) for neighbor in cnw.neighbors(start_node)]

        # The number of nodes is determined by the road_density parameter.
        remaining_nodes = self.width * self.height * self.road_density
        while remaining_nodes > 0:
            # Pick an edge to add, removing it from the candidates and adding it to the graph
            (source, sink) = random.choices(edge_candidates, weights = [self._edge_preference(e) for e in edge_candidates])[0]

            # If the sink of the new edge is new in the graph, add edges to its neighbors as new edge candidates
            if not cnw.is_road(sink):
                edge_candidates += [(sink, neighbor) for neighbor in cnw.neighbors(sink)]
            # Add the new edge (and implicitly its nodes), and remove the edge as a candidate.
            cnw.add_road(source, sink, bidirectional = True)
            remaining_nodes -= 1
            edge_candidates.remove((source, sink))

        # Step 2. Add lanes and roundabouts.
        # Create a new graph, this time directed. Each node in the coarse graph maps to 4 x 4 nodes in the new graph.
        rnw = self.road_network = RoadGridGraph(self.width * 4, self.height * 4, node_attrs = { "agent" : [] })

        # Add internal connections between coarse node in detailed graph.
        for node in cnw:
            if cnw.has_road_to(node, "E"):
                rnw.add_roads(subnode(node, 2, 2), "EEE")
            if cnw.has_road_to(node, "W"):
                rnw.add_roads(subnode(node, 1, 1), "WWW")
            if cnw.has_road_to(node, "N"):
                rnw.add_roads(subnode(node, 2, 1), "NNN")
            if cnw.has_road_to(node, "S"):
                rnw.add_roads(subnode(node, 1, 2), "SSS")

        # Add connections for roundabouts and through roads
        for node in cnw:
            if cnw.road_degree(node) == 1:
                # Dead ends need to make it possible to turn around, which requires adding three out of four edges.
                if not cnw.has_road_to(node, "E"):
                    rnw.add_roads(subnode(node, 2, 2), "N")
                if not cnw.has_road_to(node, "W"):
                    rnw.add_roads(subnode(node, 1, 1), "S")
                if not cnw.has_road_to(node, "N"):
                    rnw.add_roads(subnode(node, 2, 1), "W")
                if not cnw.has_road_to(node, "S"):
                    rnw.add_roads(subnode(node, 1, 2), "E")
            if cnw.road_degree(node) == 2:
                # # Through roads
                # Through roads
                if cnw.has_road_to(node, "N") and cnw.has_road_to(node, "W"):
                    rnw.add_roads(subnode(node, 1, 2), "EN")
                if cnw.has_road_to(node, "N") and cnw.has_road_to(node, "S"):
                    rnw.add_roads(subnode(node, 1, 1), "S")
                    rnw.add_roads(subnode(node, 2, 2), "N")
                if cnw.has_road_to(node, "N") and cnw.has_road_to(node, "E"):
                    rnw.add_roads(subnode(node, 1, 1), "SE")
                if cnw.has_road_to(node, "W") and cnw.has_road_to(node, "S"):
                    rnw.add_roads(subnode(node, 2, 2), "NW")
                if cnw.has_road_to(node, "W") and cnw.has_road_to(node, "E"):
                    rnw.add_roads(subnode(node, 2, 1), "W")
                    rnw.add_roads(subnode(node, 1, 2), "E")
                if cnw.has_road_to(node, "S") and cnw.has_road_to(node, "E"):
                    rnw.add_roads(subnode(node, 2, 1), "WS")
            if cnw.road_degree(node) > 2:
                # # Three and four way crossings require roundabouts, so all four edges are added.
                rnw.add_roads(subnode(node, 1, 1), "SENW")

        # Add one destination to all road nodes that have a free grid neighbor. 
        for node in rnw.nodes:
            if rnw.is_road(node) and not rnw.is_destination(node):
                for destination in rnw.neighbors(node): 
                    if not rnw.is_road(destination):
                        if random.random() < self.destination_density:
                            rnw.add_destination2(node, destination)
                            break

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
        nb_source_edges = cnw.road_degree(edge[0]) if edge[0] in cnw else 0
        nb_sink_edges = cnw.road_degree(edge[1]) if edge[1] in cnw else 0

        # Count distance of sink from center of world normalized with respect to the size of the world
        dist_x = edge[1][0] - self.width // 2
        dist_y = edge[1][1] - self.height // 2
        norm_dist = math.sqrt(dist_x ** 2 + dist_y ** 2) / math.sqrt((self.width // 2) ** 2 + (self.height // 2) ** 2)

        # Prefer adding edges away from the center and adding new nodes (a small epsilon is added to ensure that weights > 0)
        return 50 * norm_dist / (nb_source_edges ** 2 + nb_sink_edges + 0.00001)
        
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
        # Determine which node has priority entering to_node.

        # If from_node is a destination, all other nodes going into to_node have priority.
        if rnw.is_destination(from_node):
            return [n for n in rnw.roads_to(to_node) if n != from_node]

        # In a roundabout, a vehicle going S yields to one going W, E to S, N to E, and W to N.
        priority_rule = { "S" : "W", "E" : "S", "N" : "E", "W" : "N" }
        priority_direction = priority_rule[rnw[from_node][to_node]["direction"]]
        priority_node = next(n for n, _, d in rnw.in_edges(to_node, data = "direction") if d == priority_direction)

        # If the priority node can reach to_node, return it, otherwise return nothing.
        if rnw.is_road(priority_node, to_node) and not rnw.is_destination(priority_node):
            return [priority_node]
        else:
            return []