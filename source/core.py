"""
Provides abstract classes representing the core concepts of systems-of-systems.
"""
from typing import Self

import mesa
from view import Viewable

class Model(mesa.Model, Viewable):
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
        # We only create core.Agent, and not other mesa.Agent, so safe to ignore type error
        return self.schedule.agents # type: ignore
    
    def time(self) -> float:
        """
        Returns the current time of the simulation.

        Returns:
            Float: the time.
        """
        # Since we know there must be a scheduler, it is safe to ignore type warning.
        return self.schedule.time # type: ignore

class Space(Viewable):
    """
    A comman base class for SoS spaces.
    """

class WorldModel:
    """
    A common base class for SoS world models.
    The world model is an internal, cognitive representation of information about the world.
    It is updated by the agent's perception, and used for reasoning about e.g. planned actions.
    """
    def __init__(self, agent: "Agent"):
        """
        Creates a world model.

        Args:
            model (Model): the simulation's representation of the real world.
        """
        self.agent = agent
        self.space = Space()

        # Add a plan, which is a list of capability instances.
        self.plan: list["Capability"] = []

    def perceive(self):
        """
        Updates the perception of the world as represented in this world model.
        Redefined in subclasses.
        """
        pass

class Entity(mesa.Agent, Viewable): 
    """
    A common abstract baseclass for entities within a SoS.
    All entities are treated as agents, but not all of them have behavior.
    This means also that they can be placed on the map, and have a unique id, which is automatically generated.
    """
    def __init__(self, model: Model):
        # Create agent, with a unique id.
        super().__init__(model.next_id(), model)

        # Add agent to the scheduler
        # Since we know there must be a scheduler, it is safe to ignore type warning
        model.schedule.add(self) # type: ignore

        # Add type information, for type checking
        self.pos: tuple[int, int]

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

    def __init__(self, model: Model, world_model: WorldModel):
        """
        Creates a SoS agent in a simulation model.

        Args:
            unique_id (int): the unique id of the agent.
            model (Model): the model in which the agent is situated.
            world_model (WorldModel): the world model of the agent.
        """
        super().__init__(model)
        self.world_model = world_model

    def update_plan(self):
        """
        Update the plan for the agent, consisting of a list of capability instances.
        """
        pass

    def observe(self):
        """
        Observe stage of the OODA loop used by the simulation scheduler.
        It updates the world model through perception.
        If the agent has a plan, and the first step in that plan is completed, it skips to the next step.
        """
        # Updates the world model through perception.
        self.world_model.perceive()

        if self.world_model.plan and self.world_model.plan[0].postcondition():
            self.world_model.plan = self.world_model.plan[1:]

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
        if self.world_model.plan:
            self.ready_to_act = self.world_model.plan[0].precondition()

    def act(self):
        """
        Act stage of the OODA loop used by the simulation scheduler.
        If the precondition of the first action in the current plan was fullfilled, that action is now carried out.
        Then, any further actions specified in the superclass are carried out.
        """
        if self.world_model.plan and self.ready_to_act:
            self.world_model.plan[0].act()
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
            agent (Agent): the agent who should have this capability.
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