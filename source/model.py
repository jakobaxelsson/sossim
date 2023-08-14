"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys

from entities import Cargo, Vehicle
from configuration import Configuration, configurable, Param
import core
import space
from view import viewable

@configurable
@viewable
class TransportSystem(core.Model):
    # Define configuration parameters relevant to this class
    num_vehicles: Param(int) = 10   # number of vehicles
    num_cargos:   Param(int) = 10                # number of cargos
    random_seed:  Param(int) = -1   # seed for random number generator (use -1 to initialize from system time)

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