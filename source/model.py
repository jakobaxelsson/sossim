import math
import random
import sys

import networkx as nx

import mesa


class GridWorld:
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

        # Generate roads
        self.generate_roads()

    def generate_roads(self):
        self.coarse_network = nx.Graph()
        # Step 1. Create a connected graph whose nodes are a subset of the grid cells.
        node = (self.size_x // 2, self.size_y //2)
        edge_candidates = [(node, neighbour) for neighbour in self.neighbours(node)]

        # The number of nodes is determined by the road_density parameter.
        while nx.number_of_nodes(self.coarse_network) < self.size_x * self.size_y * self.road_density:
            # Pick an edge to add, removing it from the candidates and adding it to the graph
            edge = random.choices(edge_candidates, weights = [self.edge_preference(e) for e in edge_candidates])[0]

            # If the sink of the new edge is new in the graph, add edges to its neighbours as new edge candidates
            node = edge[1]
            if not self.coarse_network.has_node(node):
                edge_candidates += [(node, neighbour) for neighbour in self.neighbours(node)]
            # Add the new edge (and implicitly its nodes), and remove the edge as a candidate.
            self.coarse_network.add_edge(*edge)
            edge_candidates.remove(edge)

        # Step 2. Add lanes and roundabouts.
        # Create a new graph, this time directed. Each node in the coarse graph maps to 4 x 4 nodes in the new graph.
        self.road_network = nx.DiGraph()

        for (x, y) in self.coarse_network:
            if (x + 1, y) in self.coarse_network[(x, y)]: # East
                path = [(x * 4 + 2 + i, y * 4 + 2) for i in range(4)]
                nx.add_path(self.road_network, path, direction = "E")
            if (x - 1, y) in self.coarse_network[(x, y)]: # West
                path = [(x * 4 + 1 - i, y * 4 + 1) for i in range(4)]
                nx.add_path(self.road_network, path, direction = "W")
            if (x, y - 1) in self.coarse_network[(x, y)]: # North
                path = [(x * 4 + 2, y * 4 + 1 - i) for i in range(4)]
                nx.add_path(self.road_network, path, direction = "N")
            if (x, y + 1) in self.coarse_network[(x, y)]: # South
                path = [(x * 4 + 1, y * 4 + 2 + i) for i in range(4)]
                nx.add_path(self.road_network, path, direction = "S")

        # Add connections for roundabouts and through roads
        for (x, y) in self.coarse_network:
            if self.coarse_network.degree[(x, y)] == 1:
                # Dead ends need to make it possible to turn around, which requires adding three out of four edges.
                if (x + 1, y) not in self.coarse_network[(x, y)]: # No eastern neighbour
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 2), (x * 4 + 2, y * 4 + 1), direction = "N")
                if (x - 1, y) not in self.coarse_network[(x, y)]: # No western neighbour
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 1), (x * 4 + 1, y * 4 + 2), direction = "S")
                if (x, y - 1) not in self.coarse_network[(x, y)]: # No northern neighbour
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 1), (x * 4 + 1, y * 4 + 1), direction = "W")
                if (x, y + 1) not in self.coarse_network[(x, y)]: # No southern neighbour
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 2), (x * 4 + 2, y * 4 + 2), direction = "E")
            if self.coarse_network.degree[(x, y)] == 2:
                # Through roads
                if (x, y - 1) in self.coarse_network[(x, y)] and (x - 1, y) in self.coarse_network[(x, y)]: # Northern and western neighbours
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 2), (x * 4 + 2, y * 4 + 2), direction = "E")
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 2), (x * 4 + 2, y * 4 + 1), direction = "N")
                if (x, y - 1) in self.coarse_network[(x, y)] and (x, y + 1) in self.coarse_network[(x, y)]: # Northern and southern neighbours
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 1), (x * 4 + 1, y * 4 + 2), direction = "S")
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 2), (x * 4 + 2, y * 4 + 1), direction = "N")
                if (x, y - 1) in self.coarse_network[(x, y)] and (x + 1, y) in self.coarse_network[(x, y)]: # Northern and eastern neighbours
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 1), (x * 4 + 1, y * 4 + 2), direction = "S")
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 2), (x * 4 + 2, y * 4 + 2), direction = "E")
                if (x - 1, y) in self.coarse_network[(x, y)] and (x, y + 1) in self.coarse_network[(x, y)]: # Western and southern neighbours
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 2), (x * 4 + 2, y * 4 + 1), direction = "N")
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 1), (x * 4 + 1, y * 4 + 1), direction = "W")
                if (x - 1, y) in self.coarse_network[(x, y)] and (x + 1, y) in self.coarse_network[(x, y)]: # Western and eastern neighbours
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 1), (x * 4 + 1, y * 4 + 1), direction = "W")
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 2), (x * 4 + 2, y * 4 + 2), direction = "E")
                if (x, y + 1) in self.coarse_network[(x, y)] and (x + 1, y) in self.coarse_network[(x, y)]: # Southern and eastern neighbours
                    self.road_network.add_edge((x * 4 + 2, y * 4 + 1), (x * 4 + 1, y * 4 + 1), direction = "W")
                    self.road_network.add_edge((x * 4 + 1, y * 4 + 1), (x * 4 + 1, y * 4 + 2), direction = "S")
            if self.coarse_network.degree[(x, y)] > 2:
                # Three and four way crossings require roundabouts, so all four edges are added.
                self.road_network.add_edge((x * 4 + 1, y * 4 + 1), (x * 4 + 1, y * 4 + 2), direction = "S")
                self.road_network.add_edge((x * 4 + 1, y * 4 + 2), (x * 4 + 2, y * 4 + 2), direction = "E")
                self.road_network.add_edge((x * 4 + 2, y * 4 + 2), (x * 4 + 2, y * 4 + 1), direction = "N")
                self.road_network.add_edge((x * 4 + 2, y * 4 + 1), (x * 4 + 1, y * 4 + 1), direction = "W")

        # Keep track of all agents in a node
        for node in self.road_network.nodes:
            self.road_network.nodes[node]["agent"] = []

    def edge_preference(self, edge):
        # Returns a numerical value indicating how preferred this edge is (higher means more likely to be selected)

        # Count number of existing edges for the source and sink of the selected edge
        nb_source_edges = self.coarse_network.degree[edge[0]] if edge[0] in self.coarse_network else 0
        nb_sink_edges = self.coarse_network.degree[edge[1]] if edge[1] in self.coarse_network else 0

        # Count distance of sink from center of world normalized with respect to the size of the world
        dist_x = edge[1][0] - self.size_x // 2
        dist_y = edge[1][1] - self.size_y // 2
        norm_dist = math.sqrt(dist_x ** 2 + dist_y ** 2) / math.sqrt((self.size_x // 2) ** 2 + (self.size_y // 2) ** 2)

        # Prefer adding edges away from the center and adding new nodes (a small epsilon is added to ensure that weights > 0)
        return 50 * norm_dist / (nb_source_edges ** 2 + nb_sink_edges + 0.00001)
        
    def neighbours(self, coordinates):
        x, y = coordinates
        result = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [(x, y) for (x, y) in result if x >= 0 and y >= 0 and x < self.size_x and y < self.size_y ]


class Vehicle(mesa.Agent):

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        # Add a load capacity of the vehicle
        self.capacity = random.choice([1, 2, 3])

        # Randomly select a starting position which is not yet occupied by some other vehicle.
        rnw = self.model.grid.road_network
        available_positions = [p for p in rnw.nodes if not rnw.nodes[p]["agent"]]
        self.pos = random.choice(available_positions)
        rnw.nodes[self.pos]["agent"].append(self)
        self.new_pos = self.pos

        # Set the initial heading of the vehicle.
        self.heading = rnw[self.pos][next(rnw.neighbors(self.pos))]["direction"]

        # Add a view
        if self.model.view:
            self.view = self.model.view.create_agent_view(self)

    def step(self):
        # Randomly select where to go while avoiding collisions with other vehicles.
        new_pos = (x, y) = random.choice(list(self.model.grid.road_network.neighbors(self.pos)))

        # If there is a vehicle in that position, do not move.
        if self.model.grid.road_network.nodes[new_pos]["agent"]:
            return

        # Check if the move is allowed, with respect to the priority rules of roundabouts.
        # Determine direction of travel (x - x', y - y'), where (x, y) is current and (x', y') is new pos.
        # Use this to lookup delta to the square to consider.
        # TODO: This computation should be handled in the grid object! Query it with self.pos, and get back list of available choices!
        delta = (x - self.pos[0], y - self.pos[1])
        (prio_x, prio_y) = { (0, -1) : (-1, 0), (-1, 0): (0, 1), (0, 1) : (1, 0), (1, 0) : (0, -1) }[delta]
        priority_pos = (x + prio_x, y + prio_y)
        if self.model.grid.road_network.has_edge(priority_pos, new_pos) and self.model.grid.road_network.nodes[priority_pos]["agent"]:
            self.new_pos = self.pos
        else:
            self.heading = self.model.grid.road_network[self.pos][new_pos]["direction"]
            self.new_pos = new_pos

    def advance(self):
        # Move the vehicle on the grid
        self.model.grid.road_network.nodes[self.pos]["agent"].remove(self)
        self.model.grid.road_network.nodes[self.new_pos]["agent"].append(self)
        self.pos = self.new_pos

        # Update the position in the drawing
        if self.model.view:
            self.view.update(self)

class TransportSystem(mesa.Model):
    def __init__(self):
        # TODO: Initialize from a configuration object, to make it easier to edit, load, and save it.
        # Maybe the parameters should instead be provided to the generate function?
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

        self.grid = GridWorld(self.width, self.height)
        self.grid.generate_roads()
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