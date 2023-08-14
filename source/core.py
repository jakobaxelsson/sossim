"""
Provides abstract classes representing the core concepts of systems-of-systems.
"""
from typing import Self

import mesa
from view import viewable

@viewable
class Model(mesa.Model):
    """
    A comman base class for SoS models.
    """
    def __init__(self):
        super().__init__()

        # Create time and space, using a staged activation scheduler based on the OODA loop
        self.schedule = mesa.time.StagedActivation(self, ["observe", "orient", "decide", "act"])

    def agents(self) -> list["Agent"]:
        """
        Returns the agents in the model.

        Returns:
            list[Agent]: the agents
        """
        return self.schedule.agents
    
    def time(self) -> float:
        """
        Returns the current time of the simulation.

        Returns:
            Float: the time.
        """
        return self.schedule.time

@viewable
class Space:
    """
    A comman base class for SoS spaces.
    """

@viewable
class Entity(mesa.Agent): 
    """
    A common abstract baseclass for entities within a SoS.
    All entities are treated as agents, but not all of them have behavior.
    This means also that they can be placed on the map, and have a unique id, which is automatically generated.
    """
    id_counter = 0 # Counter for generating unique id.

    def __init__(self, model: Model):
        # Generate unique id based on counter.
        super().__init__(Entity.id_counter, model)
        Entity.id_counter += 1

        # Add agent to the scheduler
        model.schedule.add(self)

    def __repr__(self) -> str:
        """
        Returns a string representation of the entity.        
        """
        return f"{self.__class__.__name__}_{self.unique_id}"
    
    def can_coexist(self, other: Self) -> bool:
        """
        Returns True if this entity can coexist in the same cell with the other entity.
        Default is that all entities can coexist, but this can be refined for specific subclasses.

        Args:
            other (SoSEntity): another entity.

        Returns:
            bool: True if coexistance is possible.
        """
        return True
    
    def observe(self):
        """
        Observe stage of the OODA loop used by the simulation scheduler.
        Default behavior is to do nothing.
        """
        pass

    def orient(self):
        """
        Orient stage of the OODA loop used by the simulation scheduler.
        Default behavior is to do nothing.
        """
        pass

    def decide(self):
        """
        Decide stage of the OODA loop used by the simulation scheduler.
        Default behavior is to do nothing.
        """
        pass

    def act(self):
        """
        Act stage of the OODA loop used by the simulation scheduler.
        Default behavior is to just update the views.
        """        
        self.update_views()

class Agent(Entity):

    def __init__(self, model: Model):
        """
        Creates a SoS agent in a simulation model.

        Args:
            unique_id (int): the unique id of the agent.
            model (core.Model): the model in which the agent is situated.
        """
        super().__init__(model)

        # Add a plan, which is a list of capability instances.
        self.plan: list["Capability"] = []

    def update_plan(self):
        """
        Update the plan for the agent, consisting of a list of capability instances.
        """
        pass

    def observe(self):
        """
        Observe stage of the OODA loop used by the simulation scheduler.
        If the agent has a plan, and the first step in that plan is completed, it skips to the next step.
        """
        # TODO: This should update the world model by observing the real world.
        if self.plan and self.plan[0].postcondition():
            self.plan = self.plan[1:]

    def orient(self):
        """
        Orient stage of the OODA loop used by the simulation scheduler.
        It updates the agent's plan.
        """
        # TODO: This should generate a list of alternative plans, based solely on the world model.
        # Update the plan based on the current status of the world.
        self.update_plan()

    def decide(self):
        """
        Decide stage of the OODA loop used by the simulation scheduler.
        It checks if the preconditions of the first action in the plan are fulfilled.
        """
        # TODO: This should select the best action to take given the value of the alternative plans, based solely on the world model.
        # Check if the first step of the plan can be carried out.
        if self.plan:
            self.ready_to_act = self.plan[0].precondition()

    def act(self):
        """
        Act stage of the OODA loop used by the simulation scheduler.
        If the precondition of the first action in the current plan was fullfilled, that action is now carried out.
        Then, any further actions specified in the superclass are carried out.
        """
        if self.plan and self.ready_to_act:
            self.plan[0].act()
        super().act()

class Capability:
    """
    A generic capability, serving as a base class for specific capabilities.
    """

    def __init__(self, agent: Agent):
        """
        Creates the capability for a certain agent.
        Subclasses can add parameters for how to use a certain capability.

        Args:
            agent (core.Agent): the agent who should have this capability.
        """
        self.agent = agent

    def __repr__(self) -> str:
        """
        Returns a string representation of the capability.        
        """
        # Get the capability name
        name = self.__class__.__name__
        # Get all data attributes 
        data = ", ".join(var + " = " + str(val) for var, val in self.__dict__.items() if var not in ["agent"] and not callable(val))
        return f"{name}({data})"

    def precondition(self) -> bool:
        """
        Checks if the precondition for executing this capability is fulfilled.

        Returns:
            bool: True if the capability can be used, False otherwise
        """
        return True
    
    def act(self):
        """
        Carries out the capability during one time step.
        """
        pass

    def postcondition(self) -> bool:
        """
        Checks if the postcondition for this capability is fulfilled.

        Returns:
            bool: True if the capability has been fulfilled, False otherwise
        """
        return True