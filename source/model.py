"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys
from typing import List

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

    def __init__(self, configuration: Configuration):
        """
        Creates a transport system model.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
            views (List[View]): a list of views to be added to the model.
        """
        super().__init__()

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

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        self.update_views()