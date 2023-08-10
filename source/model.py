"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys

import agent
from configuration import Configuration, configurable, Param
import mesa
import space
from view import viewable

@configurable
@viewable
class TransportSystem(mesa.Model):
    # Define configuration parameters relevant to this class
    num_agents:  Param(int, flag = "-N", help = "number of vehicles") = 10 # type: ignore
    random_seed: Param(int, flag = "-r", help = "seed for random number generator (use -1 to initialize from system time)") = -1 # type: ignore

    def __init__(self, configuration: Configuration):
        """
        Creates a transport system model.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
        """
        super().__init__()

        # Initialize configuration
        configuration.initialize(self)

        if self.random_seed == -1:
            self.random_seed = random.randrange(sys.maxsize)
        self.random.seed(self.random_seed)

        # Create time and space
        self.schedule = mesa.time.SimultaneousActivation(self)
        self.space = space.RoadNetworkGrid(configuration, self)

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