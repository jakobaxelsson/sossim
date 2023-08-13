"""
Classes that define capabilities of agents.
"""
from typing import Callable, List, Optional

import core
from space import Node

class Move(core.Capability):
    
    def __init__(self, agent: core.Agent, route: List[Node]):
        """
        Defines the capability of an agent to move to a new position along a route of nodes.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network.

        Args:
            agent (core.Agent): the agent who should be given this capability.
            route (Position): the route to be traversed in space.
        """
        super().__init__(agent)
        self.route = route
        # If the route starts in the current position, remove it
        if self.route and self.route[0] == agent.pos:
            self.route = self.route[1:]

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
        if not self.route:
            return False
        
        space = self.agent.model.space
        target = self.route[0]

        # There is no road to the next node from the current node.
        if target not in space.roads_from(self.agent.pos):
            return False

        # If there is another entity in the node with which the agent cannot exist, it must be assumed that it might stay.
        if not all(self.agent.can_coexist(other) for other in space.get_cell_list_contents([target])):
            return False
        
        # Priority rules prevent a move.
        if not all(self.agent.can_coexist(other)
                   for priority_pos in space.priority_nodes(self.agent.pos, target)
                   for other in space.get_cell_list_contents([priority_pos])):
            return False

        # The agent has insufficient energy.
        if self.agent.energy_level == 0:
            return False

        return super().precondition()
    
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

class FindDestination(Move):
    """
    Defines the capability of an agent to find an available destination that fulfils a certain condition.
    The capability can be given to any agent that can move in a space containing a road network.
    It can take an optional condition specifying what types of destinations are acceptable.
    """

    def __init__(self, agent: core.Agent, condition: Optional[Callable[[Node], bool]] = None, final: Optional[Node] = None):
        """
        Defines the capability of an agent to move to a new position.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network.
        If a condition is provided, that must be fulfilled by the destination node.
        If a final node is provided, only that node is accepted as a the final destination.

        Args:
            agent (core.Agent): the agent who should be given this capability.
            condition (Callable[Position, bool], optional): a condition to be fulfilled by the destination. Defaults to always True.
            final (Node, optional): a final node to be achieved. Defaults to None.
        """
        super().__init__(agent, [])
        self.condition = condition
        self.final = final
        self.select_route()

    def select_route(self):
        """
        Selects the route to move.
        If there is already a route, do nothing.
        If a final node has been provided, calculate the shortest route to it.
        If there is an adjacent destination that fulfils the condition, set that as the target.
        Otherwise, randomly move one step.
        """
        space = self.agent.model.space

        # There is already a route, so no need to change it.
        if self.route:
            return
        # A final node is provided, so find the shortest path to it and use that as the route
        if self.final:
            self.route = space.shortest_path(self.agent.pos, self.final)[1:]
            return

        # Find all adjacent nodes that are destinations.
        destinations = space.roads_from(self.agent.pos, space.is_destination)
        if destinations and self.check_condition(destinations[0]) and all(self.agent.can_coexist(other) for other in space.get_cell_list_contents(destinations)):
            # If there is an adjacent destination which meets the provided condition, and which is possible to enter for this agent, set that destination as the route. 
            self.route = [destinations[0]]
        else:
            # Otherwise, randomly choose one of the neighboring non-destination nodes as the next node.
            self.route = [self.agent.model.random.choice(space.roads_from(self.agent.pos, lambda node: not space.is_destination(node)))]

    def check_condition(self, node: Node) -> bool:
        """
        Check if the condition is fulfilled in the node. For the result to be True, the following must be fulfilled:
        If a final destination was provided, the node must be equal to that destination.
        If the condition was provided, the value of that function must be True.
        If neither was provided, the condition is True.

        Args:
            node (Node): the node.

        Returns:
            bool: True if the node fulfils the condition.
        """
        return (not self.final or self.final == node) and (not self.condition or self.condition(node))
    
    def act(self):
        """
        Performs the move and selects a new route.
        """
        super().act()

        # Select a new route
        self.select_route()

    def postcondition(self) -> bool:
        """
        The postcondition of a find destination capability is that the position is a destination which fulfils the specified condition.

        Returns:
            bool: True if and only if the current position is a destination which fulfils the specified condition.
        """
        return self.agent.model.space.is_destination(self.agent.pos) and self.check_condition(self.agent.pos)

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
        if not self.agent.model.space.is_destination(self.agent.pos):
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
        return self.agent.model.space.is_charging_point(self.agent.pos)
    
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