"""
Provides concrete agents for the SoSSim system-of-systems simulator.
"""
import capabilities
from configuration import Configuration
from sos_core import SoSAgent
from space import Node

class Vehicle(SoSAgent):

    # Define configuration parameters relevant to this class
    Configuration.add_param(class_name = "Vehicle", name = "max_load", type = int, default = 3, flag = "-ml", 
                            help = "maximum load of a vehicle")
    Configuration.add_param(class_name = "Vehicle", name = "max_energy", type = int, default = 100, flag = "-me", 
                            help = "maximum energy of a vehicle")
    Configuration.add_param(class_name = "Vehicle", name = "charging_speed", type = int, default = 10, flag = "-cs", 
                            help = "the charging speed of a vehicle")
    Configuration.add_param(class_name = "Vehicle", name = "parking_probability", type = float, default = 0.1, flag = "-pp", 
                            help = "probability that a vehicle will start looking for a parking")

    def __init__(self, unique_id: int, model: "model.TransportSystem", configuration: Configuration):
        """
        Creates a vehicle agent in a simulation model.

        Args:
            unique_id (int): the unique id of the agent.
            model (model.TransportSystem): the model in which the agent is situated.
        """
        super().__init__(unique_id, model)
        configuration.initialize(self)
        self.pos: Node = (0, 0)

        # Add a load capacity of the vehicle
        self.capacity = self.model.random.choice(range(1, self.max_load + 1))

        # Add an energy level and initialize it to a random value
        self.energy_level = self.model.random.choice(range(round(0.2 * self.max_energy), self.max_energy + 1))

        # Randomly select a starting position which is not yet occupied by some other vehicle.
        space = self.model.space
        available_positions = [p for p in space.road_nodes() if space.is_cell_empty(p)]
        space.place_agent(self, self.model. random.choice(available_positions))

        # Set the initial heading of the vehicle to that of the heading of one of the roads leading into the current position.
        self.heading = space.edge_direction(space.roads_to(self.pos)[0], self.pos)

    def create_plan(self):
        """
        The vehicle creates a plan, which consists of randomly moving to one the neighbours in the road network.
        Occasionally, it chooses instead to find a parking.
        When energy level is low, it searches for an available charging point and charges energy there.
        """
        space = self.model.space
        if self.energy_level < 30:
            # Find a charging point and charge energy there.
            print(f"Vehicle {self.unique_id} needs to charge")
            self.plan = [capabilities.FindDestinationCapability(self, lambda pos: space.is_charging_point(pos)),
                         capabilities.ChargeEnergyCapability(self)]
        elif self.model.random.random() < self.parking_probability:
            # Find a destination which is not a charging point.
            self.plan = [capabilities.FindDestinationCapability(self, lambda pos: not space.is_charging_point(pos))]
        else:
            try:
                new_pos = self.model.random.choice([node for node in space.roads_from(self.pos) if not space.is_destination(node)])
                self.plan = [capabilities.MoveCapability(self, new_pos)]
            except IndexError as e:
                print(e)
                print(f"Error occured for agent {self.unique_id} in position = {self.pos}")
                self.plan = [capabilities.Capability(self)]