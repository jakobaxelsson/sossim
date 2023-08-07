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
from view import Viewable

class TransportSystem(mesa.Model, Viewable):
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

    def __init__(self, configuration: Configuration, view: Any = None):
        """
        Creates a transport system model.
        Note that it is empty initially, and needs to be generated using the generate method.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
            view (Any): an optional view of the model.
        """
        # Initialize configuration
        configuration.initialize(self)

        # TODO: Mesa has its own random seed handling, see source code of Mesa.model. 
        random.seed(self.random_seed)

        # Create time and space
        self.schedule = mesa.time.SimultaneousActivation(self)
        self.space = space.RoadNetworkGrid(width = self.width, height = self.height, destination_density = self.destination_density)

        # Create agents
        for i in range(self.num_agents):
            a = agent.Vehicle(i, self, configuration)
            self.schedule.add(a)

        # Add a view.
        self.add_view(view)

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        if self.get_view():
            self.get_view().update_time(self.schedule.time)