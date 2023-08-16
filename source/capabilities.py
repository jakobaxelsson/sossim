"""
Classes that define capabilities of agents.
"""
from typing import Callable, Optional

import core
from space import Node

class Move(core.Capability):
    
    def __init__(self, agent: core.Agent, condition: Callable[[Node], bool] = lambda _: True):
        """
        Defines the capability of an agent to move to a new position.
        It randomly choose any of the neighboring nodes which fulfils a given condition, which defaults to any node.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network.

        Args:
            agent (core.Agent): the agent who should be given this capability.
            condition (Callable[[Node], bool], optional): a condition, specifying which neighboring nodes to choose from. Defaults to any node.
        """
        super().__init__(agent)
        self.condition = condition
        self.route: list[Node] = []

    def start(self):
        """
        Selects the route based on the current position of the agent.
        """
        if not self.started:
            super().start()
            self.route = [self.agent.model.random.choice(self.agent.world_model.space.roads_from(self.agent.pos, self.condition))]

    def precondition(self) -> bool:
        """
        Defines the preconditions to make a move:
        - There is a non-empty route.
        - There is a road to the next node from the current node.
        - There is no conflicting traffic.
        - The agent has sufficient energy.

        Returns:
            bool: True if and only if the move is possible.
        """
        if not super().precondition():
            return False

        wm = self.agent.world_model

        # There is no road to the next node from the current node.
        if self.route[0] not in wm.space.roads_from(self.agent.pos):
            return False

        # If there is another entity in the node with which the agent cannot exist, it must be assumed that it might stay.
        if not all(self.agent.can_coexist(other) for other in wm.space.get_cell_list_contents([self.route[0]])):
            return False
        
        # Priority rules prevent a move.
        if not all(self.agent.can_coexist(other)
                   for priority_pos in wm.space.priority_nodes(self.agent.pos, self.route[0])
                   for other in wm.space.get_cell_list_contents([priority_pos])):
            return False

        # The agent has insufficient energy.
        if self.agent.energy_level == 0:
            return False

        return True
    
    def act(self):
        """
        Performs a move to the next node in the route, and remove that node from the route.
        """
        self.agent.move(self.route[0])

    def postcondition(self) -> bool:
        """
        The postcondition of a move is that the route is empty.

        Returns:
            bool: True if and only if the final position of the route has been reached, meaning that the route is empty.
        """
        return self.route[0] == self.agent.pos

class FollowRoute(core.Capability):
    
    def __init__(self, agent: core.Agent, route_planner: Callable[[], list[Node]]):
        """
        Defines the capability of an agent to move to a new position along a route of nodes.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network.
        It is provided with a route_planner function, which when invoked generates a route starting from the current position.

        Args:
            agent (core.Agent): the agent who should be given this capability.
            route_planner (Callable[[], list[Node]]): a function that generates the route to be traversed in space.
        """
        super().__init__(agent)
        self.route_planner = route_planner
        self.route: list[Node] = []

    def start(self):
        """
        Generates a route to be followed, from the agent's current position.
        """
        if not self.started:
            super().start()
            self.route = self.route_planner()
            # If the current node of the agent is included at the start of the route, remove it
            if self.route[0] == self.agent.pos:
                self.route = self.route[1:]

    def precondition(self) -> bool:
        """
        Defines the preconditions to follow a route:
        - There is a non-empty route.
        - There is a road to the next node from the current node.
        - There is no conflicting traffic.
        - The agent has sufficient energy.

        Returns:
            bool: True if and only if the move is possible.
        """
        if not super().precondition():
            return False

        if not self.route:
            return False
        
        wm = self.agent.world_model
        target = self.route[0]

        # There is no road to the next node from the current node.
        if target not in wm.space.roads_from(self.agent.pos):
            return False

        # If there is another entity in the node with which the agent cannot exist, it must be assumed that it might stay.
        if not all(self.agent.can_coexist(other) for other in wm.space.get_cell_list_contents([target])):
            return False
        
        # Priority rules prevent a move.
        if not all(self.agent.can_coexist(other)
                   for priority_pos in wm.space.priority_nodes(self.agent.pos, target)
                   for other in wm.space.get_cell_list_contents([priority_pos])):
            return False

        # The agent has insufficient energy.
        if self.agent.energy_level == 0:
            return False

        return True
    
    def act(self):
        """
        Performs a move to the next node in the route, and remove that node from the route.
        """
        self.agent.move(self.route[0])
        self.route = self.route[1:]

    def postcondition(self) -> bool:
        """
        The postcondition of a move is that the route is empty.

        Returns:
            bool: True if and only if the final position of the route has been reached, meaning that the route is empty.
        """
        return self.route == []

