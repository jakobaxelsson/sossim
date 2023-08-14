"""
Provides concrete agents and other entities.
"""
from typing import Optional

import capabilities
from configuration import Configuration, configurable, Param
import core 
from space import Node

@configurable
class Vehicle(core.Agent):
    # Define configuration parameters relevant to this class
    max_load:            Param(int)   = 3     # maximum load of a vehicle
    max_energy:          Param(int)   = 100   # maximum energy of a vehicle
    charging_speed:      Param(int)   = 10    # the charging speed of a vehicle

    def __init__(self, model: "model.TransportSystem", configuration: Configuration):
        """
        Creates a vehicle agent in a simulation model.

        Args:
            model (model.TransportSystem): the model in which the agent is situated.
            configuration (Configuration): the configuration parameters.
        """
        super().__init__(model)
        configuration.initialize(self)

        # Add a load capacity of the vehicle and a list of cargos
        self.capacity = self.model.random.choice(range(self.max_load)) + 1
        self.cargos: list["Cargo"] = []

        # Add an energy level and initialize it to a random value
        self.energy_level = self.model.random.choice(range(round(0.2 * self.max_energy), self.max_energy + 1))

        # Randomly select a starting position which is not yet occupied by some other vehicle.
        space = self.model.space
        available_positions = space.road_nodes(space.is_cell_empty)
        space.place_agent(self, self.model.random.choice(available_positions))

        # Set the initial heading of the vehicle to that of the heading of one of the roads leading into the current position.
        self.heading = space.edge_direction(space.roads_to(self.pos)[0], self.pos)

    def can_coexist(self, other: core.Entity) -> bool:
        """
        Returns True if this entity can coexist in the same cell with the other entity.
        Vehicles are not allowed to coexist with other vehicles.

        Args:
            other (core.Entity): another entity.

        Returns:
            bool: True if coexistance is possible.
        """
        return not isinstance(other, Vehicle)

    def available_cargo(self, node: Node) -> list["Cargo"]:
        """
        Returns the list of available cargos in a destination node that the vehicle can carry.
        
        Returns:
            list[Cargo]: the list of cargo.
        """
        space = self.model.space
        if space.is_destination(node):
            return [e for e in space.get_cell_list_contents([node]) if isinstance(e, Cargo) and e.weight <= self.load_capacity()]
        else:
            return []

    def update_plan(self):
        """
        The vehicle creates a plan, which consists of randomly moving to one the neighbours in the road network.
        Occasionally, it chooses instead to find a parking.
        When energy level is low, it searches for an available charging point and charges energy there.

        The vehicle creates a plan according to the following principles:
        - If it does not have a plan already, then:
            - If it has a cargo, transport it to its destination and unload it. 
            - If it does not have any cargo, then:
                - If there is a suitable cargo in the current destination, load it.
                - Otherwise, search for a cargo to transport by randomly moving around.
        - If it is low on energy, first search for a charging point.
        """
        space = self.model.space
        if not self.plan:
            if self.cargos:
                # Go to the destination of the cargo, and when arriving, unload it
                self.plan = [capabilities.FindDestination(self, condition = None, final = self.cargos[0].destination), 
                             capabilities.UnloadCargo(self, self.cargos[0])]
                # To avoid that the vehicle directly picks up the cargo again, move away after unloading
                node1 = space.roads_from(self.cargos[0].destination)[0]
                node2 = space.roads_from(node1, lambda node: not space.is_destination(node))[0]
                self.plan += [capabilities.Move(self, [node1, node2])]
            elif cargos := self.available_cargo(self.pos):
                # There is a suitable cargo in the current position, so load it.
                self.plan = [capabilities.LoadCargo(self, cargos[0])]
            else:
                # Randomly search for a destination where there is a cargo 
                self.plan = [capabilities.FindDestination(self, condition = self.available_cargo)]

        # If low on energy, make sure that there is a plan to recharge.
        if self.energy_level < 30 and not any(isinstance(c, capabilities.ChargeEnergy) for c in self.plan):
            # Go to the nearest charging point and charge energy there before proceeding with the plan.
            charging_points = space.destination_nodes(space.is_charging_point)
            self.plan = [capabilities.Move(self, space.path_to_nearest(self.pos, charging_points)),
                         capabilities.ChargeEnergy(self)]

        # If the vehicle wants to enter a destination that is already occupied, move on instead to avoid deadlock
        # - The vehicle has a plan
        # - The first step of the plan is to make a move
        # - There is a route to move along
        # - The first step of the route is a destination
        # - There are other agents in that destination with which the vehicle cannot coexist
        if self.plan[0] and \
            isinstance(self.plan[0], capabilities.Move) and \
            self.plan[0].route and \
            space.is_destination(self.plan[0].route[0]) and \
            not all(self.can_coexist(other) for other in space.get_cell_list_contents([self.plan[0].route[0]])):
            route = [self.model.random.choice(space.roads_from(self.pos, lambda node: not space.is_destination(node)))]
            self.plan = [capabilities.Move(self, route)]

    def move(self, target: Node):
        """
        Moves the vehicle to the given target node.

        Args:
            target (Node): the new node.
        """
        self.model.space.move_agent(self, target)
        # Also move all the cargos of the agent
        for cargo in self.cargos:
            self.model.space.move_agent(cargo, target)
        # Reduce agent energy 
        self.energy_level -= 1

    def load_capacity(self) -> int:
        """
        Returns the remaining load capacity of the vehicle.

        Returns:
            int: the remaining load capacity.
        """
        return self.max_load - sum([c.weight for c in self.cargos])

    def load_cargo(self, cargo: "Cargo"):
        """
        Loads the cargo onto this vehicle.

        Args:
            cargo (Cargo): the cargo.
        """
        self.cargos.append(cargo)
        cargo.load_onto(self)

    def unload_cargo(self, cargo: "Cargo"):
        """
        Unload the cargo from this vehicle.

        Args:
            cargo (Cargo): the cargo.
        """
        self.cargos.remove(cargo)
        cargo.unload()

