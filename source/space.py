"""
Provides spaces for the SoSSim system-of-systems simulator.
The space is a grid rendered as a bidirectional graph, with nodes being grid cells and with edges between all adjacent grid cells.
Attributes can be set on nodes and edges to represent roads, destinations, etc.
"""
import itertools
import math
from typing import Annotated, Any, Callable, Iterator, NewType, Optional

import networkx as nx

from configuration import Configuration, configurable
import core

# Type abbreviations for nodes, edges and directions.
Node = NewType("Node", tuple[int, int])
Edge = NewType("Edge", tuple[Node, Node])
Direction = int

class RoadGridGraph(nx.DiGraph):
    """
    A directed graph representing a 2D grid where the edges are labelled by direction in degrees.
    Roads are represented by having the node and edge attribute "road" set to True.
    Destinations are represented by having the node attribute "destination" set to True.
    Some destinations can also have charging points.
    """

    def __init__(self, width: int, height: int, node_attrs: dict[str, Any] = dict(), edge_attrs: dict[str, Any] = dict()):
        """
        Creates the grid graph.
        Two dictionaries are provided that give optional default attributes to nodes and edges.
        
        Args:
            width (int): the width of the grid.
            height (int): the height of the grid.
            node_attrs (dict[str, Any]): attributes and values to be added to each node. Defaults to an empty dictionary.
            edge_attrs (dict[str, Any]): attributes and values to be added to each edge. Defaults to an empty dictionary.

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
            self.nodes[node]["road"] = False
            self.nodes[node]["destination"] = False
            self.nodes[node]["charging_point"] = False
            self.nodes[node]["agent"] = []
            for (attr, value) in node_attrs.items():
                self.nodes[node][attr] = value
        for (source, sink) in self.edges:
            self[source][sink]["road"] = False
            for (attr, value) in edge_attrs.items():
                self[source][sink][attr] = value

        # Set the direction attribute for edges
        for (source, sink) in self.edges:
            ((x1, y1), (x2, y2)) = (source, sink)
            self[source][sink]["direction"] = int(math.degrees(math.atan2(y2 - y1, x2 - x1))) + 90

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

    def add_roads(self, node: Node, directions: list[Direction]):
        """
        Adds a sequence of roads to the network, starting in the provided node and going in the provided directions.

        Args:
            node (Node): the start node.
            directions (list[Direction]): a list containing directions in degrees.
        """
        for d in directions:
            next_node = next(n for n in self.neighbors(node) if self[node][n]["direction"] == d)
            self.add_road(node, next_node)
            node = next_node

    def add_destination(self, node1: Node, node2: Node, charging_point: bool = False):
        """
        Adds a destination node, as a neighbor of the given node.
        Roads are added to and from the destination from the node.
        The destination node is indicated as such using a node attribute.
        
        Args:
            node1 (Node): the node to be connected to the destination.
            node2 (Node): the destination.
            charging_point (bool, optional): if True, the destination is a charging point. Defaults to False.
        """
        self.add_road(node1, node2, bidirectional = True)
        self.nodes[node2]["destination"] = True
        if charging_point:
            self.nodes[node2]["charging_point"] = True

    def has_road_to(self, source: Node, direction: Direction) -> bool:
        """
        Returns True if and only if the graph has a road from the given node in the given direction.

        Args:
            source (Node): the source node.
            direction (Direction): the direction in degrees.

        Returns:
            bool: _description_
        """
        roads_from = [sink for _, sink, has_road in self.out_edges(source, data = "road") if has_road]
        return any(self[source][sink]["direction"] == direction for sink in roads_from)

    def is_road(self, node1: Node, node2: Optional[Node] = None) -> bool:
        """
        Checks if a node or an edge is a road. If two nodes are given, it checks the edge, otherwise the node.

        Args:
            node1 (Node): a node.
            node2 (Node, optional): a second node, if checking an edge. Defaults to None.

        Returns:
            bool: True if the node or edge is a road.
        """
        if node2:
            return self[node1][node2].get("road", False)
        else:
            return self.nodes[node1].get("road", False)

    def road_degree(self, node: Node) -> int:
        """
        Returns the number of outgoing roads from a node.

        Args:
            node (Node): the node.

        Returns:
            int: the number of outgoing roads.
        """
        return len([sink for _, sink, has_road in self.out_edges(node, data = "road") if has_road])

def subnode(node: Node, i: int, j: int) -> Node:
    """
    Returns the detailed network subnode (i, j) of a coarse network node.
    """
    return Node((node[0] * 4 + i, node[1] * 4 + j))

@configurable
class RoadNetworkGrid(core.Space):
    """
    An agent space consisting of a road network which is placed on a grid.
    The road network is a networkx graph, where node names are tuples (x, y) referring to grid positions.
    Some nodes in the road networks can be destinations, where places of interest can be placed.
    """
    width:                  Annotated[int,   "Param", "number of grid cells in x dimension"]   = 10  
    height:                 Annotated[int,   "Param", "number of grid cells in y dimension"]   = 10   
    road_density:           Annotated[float, "Param", "the proportion of the grid to be covered by roads"] = 0.3
    destination_density:    Annotated[float, "Param", "probability of generating a destination in a position where it is possible"] = 0.3 
    charging_point_density: Annotated[float, "Param", "probability of a destination having a charging point"] = 0.3

    def __init__(self, configuration: Configuration, model: core.Model):
        """
        Creates a grid of size (width, height), and adds a road network to it.
        
        Args:
            configuration (Configuration): the configuration of parameters from which the road network is generated.
            model (core.Model): the model of which this space is to be a part.
        """
        # Setup parameters and superclass
        super().__init__()
        configuration.initialize(self)
        self.model = model
        self.coarse_network = RoadGridGraph(self.width, self.height)
        self.road_network = RoadGridGraph(self.width * 4, self.height * 4)

        # Generate roads and destinations
        self.generate_roads()
        # import cProfile, pstats
        # with cProfile.Profile() as pr:
        #     self.generate_roads()
        #     stats = pstats.Stats(pr)
        #     stats.strip_dirs()
        #     stats.sort_stats("cumtime")
        #     stats.print_stats()

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
        edge_candidates = { (start_node, neighbor) : self._edge_preference((start_node, neighbor)) for neighbor in cnw.neighbors(start_node) }

        # The number of nodes is determined by the road_density parameter.
        remaining_nodes = self.width * self.height * self.road_density
        while remaining_nodes > 0:
            # Pick an edge to add, removing it from the candidates and adding it to the graph
            (source, sink) = self.model.random.choices(list(edge_candidates.keys()), weights = [w for _, w in edge_candidates.items()])[0]

            # If the sink of the new edge is new in the graph, add edges to its neighbors as new edge candidates
            if not cnw.is_road(sink):
                new_edge_candidates = { (sink, neighbor) : self._edge_preference((sink, neighbor)) for neighbor in cnw.neighbors(sink) }
                edge_candidates.update(new_edge_candidates)

            # Add the new edge (and implicitly its nodes), and remove the edge as a candidate.
            cnw.add_road(source, sink, bidirectional = True)
            remaining_nodes -= 1
            del edge_candidates[(source, sink)]

            # Update the edge preferences for all connections to neighbours of source and sink
            for node in [source, sink]:
                for neighbor in cnw.neighbors(node):
                    edge_candidates[(node, neighbor)] = self._edge_preference((node, neighbor))

        # Step 2. Add lanes and roundabouts.
        # Create a new graph, this time directed. Each node in the coarse graph maps to 4 x 4 nodes in the new graph.
        rnw = self.road_network = RoadGridGraph(self.width * 4, self.height * 4)

        # Main directions as letters to improve readability.
        N, E, S, W = [0, 90, 180, 270]

        # Add internal connections between coarse node in detailed graph.
        for node in cnw:
            if cnw.has_road_to(node, E):
                rnw.add_roads(subnode(node, 2, 2), [E] * 3)
            if cnw.has_road_to(node, W):
                rnw.add_roads(subnode(node, 1, 1), [W] * 3)
            if cnw.has_road_to(node, N):
                rnw.add_roads(subnode(node, 2, 1), [N] * 3)
            if cnw.has_road_to(node, S):
                rnw.add_roads(subnode(node, 1, 2), [S] * 3)

        # Add connections for roundabouts and through roads
        for node in cnw:
            if cnw.road_degree(node) == 1:
                # Dead ends need to make it possible to turn around, which requires adding three out of four edges.
                if not cnw.has_road_to(node, E):
                    rnw.add_roads(subnode(node, 2, 2), [N])
                if not cnw.has_road_to(node, W):
                    rnw.add_roads(subnode(node, 1, 1), [S])
                if not cnw.has_road_to(node, N):
                    rnw.add_roads(subnode(node, 2, 1), [W])
                if not cnw.has_road_to(node, S):
                    rnw.add_roads(subnode(node, 1, 2), [E])
            if cnw.road_degree(node) == 2:
                # Through roads
                if cnw.has_road_to(node, N) and cnw.has_road_to(node, W):
                    rnw.add_roads(subnode(node, 1, 2), [E, N])
                if cnw.has_road_to(node, N) and cnw.has_road_to(node, S):
                    rnw.add_roads(subnode(node, 1, 1), [S])
                    rnw.add_roads(subnode(node, 2, 2), [N])
                if cnw.has_road_to(node, N) and cnw.has_road_to(node, E):
                    rnw.add_roads(subnode(node, 1, 1), [S, E])
                if cnw.has_road_to(node, W) and cnw.has_road_to(node, S):
                    rnw.add_roads(subnode(node, 2, 2), [N, W])
                if cnw.has_road_to(node, W) and cnw.has_road_to(node, E):
                    rnw.add_roads(subnode(node, 2, 1), [W])
                    rnw.add_roads(subnode(node, 1, 2), [E])
                if cnw.has_road_to(node, S) and cnw.has_road_to(node, E):
                    rnw.add_roads(subnode(node, 2, 1), [W, S])
            if cnw.road_degree(node) > 2:
                # # Three and four way crossings require roundabouts, so all four edges are added.
                rnw.add_roads(subnode(node, 1, 1), [S, E, N, W])

        # Add one destination to all road nodes that have a free grid neighbor. 
        for node in rnw.nodes:
            if rnw.is_road(node) and not self.is_destination(node):
                for destination in rnw.neighbors(node): 
                    if not rnw.is_road(destination):
                        if self.model.random.random() < self.destination_density:
                            charging_point = self.model.random.random() < self.charging_point_density
                            rnw.add_destination(node, destination, charging_point = charging_point)
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
        
    def priority_nodes(self, from_node: Node, to_node: Node) -> list[Node]:
        """
        Returns the nodes from which traffic has priority over from_node when going into to_node.
        This is traffic coming from the left in a roundabout, and any traffic when leaving a parking.

        Args:
            from_node (Node): the node to be checked for priority.
            to_node (Node): the node to be checked for priority.

        Returns:
            list[Node]: a list of nodes from which vehicles have priority.
        """
        rnw = self.road_network
        # Determine which node has priority entering to_node.

        # If from_node is a destination, all other nodes going into to_node have priority.
        if self.is_destination(from_node):
            return self.roads_to(to_node, lambda node: node != from_node)

        # In a roundabout, a vehicle going S yields to one going W, E to S, N to E, and W to N.
        priority_rule = { 180 : 270, 90 : 180, 0 : 90, 270 : 0 }
        priority_direction = priority_rule[rnw[from_node][to_node]["direction"]]
        priority_node = next(n for n, _, d in rnw.in_edges(to_node, data = "direction") if d == priority_direction)

        # If the priority node can reach to_node, return it, otherwise return nothing.
        if self.is_road(priority_node, to_node) and not self.is_destination(priority_node):
            return [priority_node]
        else:
            return []

    def road_nodes(self, condition: Callable[[Node], bool] = lambda _: True) -> list[Node]:
        """
        Returns a list of all nodes which are connected by roads.

        Args:
            condition: a condition that the nodes must satisfy. Defaults to always True.

        Returns:
            list[Node]: the nodes connected by roads.
        """
        return [n for n in self.road_network.nodes if self.road_network.is_road(n) and condition(n)]

    def destination_nodes(self, condition: Callable[[Node], bool] = lambda _: True) -> list[Node]:
        """
        Returns a list of all nodes which are destinations.

        Args:
            condition: a condition that the nodes must satisfy. Defaults to always True.

        Returns:
            list[Node]: the destinations.
        """
        return [n for n in self.road_network.nodes if self.is_destination(n) and condition(n)]

    def road_edges(self) -> list[Edge]:
        """
        Returns a list of all edges that are roads.

        Returns:
            list[Node]: the nodes connected by roads.
        """
        return [Edge((n1, n2)) for (n1, n2) in self.road_network.edges if self.is_road(n1, n2)]

    def roads_from(self, source: Node, condition: Callable[[Node], bool] = lambda _ : True) -> list[Node]:
        """
        Returns a list of all nodes that can be reached by road from a given source node.
        If a condition function is provided, only nodes fulfilling that condition are returned.

        Args:
            source (Node): the source node.
            condition (Callable[[Node], bool], optional): a condition on the nodes. Defaults to always True.
            
        Returns:
            list[Node]: a list of nodes reachable by road.
        """
        return [sink for _, sink, has_road in self.road_network.out_edges(source, data = "road") if has_road and condition(sink)]

    def roads_to(self, sink: Node, condition: Callable[[Node], bool] = lambda _ : True) -> list[Node]:
        """
        Returns a list of all nodes that can reach the given sink node by road.
        If a condition function is provided, only nodes fulfilling that condition are returned.

        Args:
            sink (Node): the sink node.
            condition (Callable[[Node], bool], optional): a condition on the nodes. Defaults to always True.

        Returns:
            list[Node]: a list of nodes from which the sink node can be reached by road.
        """
        return [source for source, _, has_road in self.road_network.in_edges(sink, data = "road") if has_road and condition(source)]

    def is_destination(self, node: Node) -> bool:
        """
        Checks if a node is a destination.

        Args:
            node (Node): the node.

        Returns:
            bool: True if the node is a destination.
        """
        return self.road_network.nodes[node].get("destination", False)

    def is_charging_point(self, node: Node) -> bool:
        """
        Checks if a node is a charging point.

        Args:
            node (Node): the node.

        Returns:
            bool: True if the node is a charging point.
        """
        return self.road_network.nodes[node].get("charging_point", False)

    def edge_direction(self, source: Node, sink: Node) -> Direction:
        """
        Returns the direction of the edge going from source to sink.

        Args:
            source (Node): source node.
            sink (Node): sink node.

        Returns:
            Direction: the direction in degrees.
        """
        return self.road_network[source][sink]["direction"]

    def shortest_path(self, source: Node, target: Node) -> list[Node]:
        """
        Returns the shortest path from source to sink as a list of nodes.

        Args:
            source (Node): the source node.
            target (Node): the target node.

        Returns:
            list[Node]: the path.
        """
        return nx.shortest_path(self.road_network, source = source, target = target,
                                weight = lambda n1, n2, attributes: 1 if attributes["road"] else 10000000)

    def path_to_nearest(self, source: Node, targets: list[Node]) -> list[Node]:
        """
        Given a source node and a list of target nodes, return the path to the nearest of the targets.

        Args:
            source (Node): the source node.
            targets (list[Node]): the list of target nodes.

        Returns:
            list[Node]: the path to the nearest target node.
        """
        shortest_paths = [self.shortest_path(source, target) for target in targets]
        shortest_paths.sort(key = len)
        return shortest_paths[0]
    
    # Provide reference to some of the RoadGridNetwork methods directly in the space.

    def has_road_to(self, source: Node, direction: Direction) -> bool:
        """
        Calls the method with the same name on self.road_network.
        """
        return self.road_network.has_road_to(source, direction)

    def is_road(self, node1: Node, node2: Optional[Node] = None) -> bool:
        """
        Calls the method with the same name on self.road_network.
        """
        return self.road_network.is_road(node1, node2)

    # Mesa space API (adapted from mesa.space.NetworkGrid)

    def place_agent(self, agent: core.Agent, node_id: Node) -> None:
        """Place an agent in a node."""
        self.road_network.nodes[node_id]["agent"].append(agent)
        agent.pos = node_id

    def get_neighborhood(self, node_id: Node, include_center: bool = False, radius: int = 1) -> list[Node]:
        """Get all adjacent nodes within a certain radius"""
        if radius == 1:
            neighborhood = list(self.road_network.neighbors(node_id))
            if include_center:
                neighborhood.append(node_id)
        else:
            neighbors_with_distance = nx.single_source_shortest_path_length(self.road_network, node_id, radius)
            if not include_center:
                del neighbors_with_distance[node_id]
            neighborhood = sorted(neighbors_with_distance.keys())
        return neighborhood

    def get_neighbors(self, node_id: Node, include_center: bool = False) -> list[core.Agent]:
        """Get all agents in adjacent nodes."""
        neighborhood = self.get_neighborhood(node_id, include_center)
        return self.get_cell_list_contents(neighborhood)

    def move_agent(self, agent: core.Agent, node_id: Node) -> None:
        """Move an agent from its current node to a new node."""
        if hasattr(agent, "heading"):
            agent.heading = self.road_network[agent.pos][node_id]["direction"]
        self.remove_agent(agent)
        self.place_agent(agent, node_id)

    def remove_agent(self, agent: core.Agent) -> None:
        """Remove the agent from the network and set its pos attribute to None."""
        node_id = agent.pos
        self.road_network.nodes[node_id]["agent"].remove(agent)
        agent.pos = None

    def is_cell_empty(self, node_id: Node) -> bool:
        """Returns a bool of the contents of a cell."""
        return self.road_network.nodes[node_id]["agent"] == []

    def get_cell_list_contents(self, cell_list: list[Node]) -> list[core.Agent]:
        """Returns a list of the agents contained in the nodes identified
        in `cell_list`; nodes with empty content are excluded.
        """
        return list(self.iter_cell_list_contents(cell_list))

    def get_all_cell_contents(self) -> list[core.Agent]:
        """Returns a list of all the agents in the network."""
        return self.get_cell_list_contents(self.road_network.nodes)

    def iter_cell_list_contents(self, cell_list: list[Node]) -> Iterator[core.Agent]:
        """Returns an iterator of the agents contained in the nodes identified
        in `cell_list`; nodes with empty content are excluded.
        """
        return itertools.chain.from_iterable(
            self.road_network.nodes[node_id]["agent"]
            for node_id in itertools.filterfalse(self.is_cell_empty, cell_list)
        )