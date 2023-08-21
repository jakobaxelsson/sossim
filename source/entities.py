"""
Provides concrete agents and other entities.
"""
from typing import Annotated, Callable, Optional, TYPE_CHECKING

from capabilities import ChargeEnergy, FollowRoute, LoadCargo, UnloadCargo
from configuration import Configuration, configurable
import core 
from space import Node, RoadNetworkGrid

if TYPE_CHECKING:
    import model

class Navigator:
    """
    A navigation system that can be used to find routes between destinations.
    """
    def __init__(self, space: RoadNetworkGrid):
        """
        Initializes the navigator based on the space it navigates in.

        Args:
            space (RoadNetworkGrid): the space to navigate in.
        """
        self.space = space

    def shortest_path(self, source: Node, target: Node) -> list[Node]:
        """
        Returns the shortest path from source to sink as a list of nodes.

        Args:
            source (Node): the source node.
            target (Node): the target node.

        Returns:
            list[Node]: the path.
        """
        return self.space.shortest_path(source, target)

    def path_to_nearest(self, source: Node, targets: list[Node]) -> list[Node]:
        """
        Given a source node and a list of target nodes, return the path to the nearest of the targets.

        Args:
            source (Node): the source node.
            targets (list[Node]): the list of target nodes.

        Returns:
            list[Node]: the path to the nearest target node.
        """
        return self.space.path_to_nearest(source, targets)

    def path_to_nearest_charging_point(self, source: Node) -> list[Node]:
        """
        Returns the path to the nearest charging point from a source node.

        Args:
            source (Node): the starting point.

        Returns:
            list[Node]: the path to the nearest charging point.
        """
        charging_points = self.space.destination_nodes(self.space.is_charging_point)
        return self.space.path_to_nearest(source, charging_points)

class VehicleWorldModel(core.WorldModel):
    """
    The world model of a vehicle.
    """
    def __init__(self, agent: "Vehicle"):
        """
        Initializes a vehicle world model.
        """
        super().__init__(agent)

    def perceive(self):
        """
        Updates the perception of the world as represented in this world model.
        This is done by setting space to a subgraph of the model's space, that only contain neighboring nodes.
        """
        neighbors = self.agent.model.space.grid_neighbors(self.agent.pos, diagonal = True, center = True, dist = self.agent.perception_range)
        self.space = self.agent.model.space.subgraph([self.agent.pos] + neighbors)