@configurable
class Cargo(core.Entity):
    """
    A cargo is an entity which can be transported by vehicles.
    It has a weight, a position, a destination, and a carrier.
    """
    max_cargo_weight: Param(int) = 3  # The maximum weight of a cargo.

    def __init__(self, model: "model.TransportSystem", configuration: Configuration):
        """
        Creates a cargo entitiy in a simulation model.

        Args:
            model (model.TransportSystem): the model in which the cargo is situated.
            configuration (Configuration): the configuration parameters.
        """
        super().__init__(model)
        configuration.initialize(self)

        space = self.model.space
        available_positions = space.road_nodes(space.is_destination)
        space.place_agent(self, self.model.random.choice(available_positions))

        self.weight = self.model.random.choice(range(self.max_cargo_weight)) + 1
        self.select_destination()
        self.carrier: Vehicle | None = None

    def select_destination(self, destination: Optional[Node] = None):
        """
        Selects a destination for the cargo. If no destination is provided, a random one is picked.

        Args:
            destination (Node, optional): the new destination. Defaults to None.
        """
        if destination:
            self.destination = destination
        else:
            space = self.model.space
            self.destination = self.model.random.choice(space.road_nodes(lambda n: space.is_destination(n) and not space.is_charging_point(n)))

    def load_onto(self, carrier: Vehicle):
        """
        The cargo gets loaded onto a carrier vehicle.

        Args:
            carrier (Vehicle): the carrier.
        """
        self.carrier = carrier

    def unload(self):
        """
        The cargo gets unloaded from a carrier vehicle.
        """
        self.carrier = None
        # If the cargo has reached its destination, select a new destination.
        if self.pos == self.destination:
            self.select_destination()