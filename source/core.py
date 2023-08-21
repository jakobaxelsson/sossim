"""
Provides abstract classes representing the core concepts of systems-of-systems.
"""
from typing import Self

# A workaround is needed to make mesa work properly in the browser, since the full package contains dependencies that do not work in that environment.
# Therefore, importing the whole of mesa fails, and instead the few classes needed are imported individually.
from mesa.model import Model as MesaModel
from mesa.agent import Agent as MesaAgent
from mesa.time import StagedActivation

from view import Viewable

class Model(MesaModel, Viewable):
    """
    A comman base class for SoS models.
    """
    def __init__(self):
        super().__init__()

        # Create time and space, using a staged activation scheduler based on the OODA loop
        self.schedule = StagedActivation(self, ["observe", "orient", "decide", "act"])

    def agents(self) -> list["Agent"]:
        """
        Returns the agents in the model.

        Returns:
            list[Agent]: the agents
        """
        # We only create core.Agent, and not any other mesa.Agent, so safe to ignore type error
        return self.schedule.agents # type: ignore
    
    def agent(self, id: int) -> "Agent":
        """
        Returns the agent with the given id. 
        If the agent with that id does not exist, a KeyError exception is raised.

        Args:
            id (int): the agent of the requested agent.

        Returns:
            Agent: the requested agent.
        """
        return self.schedule._agents[id] # type: ignore

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
    # Lift the random attribute of the model to this class for less verbose access
    random = property(lambda self: self.model.random)

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

    def __repr__(self) -> str:
        """
        Returns a string representation of the world model.        
        """
        return f"plan = {self.plan}"

    def perceive(self):
        """
        Updates the perception of the world as represented in this world model.
        Redefined in subclasses.
        """
        pass

class Entity(MesaAgent, Viewable): 
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

        # If the postcondition of the first step in the plan is fulfilled, advance to the next step.
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
        # Start the first activity of the plan, if the plan is not empty.
        if self.world_model.plan:
            self.world_model.plan[0].start()

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

    def next_pos(self) -> tuple[int, int] | None:
        """
        Returns the intended next position of the agent, based on its plan. 
        If the agent has a plan, the intended next position of the first capability of the plan is returned.
        If there is no plan, None is returned.

        Returns:
            Tuple[int, int] | None: _description_
        """
        if self.world_model.plan:
            return self.world_model.plan[0].next_pos()
        else:
            return None

class Capability:
    """
    A generic capability, serving as a base class for specific capabilities.
    """
    # Lift the random attribute of the model to this class for less verbose access
    random = property(lambda self: self.agent.model.random)

    def __init__(self, agent: Agent):
        """
        Creates the capability for a certain agent.
        Subclasses can add parameters for how to use a certain capability.

        Args:
            agent (Agent): the agent who should have this capability.
        """
        self.agent = agent
        self.started = False

    def __repr__(self) -> str:
        """
        Returns a string representation of the capability.        
        """
        # Get the capability name
        name = self.__class__.__name__
        # Get all data attributes 
        excluded = ["agent", "started"]
        data = ", ".join(var + " = " + str(val) for var, val in self.__dict__.items() if var not in excluded and not callable(val))
        return f"{name}({data})"
    
    def start(self):
        """
        Starts the application of the capability.
        This is useful for capabilities that may be started from a different state than when they were put into a plan.
        """
        self.started = True

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
    
    def next_pos(self) -> tuple[int, int]:
        """
        Returns the intended next position of the agent, if this capability were to be activated.
        Note that this is not necessarily the position in the next time step, since preconditions may inhibit the move.
        In case of an inhibited move, next_pos may change in the next time step, if replanning occurs.
        Default behavior is to return the current agent position, i.e. the capability does not move the agent.

        Returns:
            tuple[int, int]: the intended next position.
        """
        return self.agent.pos