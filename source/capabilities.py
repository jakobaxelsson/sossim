"""
Classes that define capabilities of agents.
"""

import random
from typing import Callable

import mesa

from sos_core import Capability
from space import Node

class MoveCapability(Capability):
    
    def __init__(self, agent: mesa.Agent, target: Node):
        """
        Defines the capability of an agent to move to a new position.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network

        Args:
            agent (mesa.Agent): the agent who should be given this capability.
            new_pos (Position): the new position in the space.
        """
        super().__init__(agent)
        self.target = target

    def precondition(self) -> bool:
        """
        Defines the preconditions to make a move:
        - There is a road to the new node from the current node.
        - There is no conflicting traffic.
        - The agent has sufficient energy.

        Returns:
            bool: True if and only if the move is possible.
        """
        space = self.agent.model.space

        # There is no road to the new node from the current node.
        if self.target not in space.roads_from(self.agent.pos):
            return False

        # There is a vehicle in the new node position, and we don't know if it will move or not.
        if not space.is_cell_empty(self.target):
            return False
        
        # Priority rules prevent a move.
        if any(not space.is_cell_empty(priority_pos) for priority_pos in space.priority_nodes(self.agent.pos, self.target)):
            return False

        # The agent has insufficient energy.
        if self.agent.energy_level == 0:
            return False

        return super().precondition()

    def postcondition(self) -> bool:
        """
        The postcondition of a move is that the actual position is the same as the target.

        Returns:
            bool: True if and only if the target has been reached.
        """
        return self.target == self.agent.pos
    
    def activate(self):
        """
        Performs the move.
        """
        self.agent.model.space.move_agent(self.agent, self.target)

        # Reduce agent energy when making the move.
        self.agent.energy_level -= 1

class FindDestinationCapability(Capability):
    """
    Defines the capability of an agent to find an available destination and move there.
    The capability can be given to any agent that can move in a space containing a road network.
    It can take an optional condition specifying what types of destinations are acceptable.
    """

    def __init__(self, agent: mesa.Agent, condition: Callable[Node, bool] = lambda _: True):
        """
        Defines the capability of an agent to move to a new position.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network

        Args:
            agent (mesa.Agent): the agent who should be given this capability.
            condition: (Callable[Position, bool], optional): a condition to be fulfilled by the destination. Defaults to any destination.
        """
        super().__init__(agent)
        self.condition = condition

    def precondition(self) -> bool:
        """
        Defines the preconditions to park. There are two alternatives:
        1. There is a free destination adjacent to the current position which fulfils the specified condition.
        2. The preconditions of the move capability are met. 

        Returns:
            bool: True if and only if the agent can either park or move on.
        """
        space = self.agent.model.space

        # There is an adjacent destination and it is free.
        destinations = [node for node in space.roads_from(self.agent.pos) if space.is_destination(node)]
        if destinations and space.is_cell_empty(destinations[0]) and self.condition(destinations[0]):
            return True
        else:
            # No destination is available here, so insert a move at the head of the agent's plan and check if that is possible.
            new_pos = random.choice([node for node in space.roads_from(self.agent.pos) if not space.is_destination(node)])
            move = MoveCapability(self.agent, new_pos)
            self.agent.plan = [move] + self.agent.plan
            return move.precondition()

    def postcondition(self) -> bool:
        """
        The postcondition of a capability is that the position is a destination which fulfils the specified condition.

        Returns:
            bool: True if and only if the current position is a destination which fulfils the specified condition.
        """
        return self.agent.model.space.is_destination(self.agent.pos) and self.condition(self.agent.pos)
    
    def activate(self):
        """
        Performs the parking or keep looking for another destination.
        """
        # There is an adjacent destination and it is free.
        space = self.agent.model.space
        destination = [node for node in space.roads_from(self.agent.pos) if space.is_destination(node)][0]
        space.move_agent(self.agent, destination)

        # Reduce agent energy when making the move.
        self.agent.energy_level -= 1

class ChargeEnergyCapability(Capability):
    """
    Defines the capability of an agent to charge energy.
    This capability can be given to any agent which has the attributes energy_level and max_energy.
    
    Args:
        agent (mesa.Agent): the agent who should have this capability.
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
        if self.agent.energy_level == self.agent.max_energy:
            print(f"Vehicle {self.agent.unique_id} has completed charging")
        return self.agent.energy_level == self.agent.max_energy
    
    def activate(self):
        """
        Charge energy.
        """
        self.agent.energy_level = min(self.agent.max_energy, self.agent.energy_level + self.agent.charging_speed)