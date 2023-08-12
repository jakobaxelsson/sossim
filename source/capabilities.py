"""
Classes that define capabilities of agents.
"""
from typing import Callable, List, Optional

from sos_core import Capability, SoSEntity, SoSAgent
from space import Node

class Move(Capability):
    
    def __init__(self, agent: SoSAgent, route: List[Node]):
        """
        Defines the capability of an agent to move to a new position.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network

        Args:
            agent (SoSAgent): the agent who should be given this capability.
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
        - There is a road to the new node from the current node.
        - There is no conflicting traffic.
        - The agent has sufficient energy.

        Returns:
            bool: True if and only if the move is possible.
        """
        if not self.route:
            return False
        
        space = self.agent.model.space
        target = self.route[0]

        # There is no road to the new node from the current node.
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

    def postcondition(self) -> bool:
        """
        The postcondition of a move is that the actual position is the same as the target.

        Returns:
            bool: True if and only if the final position of the route has been reached, meaning that the route is empty.
        """
        return self.route == []
    
    def activate(self):
        """
        Performs the move and remove the first node from the route.
        """
        self.agent.move(self.route[0])
        self.route = self.route[1:]

class FindDestination(Move):
    """
    Defines the capability of an agent to find an available destination that fulfils a certain condition.
    The capability can be given to any agent that can move in a space containing a road network.
    It can take an optional condition specifying what types of destinations are acceptable.
    """

    def __init__(self, agent: SoSAgent, condition: Optional[Callable[[Node], bool]] = None, final: Optional[Node] = None):
        """
        Defines the capability of an agent to move to a new position.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network.
        If a condition is provided, that must be fulfilled by the destination node.
        If a final node is provided, only that node is accepted as a the final destination.

        Args:
            agent (SoSAgent): the agent who should be given this capability.
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
        Otherwise, randomly select a different non-destination as the target.
        """
        space = self.agent.model.space

        if self.route:
            return
        if self.final:
            self.route = space.shortest_path(self.agent.pos, self.final)[1:]
            return

        destinations = space.roads_from(self.agent.pos, space.is_destination)
        if destinations and all(self.agent.can_coexist(other) for other in space.get_cell_list_contents(destinations)) and self.check_condition(destinations[0]):
            self.route = [destinations[0]]
        else:
            self.route = [self.agent.model.random.choice(space.roads_from(self.agent.pos, lambda node: not space.is_destination(node)))]

    def check_condition(self, node: Node) -> bool:
        """
        Check if the condition is fulfilled in the node. For the result to be True, the following must be fulfilled:
        If the condition was provided, the value of that function must be True.
        If a destination was provided, the node must be equal to that destination.

        Args:
            node (Node): the node.

        Returns:
            bool: True if the node fulfils the condition.
        """
        if self.final and self.final != node:
            return False
        if self.condition and not self.condition(node):
            return False
        return True

    def postcondition(self) -> bool:
        """
        The postcondition of a find destination capability is that the position is a destination which fulfils the specified condition.

        Returns:
            bool: True if and only if the current position is a destination which fulfils the specified condition.
        """
        return self.agent.model.space.is_destination(self.agent.pos) and self.check_condition(self.agent.pos)
    
    def activate(self):
        """
        Performs the move and selects a new route.
        """
        super().activate()

        # Select a new route
        self.select_route()

class LoadCargo(Capability):
    
    def __init__(self, agent: SoSAgent, cargo: SoSEntity):
        """
        Defines the capability of an agent to load a cargo.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network.
        It should also have a max_load attribute.
        The entity constituting the cargo should also have a position and a weight.

        Args:
            agent (SoSAgent): the agent who should be given this capability.
            cargo (SoSEntity): the cargo.
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

    def postcondition(self) -> bool:
        """
        The postcondition of loading a cargo is that the agent is now the carrier of the cargo.

        Returns:
            bool: True if and only if the cargo has been loaded.
        """
        return self.cargo in self.agent.cargos
    
    def activate(self):
        """
        Performs the loading.
        """
        self.agent.load_cargo(self.cargo)
        print("Agent", self.agent.unique_id, "loaded cargo", self.cargo.unique_id, "in position", self.agent.pos, "with destination", self.cargo.destination)

class UnloadCargo(Capability):
    
    def __init__(self, agent: SoSAgent, cargo: SoSEntity):
        """
        Defines the capability of an agent to unload a cargo.
        The capability can be given to an agent which carries a cargo.
 
        Args:
            agent (SoSAgent): the agent who should be given this capability.
            cargo (SoSEntity): the cargo.
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

    def postcondition(self) -> bool:
        """
        The postcondition of unloading a cargo is that the cargo is not carried by the agent.

        Returns:
            bool: True if and only if the cargo has been loaded.
        """
        return self.cargo.carrier != self.agent
    
    def activate(self):
        """
        Performs the unloading.
        """
        self.agent.unload_cargo(self.cargo)
        print("Agent", self.agent.unique_id, "unloaded cargo", self.cargo.unique_id)

class ChargeEnergy(Capability):
    """
    Defines the capability of an agent to charge energy.
    This capability can be given to any agent which has the attributes energy_level and max_energy.
    
    Args:
        agent (SoSAgent): the agent who should have this capability.
    """

    def precondition(self) -> bool:
        """
        The precondition is that the agent is at a charging point.

        Returns:
            bool: True if the capability can be used, False otherwise
        """
        return self.agent.model.space.is_charging_point(self.agent.pos)
    
    def postcondition(self) -> bool:
        """
        The postcondition is that the energy level has reached the maximum.

        Returns:
            bool: True if the capability has been fulfilled, False otherwise
        """
        return self.agent.energy_level >= self.agent.max_energy
    
    def activate(self):
        """
        Charge energy.
        """
        self.agent.energy_level = min(self.agent.max_energy, self.agent.energy_level + self.agent.charging_speed)