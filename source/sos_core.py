"""
Provides abstract classes representing the core concepts of systems-of-systems.
"""

from typing import List

import mesa

class SoSAgent(mesa.Agent):

    def __init__(self, unique_id: int, model: mesa.Model):
        """
        Creates a SoS agent in a simulation model.

        Args:
            unique_id (int): the unique id of the agent.
            model (mesa.Model): the model in which the agent is situated.
        """
        super().__init__(unique_id, model)

        # Add a plan, which is a list of capability instances.
        self.plan: List["Capability"] = []

        # Add an optional view
        self.view = None

    def create_plan(self):
        """
        Creates a plan for the agent, consisting of a list of capability instances.
        """
        pass

    def step(self):
        """
        The first part of a simulation round when using the Mesa simultaneous activation scheduler.
        If the agent does not have a plan, it creates one.
        Then it checks that the preconditions of the first action in the plan are fulfilled.
        """
        if not self.plan:
            self.create_plan()
        action = self.plan[0]
        self.ready_to_advance = action.precondition()

    def advance(self):
        """
        The second part of a simulation round when using the Mesa simultaneous activation scheduler.
        If the precondition of the first action in the current plan was fullfilled, that action is now carried out.
        If this leads to the action's postcondition being fulfilled, the action is removed from the plan.
        Finally, if the agent has a view, that view is updated.
        """
        action = self.plan[0]
        if self.ready_to_advance:
            action.activate()
        if action.postcondition():
            self.plan = self.plan[1:]

        # Update the views of the agent
        if self.view:
            self.view.update(self)

class Capability:
    """
    A generic capability, serving as a base class for specific capabilities.
    """

    def __init__(self, agent: SoSAgent):
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