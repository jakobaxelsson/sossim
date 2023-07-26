"""
Classes that define capabilities of agents.
"""

import random
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

    def __repr__(self) -> str:
        """
        Returns a string representation of the capability.        
        """
        return self.__class__.__name__

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
        - There is a road to the new node from the current node.
        - There is no conflicting traffic.
        - TODO: The agent has sufficient energy.

        Returns:
            bool: True if and only if the move is possible.
        """
        rnw = self.agent.model.space.road_network

        # There is no road to the new node from the current node.
        if self.target not in rnw.roads_from(self.agent.pos):
            return False

        # There is a vehicle in the new node position, and we don't know if it will move or not.
        if rnw.nodes[self.target]["agent"]:
            return False
        
        # Priority rules prevent a move.
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

class ParkCapability(Capability):
    
    def __init__(self, agent: mesa.Agent):
        """
        Defines the capability of an agent to find an available destination and park there.
        The capability can be given to any agent that can move in a space containing a road network.

        Args:
            agent (mesa.Agent): the agent who should be given this capability.
        """
        super().__init__(agent)

    def precondition(self) -> bool:
        """
        Defines the preconditions to park. There are two alternatives:
        1. There is a free destination adjacent to the current position.
        2. The preconditions of the move capability are met. 

        Returns:
            bool: True if and only if the agent can either park or move on.
        """
        rnw = self.agent.model.space.road_network

        # There is an adjacent destination and it is free.
        destinations = [node for node in rnw.roads_from(self.agent.pos) if rnw.is_destination(node)]
        if destinations and rnw.nodes[destinations[0]]["agent"] == []:
            return True
        else:
            # No destination is available here, so insert a move at the head of the agent's plan and check if that is possible.
            new_pos = random.choice([node for node in rnw.roads_from(self.agent.pos) if not rnw.is_destination(node)])
            move = MoveCapability(self.agent, new_pos)
            self.agent.plan = [move] + self.agent.plan
            return move.precondition()

    def postcondition(self) -> bool:
        """
        The postcondition of a move is that the position is a destination.

        Returns:
            bool: True if and only if the current position is a destination.
        """
        rnw = self.agent.model.space.road_network
        return rnw.is_destination(self.agent.pos)
    
    def activate(self):
        """
        Performs the parking or keep looking for another destination.
        """
        # There is an adjacent destination and it is free.
        rnw = self.agent.model.space.road_network
        destination = [node for (_, node) in rnw.out_edges(self.agent.pos) if rnw.is_destination(node)][0]
        rnw.nodes[self.agent.pos]["agent"].remove(self.agent)
        rnw.nodes[destination]["agent"].append(self.agent)

        self.agent.heading = rnw[self.agent.pos][destination]["direction"]
        self.agent.pos = destination

        # TODO: Reduce agent energy when making the move.