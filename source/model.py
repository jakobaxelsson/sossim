"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys
from typing import Any

import agent
from configuration import Configuration
import mesa
import space

class TransportSystem(mesa.Model):
    # Define configuration parameters relevant to this class
    Configuration.add_param(class_name = "TransportSystem", name = "num_agents", type = int, default = 10, flag = "-N", 
                            help = "number of vehicles")
    Configuration.add_param(class_name = "TransportSystem", name = "width", type = int, default = 10, flag = "-x", 
                            help = "number of grid cells in x dimension")
    Configuration.add_param(class_name = "TransportSystem", name = "height", type = int, default = 10, flag = "-y", 
                            help = "number of grid cells in y dimension")
    Configuration.add_param(class_name = "TransportSystem", name = "destination_density", type = float, default = 0.3, flag = "-dd", 
                            help = "probability of generating a destination in a position where it is possible")
    Configuration.add_param(class_name = "TransportSystem", name = "random_seed", type = int, default = random.randrange(sys.maxsize), flag = "-r", 
                            help = "seed for random number generator")

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
        self.space = space.RoadNetworkGrid()

    def add_view(self, view: Any):
        """
        Adds a view to the model.

        Args:
            view (Any): the view to be added.
        """
        self.view = view

    def generate(self, configuration: Configuration):
        """
        Generates the model, including creating its space and agents.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
        """
        configuration.initialize(self)
        random.seed(self.random_seed)
        self.schedule = mesa.time.SimultaneousActivation(self)

        self.space = space.RoadNetworkGrid(width = self.width, height = self.height, destination_density = self.destination_density)
        if self.view:
            self.view.update(self)
        # Create agents
        for i in range(self.num_agents):
            a = agent.Vehicle(i, self, configuration)
            self.schedule.add(a)

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        if self.view:
            self.view.update_time(self.schedule.time)