"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys
from typing import Any

import agent
import mesa
import space

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

    def generate(self, N: int = 10, width: int = 10, height: int = 10, destination_density: float = 0.3, random_seed: int | None = None):
        """
        Generates the model, including creating its space and agents.

        Args:
            N (int, optional): number of agents. Defaults to 10.
            width (int, optional): width of the coarse grid space. Defaults to 10.
            height (int, optional): height of the coarse grid space. Defaults to 10.
            destination_density (float, optional): the proportion of possibly destinations that exist on the map. Defaults to 0.3.
            random_seed (int | None, optional): a random seed. Defaults to None, in which case a seed is generated.
        """
        self.num_agents = N
        self.width = width
        self.height = height
        self.destination_density = destination_density
        self.random_seed = random_seed or random.randrange(sys.maxsize)
        random.seed(self.random_seed)
        self.schedule = mesa.time.SimultaneousActivation(self)

        self.space = space.RoadNetworkGrid(size_x = self.width, size_y = self.height, destination_density = self.destination_density)
        if self.view:
            self.view.update(self)
        # Create agents
        for i in range(self.num_agents):
            a = agent.Vehicle(i, self)
            self.schedule.add(a)

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        if self.view:
            self.view.update_time(self.schedule.time)