class LoadCargo(core.Capability):
    
    def __init__(self, agent: core.Agent, cargo: core.Entity):
        """
        Defines the capability of an agent to load a cargo.
        The capability can be given to an agent which has a pos attribute and a max_load attribute.
        The entity constituting the cargo should also have a position and a weight.

        Args:
            agent (core.Agent): the agent who should be given this capability.
            cargo (core.Entity): the cargo.
        """
        super().__init__(agent)
        self.cargo = cargo

    def precondition(self) -> bool:
        """
        Defines the preconditions to load a cargo:
        - The cargo should be in the same position as the agent 
        - The cargo should not not already be loaded.
        - The weight of the cargo should be less than the remaining load capacity of the agent.

        Returns:
            bool: True if and only if loading the cargo is possible.
        """
        # The cargo and the agent are not in the same position
        if self.cargo.pos != self.agent.pos:
            return False
        
        # The cargo is already loaded.
        if self.cargo in self.agent.cargos:
            return False
        
        # The weight of the cargo exceeds the remaining load capacity of the agent.
        if self.cargo.weight > self.agent.load_capacity():
            return False

        return super().precondition()
    
    def act(self):
        """
        Performs the loading.
        """
        self.agent.load_cargo(self.cargo)

    def postcondition(self) -> bool:
        """
        The postcondition of loading a cargo is that the agent is now the carrier of the cargo.

        Returns:
            bool: True if and only if the cargo has been loaded.
        """
        return self.cargo in self.agent.cargos

class UnloadCargo(core.Capability):
    
    def __init__(self, agent: core.Agent, cargo: core.Entity):
        """
        Defines the capability of an agent to unload a cargo.
        The capability can be given to an agent which can carry a cargo.
 
        Args:
            agent (core.Agent): the agent who should be given this capability.
            cargo (core.Entity): the cargo.
        """
        super().__init__(agent)
        self.cargo = cargo

    def precondition(self) -> bool:
        """
        Defines the preconditions to load a cargo:
        - The agent is carrying the cargo.
        - The current position is a destination.

        Returns:
            bool: True if and only if unloading the cargo is possible.
        """
        # The agent is not carrying the cargo
        if self.cargo not in self.agent.cargos:
            return False

        # The current position is not a destination.
        if not self.agent.world_model.space.is_destination(self.agent.pos):
            return False

        return super().precondition()
    
    def act(self):
        """
        Performs the unloading.
        """
        self.agent.unload_cargo(self.cargo)

    def postcondition(self) -> bool:
        """
        The postcondition of unloading a cargo is that the cargo is not carried by the agent.

        Returns:
            bool: True if and only if the cargo has been loaded.
        """
        return self.cargo.carrier != self.agent

class ChargeEnergy(core.Capability):
    """
    Defines the capability of an agent to charge energy.
    This capability can be given to any agent which has the attributes energy_level and max_energy.
    
    Args:
        agent (core.Agent): the agent who should have this capability.
    """

    def precondition(self) -> bool:
        """
        The precondition is that the agent is at a charging point.

        Returns:
            bool: True if the capability can be used, False otherwise
        """
        return self.agent.world_model.space.is_charging_point(self.agent.pos)
    
    def act(self):
        """
        Charge energy.
        """
        self.agent.energy_level = min(self.agent.max_energy, self.agent.energy_level + self.agent.charging_speed)

    def postcondition(self) -> bool:
        """
        The postcondition is that the energy level has reached the maximum.

        Returns:
            bool: True if the capability has been fulfilled, False otherwise
        """
        return self.agent.energy_level >= self.agent.max_energy