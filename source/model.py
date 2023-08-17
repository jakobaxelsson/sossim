"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys
from typing import Annotated

from entities import Cargo, Vehicle
from configuration import Configuration, configurable
import core
import space

@configurable
class TransportSystem(core.Model):
    # Define configuration parameters relevant to this class
    num_vehicles: Annotated[int, "Param", "number of vehicles"] = 10
    num_cargos:   Annotated[int, "Param", "number of cargos"] = 10
    random_seed:  Annotated[int, "Param", "seed for random number generator (use -1 to initialize from system time)"] = -1

    def __init__(self, configuration: Configuration):
        """
        Creates a transport system model.

        Args:
            configuration (Configuration): the configuration of parameters from which the model is generated.
        """
        # Initialize superclass and configuration
        super().__init__()
        configuration.initialize(self)
        
        # Setup random number generation.
        if self.random_seed == -1:
            self.random_seed = random.randrange(sys.maxsize)
        self.random.seed(self.random_seed)

        # Create the space
        self.space = space.RoadNetworkGrid(configuration, self)

        # Create vehicles
        for i in range(self.num_vehicles):
            Vehicle(self, configuration)

        # Create cargos
        for i in range(self.num_cargos):
            Cargo(self, configuration)

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        self.update_views()