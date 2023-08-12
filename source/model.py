"""
Provides models for the SoSSim system-of-systems simulator.
"""
import random
import sys

from entities import Cargo, Vehicle
from configuration import Configuration, configurable, Param
import mesa
import space
from view import viewable

@configurable
@viewable
class TransportSystem(mesa.Model):
    # Define configuration parameters relevant to this class
    num_vehicles: Param(int, flag = "-N") = 10   # number of vehicles
    num_cargos:   Param(int) = 10                # number of cargos
    random_seed:  Param(int, flag = "-r") = -1   # seed for random number generator (use -1 to initialize from system time)

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

        # Create time and space, using a staged activation scheduler based on the OODA loop
        self.schedule = mesa.time.StagedActivation(self, ["observe", "orient", "decide", "act"])
        self.space = space.RoadNetworkGrid(configuration, self)

        # Create vehicles
        for i in range(self.num_vehicles):
            a = Vehicle(self, configuration)
            self.schedule.add(a)

        # Create cargos
        for i in range(self.num_cargos):
            c = Cargo(self, configuration)
            self.schedule.add(c)

    def step(self):
        """
        Performs a simulation step and updates the views.
        """
        self.schedule.step()
        self.update_views()