"""
Classes that define capabilities of agents.
"""

from typing import Tuple

import mesa

class Capability:
    """
    A generic capability, serving as a base class for specific capabilities.
    """

    def __init__(self, agent: mesa.Agent):
        """
        Creates the capability for a certain agent.
        Subclasses can add parameters for how to use a certain capability.

        Args:
            agent (mesa.Agent): the agent who should have this capability.
        """
        self.agent = agent

    def precondition(self) -> bool:
        """
        Checks if the precondition for executing this capability is fulfilled.

        Returns:
            bool: True if the capability can be used, False otherwise
        """
        return True
    
    def postcondition(self) -> bool:
        """
        Checks if the postcondition for this capability is fulfilled.

        Returns:
            bool: True if the capability has been fulfilled, False otherwise
        """
        return True
    
    def activate(self):
        """
        Carries out the capability.
        """
        pass
    
class MoveCapability(Capability):
    
    def __init__(self, agent: mesa.Agent, target: Tuple[int, int]):
        """
        Defines the capability of an agent to move to a new position.
        The capability can be given to an agent which has a pos attribute and has a model with a space containing a road network

        Args:
            agent (mesa.Agent): the agent who should be given this capability.
            new_pos (Tuple[int, int]): the new position in the space.
        """
        super().__init__(agent)
        self.target = target

    def precondition(self) -> bool:
        """
        Defines the preconditions to make a move:
        - There is a path to the new node from the current node.
        - There is no conflicting traffic.
        - TODO: The agent has sufficient energy.

        Returns:
            bool: True if and only if the move is possible.
        """
        rnw = self.agent.model.space.road_network

        # There is no path to the new node from the current node.
        if not rnw.has_edge(self.agent.pos, self.target):
            return False

        # There is a vehicle in the new node position, and we don't know if it will move or not.
        if rnw.nodes[self.target]["agent"]:
            return False
        
        # Priority rules of a roundabout prevents a move.
        if any(rnw.nodes[priority_pos]["agent"] for priority_pos in self.agent.model.space.priority_nodes(self.agent.pos, self.target)):
            return False

        # TODO: The agent has insufficient energy.
        pass

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
        rnw = self.agent.model.space.road_network
        rnw.nodes[self.agent.pos]["agent"].remove(self.agent)
        rnw.nodes[self.target]["agent"].append(self.agent)

        self.agent.heading = rnw[self.agent.pos][self.target]["direction"]
        self.agent.pos = self.target

        # TODO: Reduce agent energy when making the move.