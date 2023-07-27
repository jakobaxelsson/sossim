"""
Provides concrete agents for the SoSSim system-of-systems simulator.
"""

import random

import capabilities
from sos_core import SoSAgent
from space import Node

class Vehicle(SoSAgent):

    def __init__(self, unique_id: int, model: "model.TransportSystem"):
        """
        Creates a vehicle agent in a simulation model.

        Args:
            unique_id (int): the unique id of the agent.
            model (model.TransportSystem): the model in which the agent is situated.
        """
        super().__init__(unique_id, model)
        self.pos: Node = (0, 0)

        # Add a load capacity of the vehicle
        self.capacity = random.choice([1, 2, 3])

        # Randomly select a starting position which is not yet occupied by some other vehicle.
        space = self.model.space
        available_positions = [p for p in space.road_nodes() if space.is_cell_empty(p)]
        space.place_agent(self, random.choice(available_positions))

        # Set the initial heading of the vehicle to that of the heading of one of the roads leading into the current position.
        self.heading = space.edge_direction(space.roads_to(self.pos)[0], self.pos)

        # Add a view
        if self.model.view:
            self.view = self.model.view.create_agent_view(self)

    def create_plan(self):
        """
        The vehicle creates a plan, which consists of randomly moving to one the neighbours in the road network.
        Occasionally, it chooses instead to find a parking.
        """
        space = self.model.space
        if random.random() < 0.1:
            self.plan = [capabilities.ParkCapability(self)]
        else:
            try:
                new_pos = random.choice([node for node in space.roads_from(self.pos) if not space.is_destination(node)])
                self.plan = [capabilities.MoveCapability(self, new_pos)]
            except IndexError as e:
                print(e)
                print(f"Error occured for agent {self.unique_id} in position = {self.pos}")
                self.plan = [capabilities.Capability(self)]