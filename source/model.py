"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys

import agent
from configuration import Configuration
import mesa
import space
from view import Viewable

class TransportSystem(mesa.Model, Viewable):
    # Define configuration parameters relevant to this class
    Configuration.add_param(class_name = "TransportSystem", name = "num_agents", type = int, default = 10, flag = "-N", 
                            help = "number of vehicles")
    Configuration.add_param(class_name = "TransportSystem", name = "random_seed", type = int, default = random.randrange(sys.maxsize), flag = "-r", 
                            help = "seed for random number generator")

    def __init__(self, configuration: Configuration):
        """
        Creates a transport system model.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
        """
        super().__init__()

        # Initialize configuration
        configuration.initialize(self)

        # TODO: Mesa has its own random seed handling, see source code of Mesa.model. 
        random.seed(self.random_seed)

        # Create time and space
        self.schedule = mesa.time.SimultaneousActivation(self)
        self.space = space.RoadNetworkGrid(configuration)

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