@configurable
class Vehicle(core.Agent):
    # Define configuration parameters relevant to this class
    max_load:         Annotated[int, "Param", "maximum load of a vehicle"]           = 3 
    max_energy:       Annotated[int, "Param", "maximum energy of a vehicle"]         = 100 
    charging_speed:   Annotated[int, "Param", "the charging speed of a vehicle"]     = 10 
    perception_range: Annotated[int, "Param", "the perception range of the vehicle"] = 2

    # Define state variables
    energy_level: Annotated[int, "State"]
    heading:      Annotated[int, "State"]

    def __init__(self, model: "model.TransportSystem", configuration: Configuration):
        """
        Creates a vehicle agent in a simulation model.

        Args:
            model (model.TransportSystem): the model in which the agent is situated.
            configuration (Configuration): the configuration parameters.
        """
        super().__init__(model, VehicleWorldModel(self))
        configuration.initialize(self)

        # Add a navigator
        self.navigator = Navigator(self.model.space)

        # Add a load capacity of the vehicle and a list of cargos
        self.capacity = self.random.choice(range(self.max_load)) + 1
        self.cargos: list["Cargo"] = []

        # Add an energy level and initialize it to a random value
        self.energy_level = self.random.choice(range(round(0.2 * self.max_energy), self.max_energy + 1))

        # Randomly select a starting position which is not yet occupied by some other vehicle.
        space = self.model.space
        available_positions = space.road_nodes(space.is_cell_empty)
        space.place_agent(self, self.random.choice(available_positions))

        # Set the initial heading of the vehicle to that of the heading of one of the roads leading into the current position.
        self.heading = space.edge_direction(space.roads_to(self.pos)[0], self.pos)

        # Initialize the perceived state of the world.
        self.world_model.perceive()

    def can_coexist(self, other: core.Entity) -> bool:
        """
        Returns True if this entity can coexist in the same cell with the other entity.
        Vehicles are not allowed to coexist with other vehicles.

        Args:
            other (core.Entity): another entity.

        Returns:
            bool: True if coexistance is possible.
        """
        return other == self or not isinstance(other, Vehicle)

    def available_cargo(self, node: Node) -> list["Cargo"]:
        """
        Returns the list of available cargos in a destination node that the vehicle can carry.
        
        Returns:
            list[Cargo]: the list of cargo.
        """
        space = self.world_model.space
        if space.is_destination(node):
            return [e for e in space.get_cell_list_contents([node]) if isinstance(e, Cargo) and e.weight <= self.load_capacity()]
        else:
            return []

    def random_route(self, condition: Callable[[Node], bool] = lambda _: True) -> list[Node]:
        """
        Randomly choose any of the neighboring nodes which fulfils a given condition, which defaults to any node.

        Args:
            condition (Callable[[Node], bool], optional): a condition, specifying which neighboring nodes to choose from. Defaults to any node.

        Returns:
            Node: a list containing the chosen node.
        """
        return [self.random.choice(self.world_model.space.roads_from(self.pos, condition))]

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
        wm = self.world_model
        not_destination = lambda node: not wm.space.is_destination(node)
        if not wm.plan:
            if self.cargos:
                # Go to the destination of the cargo, and when arriving, unload it
                wm.plan = [FollowRoute(self, lambda: self.navigator.shortest_path(self.pos, self.cargos[0].destination)), 
                           UnloadCargo(self, self.cargos[0])]
                # To avoid that the vehicle directly picks up the cargo again, move away from the destination after unloading
                wm.plan += [FollowRoute(self, lambda: self.random_route(not_destination)), 
                            FollowRoute(self, lambda: self.random_route(not_destination))]
            elif cargos := self.available_cargo(self.pos):
                # There is a suitable cargo in the current position, so load it.
                wm.plan = [LoadCargo(self, cargos[0])]
            elif any(self.available_cargo(node) for node in wm.space.roads_from(self.pos)):
                # There is an available cargo in an adjacent node, so move to that one
                wm.plan = [FollowRoute(self, lambda: self.random_route(self.available_cargo))]
            else:
                # Move along the rode to look for cargos elsewhere
                wm.plan = [FollowRoute(self, lambda: self.random_route(not_destination))]

        # If low on energy, make sure that there is a plan to recharge.
        if self.energy_level < 30 and not any(isinstance(c, ChargeEnergy) for c in self.world_model.plan):
            # Go to the nearest charging point and charge energy there before proceeding with the plan.
            wm.plan = [FollowRoute(self, lambda: self.navigator.path_to_nearest_charging_point(self.pos)), 
                       ChargeEnergy(self)]

        # The vehicle wants to enter a destination that is already occupied, move on instead to avoid deadlock
        if wm.space.is_destination(self.next_pos()) and \
           not all(self.can_coexist(other) for other in wm.space.get_cell_list_contents([self.next_pos()])):
            # Abandon current plan, and move to one of the other neighbors which is not a destination node
            self.world_model.plan = [FollowRoute(self, lambda: self.random_route(not_destination))]

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
    max_cargo_weight: Annotated[int, "Param", "The maximum weight of a cargo"] = 3

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
        space.place_agent(self, self.random.choice(available_positions))

        self.weight = self.random.choice(range(self.max_cargo_weight)) + 1
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
            self.destination = self.random.choice(space.road_nodes(lambda n: space.is_destination(n) and not space.is_charging_point(n)))

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