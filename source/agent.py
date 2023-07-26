"""
Provides agents for the SoSSim system-of-systems simulator.
"""

import random
from typing import List

import capabilities
import mesa

class Vehicle(mesa.Agent):

    def __init__(self, unique_id: int, model: "model.TransportSystem"):
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
        space = self.model.space
        available_positions = [p for p in space.road_nodes() if space.is_cell_empty(p)]
        space.place_agent(self, random.choice(available_positions))

        # Add a view
        if self.model.view:
            self.view = self.model.view.create_agent_view(self)

        # Add a plan, which is a list of capability instances.
        self.plan: List[capabilities.Capability] = []

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